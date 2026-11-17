from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ShipmentForm, StaffUpdateForm
from .geo import COUNTRIES
from .models import Shipment


def staff_required(view):
    """Only logged-in staff (the admin) may open these pages; everyone else gets 403."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not (request.user.is_active and request.user.is_staff):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


@login_required
def dashboard(request):
    shipments = request.user.shipments.all()
    context = {
        "shipments": shipments,
        "total": shipments.count(),
        "delivered": shipments.filter(status=Shipment.Status.DELIVERED).count(),
        "active": shipments.exclude(
            status__in=[Shipment.Status.DELIVERED, Shipment.Status.CANCELLED]
        ).count(),
    }
    return render(request, "shipments/dashboard.html", context)


@login_required
def shipment_create(request):
    form = ShipmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        shipment = form.save(commit=False)
        shipment.user = request.user
        shipment.save()
        return redirect("shipments:created", tracking_id=shipment.tracking_id)
    return render(request, "shipments/shipment_form.html", {"form": form})


@login_required
def shipment_created(request, tracking_id):
    shipment = get_object_or_404(Shipment, tracking_id=tracking_id, user=request.user)
    return render(request, "shipments/shipment_created.html", {"shipment": shipment})


def track_lookup(request):
    """Search box: ?tracking_id=SSL-XXXXXXXXXX redirects to the tracking page."""
    raw = request.GET.get("tracking_id", "")
    tracking_id = raw.strip().upper().replace(" ", "")
    if tracking_id:
        if Shipment.objects.filter(tracking_id=tracking_id).exists():
            return redirect("shipments:track_detail", tracking_id=tracking_id)
        messages.error(request, f"No shipment found for tracking ID “{raw.strip()}”.")
    return render(request, "shipments/track_lookup.html", {"query": raw.strip()})


def _build_map_data(shipment, updates):
    """Everything the Leaflet map needs, as plain JSON-serialisable data."""

    def point(country, city):
        coords = COUNTRIES.get(country)
        if not coords:
            return None
        return {"lat": coords[0], "lng": coords[1], "label": f"{city}, {country}"}

    points = []
    for update in updates:
        coords = update.coords
        if not coords:
            continue
        points.append(
            {
                "lat": coords[0],
                "lng": coords[1],
                "title": update.get_status_display(),
                "location": update.location or update.country,
                "time": timezone.localtime(update.created_at).strftime("%d %b %Y, %H:%M"),
            }
        )

    return {
        "origin": point(shipment.origin_country, shipment.origin_city),
        "destination": point(shipment.destination_country, shipment.destination_city),
        "points": points,
        "delivered": shipment.status == Shipment.Status.DELIVERED,
    }


def track_detail(request, tracking_id):
    shipment = get_object_or_404(Shipment, tracking_id=tracking_id)
    updates = list(shipment.updates.all())  # oldest -> newest
    user = request.user
    can_see_private = user.is_authenticated and (
        user == shipment.user or user.is_staff
    )
    context = {
        "shipment": shipment,
        "updates": list(reversed(updates)),  # newest first for the timeline
        "latest": updates[-1] if updates else None,
        "steps": shipment.progress_steps(),
        "map_data": _build_map_data(shipment, updates),
        "can_see_private": can_see_private,
    }
    return render(request, "shipments/track_detail.html", context)


# --- Staff (admin) dashboard -------------------------------------------------

@staff_required
def manage_dashboard(request):
    """Every shipment from every customer, with search and status filter."""
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    shipments = Shipment.objects.select_related("user")
    if query:
        shipments = shipments.filter(
            Q(tracking_id__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(receiver_name__icontains=query)
            | Q(origin_country__icontains=query)
            | Q(destination_country__icontains=query)
            | Q(origin_city__icontains=query)
            | Q(destination_city__icontains=query)
        )
    if status:
        shipments = shipments.filter(status=status)

    counts = {
        row["status"]: row["n"]
        for row in Shipment.objects.values("status").annotate(n=Count("id"))
    }
    status_cards = [
        {"value": value, "label": label, "count": counts.get(value, 0)}
        for value, label in Shipment.Status.choices
    ]
    total = sum(counts.values())
    closed = counts.get("delivered", 0) + counts.get("cancelled", 0)

    page = Paginator(shipments, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "page": page,
        "query": query,
        "status": status,
        "status_choices": Shipment.Status.choices,
        "status_cards": status_cards,
        "total": total,
        "active": total - closed,
        "delivered": counts.get("delivered", 0),
        "customers": get_user_model().objects.filter(is_staff=False).count(),
        "querystring": params.urlencode(),
    }
    return render(request, "shipments/manage_dashboard.html", context)


@staff_required
def manage_shipment(request, tracking_id):
    """Full details of one shipment plus the form to log a new tracking update."""
    shipment = get_object_or_404(
        Shipment.objects.select_related("user"), tracking_id=tracking_id
    )
    form = StaffUpdateForm(
        request.POST or None,
        initial={
            "status": shipment.status,
            "country": shipment.updates.last().country if shipment.updates.exists() else "",
            "estimated_delivery": shipment.estimated_delivery,
        },
    )
    if request.method == "POST" and form.is_valid():
        update = form.save(commit=False)
        update.shipment = shipment
        update.save()  # also sets shipment.status to this update's status
        Shipment.objects.filter(pk=shipment.pk).update(
            estimated_delivery=form.cleaned_data["estimated_delivery"]
        )
        messages.success(request, f"{shipment.tracking_id} updated: {update.get_status_display()}.")
        return redirect("shipments:manage_shipment", tracking_id=shipment.tracking_id)

    updates = list(shipment.updates.all())
    picker_data = {
        "countries": {name: list(coords) for name, coords in COUNTRIES.items()},
        "origin": _build_map_data(shipment, updates)["origin"],
        "destination": _build_map_data(shipment, updates)["destination"],
    }
    context = {
        "shipment": shipment,
        "form": form,
        "updates": list(reversed(updates)),
        "picker_data": picker_data,
    }
    return render(request, "shipments/manage_shipment.html", context)

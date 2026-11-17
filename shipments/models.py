import secrets

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .geo import COUNTRIES, COUNTRY_CHOICES

# Unambiguous characters only (no 0/O, 1/I) so IDs are easy to read out loud.
TRACKING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_unique_tracking_id():
    while True:
        candidate = "SSL-" + "".join(secrets.choice(TRACKING_ALPHABET) for _ in range(10))
        if not Shipment.objects.filter(tracking_id=candidate).exists():
            return candidate


class Shipment(models.Model):
    class ServiceType(models.TextChoices):
        GOODS = "goods", "Goods / parcel"
        SERVICE = "service", "Service"

    class Status(models.TextChoices):
        PENDING = "pending", "Request received"
        CONFIRMED = "confirmed", "Confirmed"
        PICKED_UP = "picked_up", "Picked up"
        IN_TRANSIT = "in_transit", "In transit"
        CUSTOMS = "customs", "In customs clearance"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class Currency(models.TextChoices):
        GBP = "GBP", "GBP (£)"
        USD = "USD", "USD ($)"
        EUR = "EUR", "EUR (€)"
        NGN = "NGN", "NGN (₦)"

    # Steps shown in the progress bar on the tracking page.
    PROGRESS_STEPS = [
        (Status.PENDING, "Received"),
        (Status.CONFIRMED, "Confirmed"),
        (Status.PICKED_UP, "Picked up"),
        (Status.IN_TRANSIT, "In transit"),
        (Status.CUSTOMS, "Customs"),
        (Status.OUT_FOR_DELIVERY, "Out for delivery"),
        (Status.DELIVERED, "Delivered"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shipments"
    )
    tracking_id = models.CharField(max_length=20, unique=True, editable=False)

    service_type = models.CharField(
        max_length=10, choices=ServiceType.choices, default=ServiceType.GOODS
    )
    item_description = models.TextField(
        help_text="What are we moving? For services, describe the work required."
    )
    weight_kg = models.DecimalField(
        "Weight (kg)", max_digits=8, decimal_places=2, null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1)
    declared_value = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(
        max_length=3, choices=Currency.choices, default=Currency.GBP
    )

    origin_country = models.CharField(max_length=60, choices=COUNTRY_CHOICES)
    origin_city = models.CharField(max_length=100)
    origin_address = models.TextField("Pick-up address")

    destination_country = models.CharField(max_length=60, choices=COUNTRY_CHOICES)
    destination_city = models.CharField(max_length=100)
    destination_address = models.TextField("Delivery address")

    receiver_name = models.CharField(max_length=150)
    receiver_phone = models.CharField(max_length=30)
    receiver_email = models.EmailField(blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    estimated_delivery = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tracking_id} ({self.origin_country} → {self.destination_country})"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        if not self.tracking_id:
            self.tracking_id = generate_unique_tracking_id()
        super().save(*args, **kwargs)
        if creating:
            ShipmentUpdate.objects.create(
                shipment=self,
                status=self.Status.PENDING,
                location=self.origin_city,
                country=self.origin_country,
                note="Your shipment request has been received and is awaiting confirmation.",
            )

    def get_absolute_url(self):
        return reverse("shipments:track_detail", args=[self.tracking_id])

    @property
    def is_closed(self):
        return self.status in (self.Status.DELIVERED, self.Status.CANCELLED)

    def progress_steps(self):
        """Steps for the progress bar, flagged done / current."""
        keys = [key for key, _ in self.PROGRESS_STEPS]
        if self.status == self.Status.CANCELLED or self.status not in keys:
            index = -1
        else:
            index = keys.index(self.status)
        delivered = self.status == self.Status.DELIVERED
        return [
            {
                "label": label,
                "done": delivered or i < index,
                "current": (i == index) and not delivered,
            }
            for i, (_, label) in enumerate(self.PROGRESS_STEPS)
        ]


class ShipmentUpdate(models.Model):
    """One tracking event, entered by an admin. The newest one drives the status."""

    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE, related_name="updates"
    )
    status = models.CharField(max_length=20, choices=Shipment.Status.choices)
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Where the goods are now, e.g. 'Heathrow Cargo Terminal, London'.",
    )
    country = models.CharField(
        max_length=60,
        choices=COUNTRY_CHOICES,
        blank=True,
        help_text="Used to place the marker on the map if no exact coordinates are given.",
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Optional. Exact position (right-click a spot on Google Maps to copy it).",
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    note = models.TextField(blank=True, help_text="Message shown to the customer.")
    created_at = models.DateTimeField("Date / time", default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.shipment.tracking_id}: {self.get_status_display()}"

    @property
    def coords(self):
        """(lat, lng) for the map, or None when nothing usable was entered."""
        if self.latitude is not None and self.longitude is not None:
            return (self.latitude, self.longitude)
        return COUNTRIES.get(self.country)

    def _sync_shipment_status(self):
        latest = (
            ShipmentUpdate.objects.filter(shipment_id=self.shipment_id)
            .order_by("-created_at", "-id")
            .first()
        )
        if latest:
            Shipment.objects.filter(pk=self.shipment_id).update(
                status=latest.status, updated_at=timezone.now()
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_shipment_status()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self._sync_shipment_status()

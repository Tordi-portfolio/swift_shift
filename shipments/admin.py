from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Shipment, ShipmentUpdate


class ShipmentUpdateInline(admin.TabularInline):
    """Add a row here every time the goods move. The newest row sets the status."""

    model = ShipmentUpdate
    extra = 1
    fields = ("created_at", "status", "location", "country", "latitude", "longitude", "note")
    ordering = ("created_at", "id")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        "tracking_id",
        "user",
        "service_type",
        "origin_country",
        "destination_country",
        "status",
        "estimated_delivery",
        "created_at",
    )
    list_filter = ("status", "service_type", "origin_country", "destination_country")
    search_fields = (
        "tracking_id",
        "user__username",
        "user__email",
        "receiver_name",
        "origin_city",
        "destination_city",
    )
    date_hierarchy = "created_at"
    readonly_fields = ("tracking_id", "status", "tracking_page", "created_at", "updated_at")
    inlines = [ShipmentUpdateInline]
    fieldsets = (
        ("Tracking", {"fields": ("tracking_id", "tracking_page", "status", "estimated_delivery")}),
        ("Customer", {"fields": ("user",)}),
        (
            "Shipment",
            {
                "fields": (
                    "service_type",
                    "item_description",
                    ("weight_kg", "quantity"),
                    ("declared_value", "currency"),
                )
            },
        ),
        ("Origin", {"fields": ("origin_country", "origin_city", "origin_address")}),
        ("Destination", {"fields": ("destination_country", "destination_city", "destination_address")}),
        ("Receiver", {"fields": ("receiver_name", "receiver_phone", "receiver_email")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Public tracking page")
    def tracking_page(self, obj):
        if not obj.pk:
            return "Available after saving."
        url = reverse("shipments:track_detail", args=[obj.tracking_id])
        return format_html('<a href="{}" target="_blank">Open tracking page</a>', url)


@admin.register(ShipmentUpdate)
class ShipmentUpdateAdmin(admin.ModelAdmin):
    list_display = ("shipment", "status", "location", "country", "created_at")
    list_filter = ("status", "country")
    search_fields = ("shipment__tracking_id", "location", "note")

from django import forms

from .models import Shipment, ShipmentUpdate


class StaffUpdateForm(forms.ModelForm):
    """Used on the staff dashboard to log a new tracking event."""

    estimated_delivery = forms.DateField(
        required=False,
        label="Estimated delivery date",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    class Meta:
        model = ShipmentUpdate
        fields = ["status", "location", "country", "latitude", "longitude", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}
        labels = {"note": "Message to customer"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")
        self.fields["latitude"].widget.attrs["step"] = "any"
        self.fields["longitude"].widget.attrs["step"] = "any"

    def clean(self):
        cleaned = super().clean()
        lat, lng = cleaned.get("latitude"), cleaned.get("longitude")
        if (lat is None) != (lng is None):
            self.add_error("longitude", "Enter both latitude and longitude, or leave both empty.")
        return cleaned


class ShipmentForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = [
            "service_type",
            "item_description",
            "weight_kg",
            "quantity",
            "declared_value",
            "currency",
            "origin_country",
            "origin_city",
            "origin_address",
            "destination_country",
            "destination_city",
            "destination_address",
            "receiver_name",
            "receiver_phone",
            "receiver_email",
        ]
        widgets = {
            "item_description": forms.Textarea(attrs={"rows": 4}),
            "origin_address": forms.Textarea(attrs={"rows": 2}),
            "destination_address": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "service_type": "What do you want to send?",
            "item_description": "Description",
            "origin_country": "Country",
            "origin_city": "City",
            "destination_country": "Country",
            "destination_city": "City",
            "receiver_name": "Receiver's full name",
            "receiver_phone": "Receiver's phone",
            "receiver_email": "Receiver's email (optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")
        self.fields["weight_kg"].widget.attrs.update({"step": "0.01", "min": "0"})
        self.fields["quantity"].widget.attrs.update({"min": "1"})
        self.fields["declared_value"].widget.attrs.update({"step": "0.01", "min": "0"})

    def clean(self):
        cleaned = super().clean()
        origin = cleaned.get("origin_country")
        destination = cleaned.get("destination_country")
        if origin and destination and origin == destination:
            self.add_error(
                "destination_country",
                "Destination must be in a different country from the pick-up country.",
            )
        if cleaned.get("service_type") == Shipment.ServiceType.GOODS and not cleaned.get(
            "weight_kg"
        ):
            self.add_error("weight_kg", "Please enter the weight of the goods.")
        return cleaned

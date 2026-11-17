from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Shipment, ShipmentUpdate


def shipment_payload(**overrides):
    data = {
        "service_type": "goods",
        "item_description": "Two boxes of books",
        "weight_kg": "4.50",
        "quantity": 2,
        "declared_value": "120.00",
        "currency": "GBP",
        "origin_country": "United Kingdom",
        "origin_city": "London",
        "origin_address": "1 High Street",
        "destination_country": "Nigeria",
        "destination_city": "Lagos",
        "destination_address": "5 Marina Road",
        "receiver_name": "Ada Obi",
        "receiver_phone": "+2348000000000",
        "receiver_email": "",
    }
    data.update(overrides)
    return data


class ShipmentFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "amy", "amy@example.com", "S3cure-pass-123"
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("shipments:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_registration_logs_user_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Bob",
                "last_name": "Jones",
                "username": "bob",
                "email": "bob@example.com",
                "password1": "S3cure-pass-123",
                "password2": "S3cure-pass-123",
            },
        )
        self.assertRedirects(response, reverse("shipments:dashboard"))

    def test_creating_a_shipment_issues_a_tracking_id(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("shipments:create"), shipment_payload())
        shipment = Shipment.objects.get()
        self.assertTrue(shipment.tracking_id.startswith("SSL-"))
        self.assertRedirects(
            response, reverse("shipments:created", args=[shipment.tracking_id])
        )
        self.assertEqual(shipment.updates.count(), 1)

    def test_same_country_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("shipments:create"), shipment_payload(destination_country="United Kingdom")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Shipment.objects.count(), 0)

    def test_tracking_page_is_public_and_follows_latest_update(self):
        self.client.force_login(self.user)
        self.client.post(reverse("shipments:create"), shipment_payload())
        shipment = Shipment.objects.get()
        ShipmentUpdate.objects.create(
            shipment=shipment,
            status="in_transit",
            location="Frankfurt Hub",
            country="Germany",
        )
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, "in_transit")

        self.client.logout()
        response = self.client.get(reverse("shipments:track_detail", args=[shipment.tracking_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Frankfurt Hub")

    def test_lookup_redirects_to_tracking_page(self):
        self.client.force_login(self.user)
        self.client.post(reverse("shipments:create"), shipment_payload())
        shipment = Shipment.objects.get()
        response = self.client.get(
            reverse("shipments:track_lookup"), {"tracking_id": shipment.tracking_id.lower()}
        )
        self.assertRedirects(
            response,
            reverse("shipments:track_detail", args=[shipment.tracking_id]),
        )


class StaffDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user("amy", "amy@example.com", "S3cure-pass-123")
        self.staff = User.objects.create_user(
            "boss", "boss@example.com", "S3cure-pass-123", is_staff=True
        )
        self.shipment = Shipment.objects.create(
            user=self.customer,
            **{k: v for k, v in shipment_payload().items()
               if k not in ("weight_kg", "declared_value", "quantity")},
            weight_kg="4.50", quantity=2, declared_value="120.00",
        )

    def test_anonymous_is_sent_to_login(self):
        response = self.client.get(reverse("shipments:manage_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_customer_is_forbidden(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("shipments:manage_dashboard")).status_code, 403)
        url = reverse("shipments:manage_shipment", args=[self.shipment.tracking_id])
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_sees_all_shipments(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("shipments:manage_dashboard"))
        self.assertContains(response, self.shipment.tracking_id)

    def test_staff_can_post_an_update(self):
        self.client.force_login(self.staff)
        url = reverse("shipments:manage_shipment", args=[self.shipment.tracking_id])
        response = self.client.post(url, {
            "status": "in_transit",
            "location": "Frankfurt Hub",
            "country": "Germany",
            "latitude": "50.11",
            "longitude": "8.68",
            "note": "Left the hub.",
            "estimated_delivery": "2026-12-01",
        })
        self.assertRedirects(response, url)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, "in_transit")
        self.assertEqual(str(self.shipment.estimated_delivery), "2026-12-01")

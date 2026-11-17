from django.urls import path

from . import views

app_name = "shipments"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("shipments/new/", views.shipment_create, name="create"),
    path("shipments/created/<str:tracking_id>/", views.shipment_created, name="created"),
    path("manage/", views.manage_dashboard, name="manage_dashboard"),
    path("manage/<str:tracking_id>/", views.manage_shipment, name="manage_shipment"),
    path("track/", views.track_lookup, name="track_lookup"),
    path("track/<str:tracking_id>/", views.track_detail, name="track_detail"),
]

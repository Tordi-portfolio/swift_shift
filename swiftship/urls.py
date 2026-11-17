from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

admin.site.site_header = "SwiftShipLogistics Admin"
admin.site.site_title = "SwiftShipLogistics"
admin.site.index_title = "Manage shipments and tracking updates"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("accounts/", include("accounts.urls")),
    path("", include("shipments.urls")),
]

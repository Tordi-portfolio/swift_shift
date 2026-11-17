from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import LoginForm, RegisterForm


class SiteLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        # Staff land on the management dashboard; customers on their own dashboard.
        if self.request.user.is_staff:
            return reverse("shipments:manage_dashboard")
        return super().get_default_redirect_url()


def register(request):
    if request.user.is_authenticated:
        return redirect("shipments:dashboard")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to SwiftShipLogistics, {user.first_name}!")
        return redirect("shipments:dashboard")
    return render(request, "accounts/register.html", {"form": form})

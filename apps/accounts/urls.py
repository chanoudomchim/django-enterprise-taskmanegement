"""URL configuration for accounts."""

from django.urls import path
from apps.accounts.views import (
    RegisterView,
    LoginView,
    LogoutView,
    VerifyEmailView,
    ProfileView,
    PasswordChangeView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("verify-email/<str:token>/", VerifyEmailView.as_view(), name="verify_email"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/password/", PasswordChangeView.as_view(), name="password_change"),
]


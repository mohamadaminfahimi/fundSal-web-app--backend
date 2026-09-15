# apps/users/urls.py

from django.urls import path

from .views import (
    CheckPhoneView,
    LoginView,
    LogoutView,
    ProfileView,
    RefreshTokenView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("check-phone/", CheckPhoneView.as_view(), name="check-phone"),  # ✅
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh-token"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
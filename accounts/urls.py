from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    DevLoginView,
    LoginView,
    MeView,
    RegisterView,
    ResendOtpView,
    UserDeleteView,
    UsersListView,
    VerifyOtpView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-otp/", VerifyOtpView.as_view(), name="verify-otp"),
    path("resend-otp/", ResendOtpView.as_view(), name="resend-otp"),
    path("login/", LoginView.as_view(), name="login"),
    path("dev-login/", DevLoginView.as_view(), name="dev-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("users/", UsersListView.as_view(), name="users"),
    path("users/<int:pk>/", UserDeleteView.as_view(), name="user-delete"),
]

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import EmailOTP, User
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    ResendOtpSerializer,
    UserSerializer,
    VerifyOtpSerializer,
)


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def _otp_payload(otp):
    """Expose the code in dev so the OTP screen is testable without SMS."""
    data = {"message": f"An OTP was sent to your email/phone. (expires in {settings.OTP_TTL_MINUTES} min)"}
    if settings.OTP_DEBUG_RETURN:
        data["devOtp"] = otp.code
    print(f"[EatEarn OTP] {otp.user.email} -> {otp.code}")
    return data


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        otp = EmailOTP.issue(user, purpose="register")
        return Response(
            {"user": UserSerializer(user).data, **_otp_payload(otp)},
            status=status.HTTP_201_CREATED,
        )


class VerifyOtpView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()
        code = serializer.validated_data["code"].strip()

        user = get_object_or_404(User, email=email)
        otp = (
            EmailOTP.objects.filter(user=user, purpose="register", is_used=False)
            .order_by("-created_at")
            .first()
        )
        if not otp or otp.code != code:
            return Response({"detail": "Invalid OTP code."}, status=status.HTTP_400_BAD_REQUEST)
        if otp.is_expired:
            return Response({"detail": "OTP code has expired. Request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        otp.is_used = True
        otp.save(update_fields=["is_used"])
        user.is_verified = True
        user.save(update_fields=["is_verified"])

        return Response({"user": UserSerializer(user).data, "tokens": tokens_for(user)})


class ResendOtpView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()
        user = get_object_or_404(User, email=email)
        otp = EmailOTP.issue(user, purpose="register")
        return Response(_otp_payload(otp))


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response({"user": UserSerializer(user).data, "tokens": tokens_for(user)})


class DevLoginView(APIView):
    """Demo-friendly one-tap login by email + role (no password).

    Keeps the existing 'Preview as' flow working and is handy for the FYP demo.
    Disabled automatically when DEBUG is off.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.DEBUG:
            return Response({"detail": "Not available."}, status=status.HTTP_403_FORBIDDEN)
        email = (request.data.get("email") or "").lower().strip()
        role = request.data.get("role")

        user = User.objects.filter(email=email).first()
        if not user and role:
            user = User.objects.filter(role=role).first()
        if not user:
            return Response({"detail": "No demo account found for that role."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"user": UserSerializer(user).data, "tokens": tokens_for(user)})


class UsersListView(APIView):
    """Admin-only directory of all accounts (used by the admin dashboard)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.ADMIN:
            return Response({"detail": "Admins only."}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all()
        return Response(UserSerializer(users, many=True).data)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

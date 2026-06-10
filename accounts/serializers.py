from django.contrib.auth import authenticate
from rest_framework import serializers

from catalog.models import Vendor

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serialises a user using the camelCase shape the mobile app expects."""

    id = serializers.CharField(read_only=True)
    fullName = serializers.CharField(source="full_name")
    vendorId = serializers.SerializerMethodField()
    studentId = serializers.CharField(source="student_id", required=False, allow_blank=True)
    hostelBlock = serializers.CharField(source="hostel_block", required=False, allow_blank=True)
    cafeteriaName = serializers.CharField(source="cafeteria_name", required=False, allow_blank=True)
    businessTag = serializers.CharField(source="business_tag", required=False, allow_blank=True)
    deliveryMode = serializers.CharField(source="delivery_mode", required=False, allow_blank=True)
    pickupZone = serializers.CharField(source="pickup_zone", required=False, allow_blank=True)
    isVerified = serializers.BooleanField(source="is_verified", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "fullName",
            "email",
            "phone",
            "role",
            "vendorId",
            "studentId",
            "department",
            "hostelBlock",
            "cafeteriaName",
            "businessTag",
            "deliveryMode",
            "pickupZone",
            "latitude",
            "longitude",
            "isVerified",
        ]

    def get_vendorId(self, obj):
        return str(obj.vendor_id) if obj.vendor_id else None


class RegisterSerializer(serializers.Serializer):
    fullName = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6, required=False)
    role = serializers.ChoiceField(choices=User.Role.choices)
    studentId = serializers.CharField(required=False, allow_blank=True)
    department = serializers.CharField(required=False, allow_blank=True)
    hostelBlock = serializers.CharField(required=False, allow_blank=True)
    cafeteriaName = serializers.CharField(required=False, allow_blank=True)
    businessTag = serializers.CharField(required=False, allow_blank=True)
    deliveryMode = serializers.CharField(required=False, allow_blank=True)
    pickupZone = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        cafeteria_name = validated_data.get("cafeteriaName", "")
        vendor = None
        if validated_data["role"] == User.Role.VENDOR and cafeteria_name:
            vendor = Vendor.objects.filter(name__iexact=cafeteria_name).first()

        # A password is optional for the demo; default keeps quick-login working.
        password = validated_data.get("password") or "123456"

        user = User.objects.create_user(
            email=validated_data["email"],
            password=password,
            full_name=validated_data["fullName"],
            phone=validated_data.get("phone", ""),
            role=validated_data["role"],
            vendor=vendor,
            student_id=validated_data.get("studentId", ""),
            department=validated_data.get("department", ""),
            hostel_block=validated_data.get("hostelBlock", ""),
            cafeteria_name=cafeteria_name,
            business_tag=validated_data.get("businessTag", ""),
            delivery_mode=validated_data.get("deliveryMode", ""),
            pickup_zone=validated_data.get("pickupZone", ""),
            latitude=validated_data.get("latitude"),
            longitude=validated_data.get("longitude"),
            is_verified=False,
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")
        attrs["user"] = user
        return attrs


class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)


class ResendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()

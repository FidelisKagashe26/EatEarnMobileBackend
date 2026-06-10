import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_verified", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Single user model for every role in the campus app."""

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        VENDOR = "vendor", "Vendor"
        DELIVERY = "delivery", "Delivery"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

    # A vendor-role account is linked to the cafeteria/vendor it manages.
    vendor = models.ForeignKey(
        "catalog.Vendor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="managers",
    )

    # Student profile
    student_id = models.CharField(max_length=60, blank=True)
    department = models.CharField(max_length=120, blank=True)
    hostel_block = models.CharField(max_length=120, blank=True)

    # Vendor profile extras
    cafeteria_name = models.CharField(max_length=120, blank=True)
    business_tag = models.CharField(max_length=120, blank=True)

    # Delivery profile
    delivery_mode = models.CharField(max_length=40, blank=True)
    pickup_zone = models.CharField(max_length=120, blank=True)

    # Saved default location (used to pre-fill the map picker)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    is_verified = models.BooleanField(default=False)  # OTP confirmed
    # Vendors & delivery agents need admin approval before they can operate.
    # Customers (students) and admins are approved automatically.
    is_approved = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.full_name} <{self.email}> ({self.role})"


class EmailOTP(models.Model):
    """One-time code used to confirm a registration / login."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, default="register")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def issue(cls, user, purpose="register"):
        # Invalidate previous unused codes for the same purpose.
        cls.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
        code = f"{random.randint(0, 999999):06d}"
        ttl = getattr(settings, "OTP_TTL_MINUTES", 10)
        return cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=ttl),
        )

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP {self.code} for {self.user.email}"

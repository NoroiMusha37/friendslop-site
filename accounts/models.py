from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.utils import timezone


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("approved_at", timezone.now())
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Admin = `is_superuser`. Pending = `approved_at` is null. Banned = approved but not `is_active`."""

    first_name = None
    last_name = None
    email = models.EmailField(unique=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    @property
    def status(self):
        if self.approved_at is None:
            return "pending"
        return "active" if self.is_active else "banned"

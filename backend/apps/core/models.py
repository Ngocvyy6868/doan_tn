from django.conf import settings
from django.db import models


class Customer(models.Model):
    """Customer profile kept separately from Django's authentication user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.full_name} ({self.user.email})'

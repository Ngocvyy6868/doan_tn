from django.urls import path

from .views import customers, health, register

urlpatterns = [
    path('health/', health, name='health'),
    path('auth/register/', register, name='register'),
    path('admin/customers/', customers, name='admin-customers'),
]

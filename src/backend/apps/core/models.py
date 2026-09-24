from django.conf import settings
from django.db import models


class Customer(models.Model):
    """Customer profile kept separately from Django's authentication user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15, unique=True)
    avatar_url = models.URLField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.full_name} ({self.user.email})'


class Address(models.Model):
    """FR-ADDR-01: delivery address owned by a single customer account."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    province_code = models.CharField(max_length=20)
    province_name = models.CharField(max_length=150)
    ward_code = models.CharField(max_length=20)
    ward_name = models.CharField(max_length=150)
    detail = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.full_name} - {self.detail}'


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ProductAttribute(models.Model):
    name = models.CharField(max_length=100, unique=True)
    values = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    external_id = models.CharField(max_length=64, unique=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name='products')
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.payload.get('name', self.external_id)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'PENDING_PAYMENT', 'Chờ thanh toán'
        CONFIRMED = 'CONFIRMED', 'Đã xác nhận'
        PACKING = 'PACKING', 'Đang đóng gói'
        DELIVERING = 'DELIVERING', 'Đang giao'
        DELIVERED = 'DELIVERED', 'Đã giao'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    code = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    handler = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='handled_orders')
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.CONFIRMED)
    payment_status = models.CharField(max_length=20, default='UNPAID')
    payment_method = models.CharField(max_length=30)
    shipping_method = models.CharField(max_length=30)
    recipient_name = models.CharField(max_length=150)
    recipient_phone = models.CharField(max_length=15)
    province = models.CharField(max_length=100)
    address = models.TextField()
    subtotal = models.BigIntegerField(default=0)
    shipping_fee = models.BigIntegerField(default=0)
    grand_total = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_external_id = models.CharField(max_length=64)
    sku = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    image = models.URLField(blank=True)
    unit_price = models.BigIntegerField()
    quantity = models.PositiveIntegerField()
    total = models.BigIntegerField()

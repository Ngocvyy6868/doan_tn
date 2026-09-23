from django.urls import path

from .views import admin_orders, categories, create_order, customers, health, product_attributes, products, register

urlpatterns = [
    path('health/', health, name='health'),
    path('auth/register/', register, name='register'),
    path('admin/customers/', customers, name='admin-customers'),
    path('admin/categories/', categories, name='admin-categories'),
    path('admin/product-attributes/', product_attributes, name='admin-product-attributes'),
    path('admin/products/', products, name='admin-products'),
    path('orders/', create_order, name='create-order'),
    path('admin/orders/', admin_orders, name='admin-orders'),
    path('admin/orders/<int:order_id>/', admin_orders, name='admin-order-update'),
]

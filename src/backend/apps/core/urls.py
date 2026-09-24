from django.urls import path

from .views import (
    address_detail, addresses, admin_orders, categories, create_order, customers, health, login, logout,
    product_attributes, products, profile, register,
)

urlpatterns = [
    path('health/', health, name='health'),
    path('auth/register/', register, name='register'),
    path('auth/login/', login, name='login'),
    path('auth/logout/', logout, name='logout'),
    path('account/profile/', profile, name='profile'),
    path('addresses/', addresses, name='addresses'),
    path('addresses/<int:address_id>/', address_detail, name='address-detail'),
    path('admin/customers/', customers, name='admin-customers'),
    path('admin/categories/', categories, name='admin-categories'),
    path('admin/product-attributes/', product_attributes, name='admin-product-attributes'),
    path('admin/products/', products, name='admin-products'),
    path('orders/', create_order, name='create-order'),
    path('admin/orders/', admin_orders, name='admin-orders'),
    path('admin/orders/<int:order_id>/', admin_orders, name='admin-order-update'),
]

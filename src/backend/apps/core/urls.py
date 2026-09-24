from django.urls import path
from .management_views import employees, documents
from .compatibility_views import compatibility_rules
from .report_views import overview
from .flash_views import flash_sales

from .views import (
    address_detail, addresses, admin_orders, categories, create_order, customers, health, login, logout,
    product_attributes, products, profile, register, order_status,
)

urlpatterns = [
    path('admin/flash-sales/', flash_sales, name='admin-flash-sales'),
    path('admin/flash-sales/<int:sale_id>/', flash_sales, name='admin-flash-sale-detail'),
    path('flash-sales/', flash_sales, {'public': True}, name='flash-sales'),
    path('admin/overview/', overview, name='admin-overview'),
    path('compatibility-rules/', compatibility_rules, name='compatibility-rules'),
    path('compatibility-rules/<int:rule_id>/', compatibility_rules, name='compatibility-rule-detail'),
    path('admin/employees/', employees, name='admin-employees'),
    path('admin/employees/<int:employee_id>/', employees, name='admin-employee-detail'),
    path('admin/documents/', documents, name='admin-documents'),
    path('admin/documents/<int:document_id>/', documents, name='admin-document-detail'),
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
    path('orders/status/', order_status, name='order-status'),
    path('admin/orders/', admin_orders, name='admin-orders'),
    path('admin/orders/<int:order_id>/', admin_orders, name='admin-order-update'),
]

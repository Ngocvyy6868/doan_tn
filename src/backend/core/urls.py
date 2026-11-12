from django.urls import path
from .advisor_views import sessions, validate_build
from .customer_views import customer_orders, admin_session
from .crm_views import customer_events, customer_notes, customer_profile, customer_tasks
from .management_views import employees, documents
from .compatibility_views import compatibility_rules
from .report_views import overview
from .flash_views import flash_sales
from .inventory_views import inventory, product_availability, warehouses
from .chat_views import chat
from .catalog_views import edit_category, edit_product_attribute, product_image, upload_product_image

from .views import (
    address_detail, addresses, admin_orders, categories, create_order, customers, health, login, logout,
    product_attributes, products, profile, register, order_status,
)

urlpatterns = [
    path('admin/session/', admin_session, name='admin-session'),
    path('admin/categories/rename/', edit_category, name='edit-category'),
    path('admin/product-images/', upload_product_image, name='upload-product-image'),
    path('product-images/<int:image_id>/', product_image, name='product-image'),
    path('admin/product-attributes/<int:attribute_id>/', edit_product_attribute, name='edit-product-attribute'),
    path('chat/', chat, name='chat'),
    path('chat/sessions/', sessions, name='chat-sessions'),
    path('chat/sessions/<int:session_id>/', sessions, name='chat-session-detail'),
    path('advisor/validate/', validate_build, name='advisor-validate'),
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
    path('admin/warehouses/', warehouses, name='admin-warehouses'),
    path('admin/warehouses/<int:warehouse_id>/', warehouses, name='admin-warehouse-detail'),
    path('admin/inventory/', inventory, name='admin-inventory'),
    path('products/<str:product_id>/availability/', product_availability, name='product-availability'),
    path('auth/register/', register, name='register'),
    path('auth/login/', login, name='login'),
    path('auth/logout/', logout, name='logout'),
    path('account/profile/', profile, name='profile'),
    path('addresses/', addresses, name='addresses'),
    path('addresses/<int:address_id>/', address_detail, name='address-detail'),
    path('admin/customers/', customers, name='admin-customers'),
    path('admin/customers/<int:customer_id>/addresses/', addresses, name='admin-customer-addresses'),
    path('admin/customers/<int:customer_id>/addresses/<int:address_id>/', address_detail, name='admin-customer-address-detail'),
    path('admin/customers/<int:customer_id>/orders/', customer_orders, name='admin-customer-orders'),
    path('admin/customers/<int:customer_id>/profile/', customer_profile, name='admin-customer-profile'),
    path('admin/customers/<int:customer_id>/events/', customer_events, name='admin-customer-events'),
    path('admin/customers/<int:customer_id>/notes/', customer_notes, name='admin-customer-notes'),
    path('admin/customers/<int:customer_id>/notes/<int:note_id>/', customer_notes, name='admin-customer-note-detail'),
    path('admin/customers/<int:customer_id>/tasks/', customer_tasks, name='admin-customer-tasks'),
    path('admin/customers/<int:customer_id>/tasks/<int:task_id>/', customer_tasks, name='admin-customer-task-detail'),
    path('admin/categories/', categories, name='admin-categories'),
    path('admin/product-attributes/', product_attributes, name='admin-product-attributes'),
    path('admin/products/', products, name='admin-products'),
    path('orders/', create_order, name='create-order'),
    path('orders/status/', order_status, name='order-status'),
    path('admin/orders/', admin_orders, name='admin-orders'),
    path('admin/orders/<int:order_id>/', admin_orders, name='admin-order-update'),
]

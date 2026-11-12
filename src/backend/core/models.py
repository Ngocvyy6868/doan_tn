from django.conf import settings
from django.db import models
from django.utils import timezone
from .advisor.fields import ProductVectorField


class Employee(models.Model):
    class Role(models.TextChoices):
        WAREHOUSE = 'WAREHOUSE', 'Nhân viên kho'
        ORDER_PROCESSOR = 'ORDER_PROCESSOR', 'Nhân viên xử lý'

    role = models.CharField(max_length=24, choices=Role.choices, default=Role.ORDER_PROCESSOR)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class KnowledgeDocument(models.Model):
    name = models.CharField(max_length=255)
    content = models.BinaryField()
    text = models.TextField()
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


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


class FlashSale(models.Model):
    product_external_id = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField()
    sold = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    active = models.BooleanField(default=True)


class CompatibilityRule(models.Model):
    name = models.CharField(max_length=150)
    source_category = models.CharField(max_length=100)
    source_attribute = models.CharField(max_length=100)
    target_category = models.CharField(max_length=100)
    target_attribute = models.CharField(max_length=100)
    operator = models.CharField(max_length=12)
    active = models.BooleanField(default=True)


class ProductImage(models.Model):
    content = models.BinaryField()
    content_type = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)


class Product(models.Model):
    external_id = models.CharField(max_length=64, unique=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name='products')
    payload = models.JSONField(default=dict)
    embedding = ProductVectorField(null=True, editable=False)
    embedding_hash = models.CharField(max_length=64, blank=True, default='', editable=False)
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
    # Kho đã trừ tồn khi đặt hàng: [{"warehouse_id": id|None, "quantity": n}]; None = tồn kho nhập tay.
    allocations = models.JSONField(default=list, blank=True)


class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='advisor_sessions')
    state = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=12)
    text = models.TextField()
    data = models.JSONField(default=dict)
    latency_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']


class CustomerEvent(models.Model):
    """CDP: một sự kiện trên dòng thời gian của khách hàng (khách tự làm, nhân viên làm hoặc hệ thống ghi)."""

    class Type(models.TextChoices):
        REGISTERED = 'REGISTERED', 'Đăng ký tài khoản'
        LOGIN = 'LOGIN', 'Đăng nhập'
        PROFILE_UPDATED = 'PROFILE_UPDATED', 'Cập nhật thông tin Profile'
        ADDRESS_ADDED = 'ADDRESS_ADDED', 'Thêm địa chỉ'
        ADDRESS_UPDATED = 'ADDRESS_UPDATED', 'Sửa địa chỉ'
        ADDRESS_DELETED = 'ADDRESS_DELETED', 'Xóa địa chỉ'
        ORDER_PLACED = 'ORDER_PLACED', 'Đặt đơn hàng'
        ORDER_STATUS = 'ORDER_STATUS', 'Cập nhật trạng thái đơn hàng'
        CHAT_STARTED = 'CHAT_STARTED', 'Trò chuyện với trợ lý AI'
        NOTE_ADDED = 'NOTE_ADDED', 'Thêm ghi chú'
        TASK_CREATED = 'TASK_CREATED', 'Tạo công việc'
        TASK_COMPLETED = 'TASK_COMPLETED', 'Hoàn thành công việc'

    class Source(models.TextChoices):
        CUSTOMER = 'customer', 'Khách hàng'
        STAFF = 'staff', 'Nhân viên'
        SYSTEM = 'system', 'Hệ thống'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='events')
    type = models.CharField(max_length=24, choices=Type.choices)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.CUSTOMER)
    title = models.CharField(max_length=255)
    data = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    # Không dùng auto_now_add để dựng lại được sự kiện cũ từ dữ liệu có sẵn (đăng ký, đơn hàng...).
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['customer', '-created_at'])]


class CustomerNote(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    content = models.TextField()
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pinned', '-created_at', '-id']


class CustomerTask(models.Model):
    """Công việc chăm sóc khách hàng: liên hệ, xử lý phản ánh, tư vấn..."""

    class Type(models.TextChoices):
        CONTACT = 'CONTACT', 'Liên hệ khách hàng'
        COMPLAINT = 'COMPLAINT', 'Xử lý phản ánh'
        CONSULT = 'CONSULT', 'Tư vấn'
        CARE = 'CARE', 'Chăm sóc sau bán'
        OTHER = 'OTHER', 'Khác'

    class Status(models.TextChoices):
        TODO = 'TODO', 'Cần làm'
        DONE = 'DONE', 'Hoàn thành'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='tasks')
    type = models.CharField(max_length=12, choices=Type.choices, default=Type.CONTACT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TODO)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    channel = models.CharField(max_length=20, blank=True, default='')  # phone, email, zalo, store...
    result = models.TextField(blank=True, default='')
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']


class Warehouse(models.Model):
    """Kho/cửa hàng giữ hàng; tồn kho tổng của sản phẩm = tổng các kho đang hoạt động."""
    code = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return self.code


class WarehouseStock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='warehouse_stocks')
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['warehouse', 'product'], name='unique_warehouse_product_stock')]

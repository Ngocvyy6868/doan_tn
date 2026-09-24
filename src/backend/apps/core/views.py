import json
import re

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Address, Category, Customer, Order, OrderItem, Product, ProductAttribute

LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', 'unknown')


def _serialize_account(user):
    customer = Customer.objects.filter(user=user).first()
    return {
        'id': user.id,
        'full_name': customer.full_name if customer else (user.get_full_name() or user.username),
        'email': user.email,
        'phone': customer.phone if customer else '',
        'avatar_url': customer.avatar_url if customer else '',
    }


def health(request):
    return JsonResponse({'status': 'ok'})


@require_GET
def customers(request):
    """Customer list consumed by the application admin dashboard."""
    records = Customer.objects.select_related('user').order_by('-created_at')
    return JsonResponse({'results': [
        {
            'id': customer.id,
            'full_name': customer.full_name,
            'email': customer.user.email,
            'phone': customer.phone,
            'created_at': customer.created_at.isoformat(),
        }
        for customer in records
    ]})


def _payload(request):
    try:
        return json.loads(request.body)
    except (TypeError, ValueError):
        return None


@csrf_exempt
def categories(request):
    if request.method == 'GET':
        return JsonResponse({'results': list(Category.objects.order_by('name').values('id', 'name'))})
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    data = _payload(request)
    if not isinstance(data, list) or any(not str(name).strip() for name in data):
        return JsonResponse({'message': 'Danh mục không hợp lệ.'}, status=400)
    names = list(dict.fromkeys(str(name).strip() for name in data))
    with transaction.atomic():
        Category.objects.exclude(name__in=names).delete()
        for name in names:
            Category.objects.get_or_create(name=name)
    return JsonResponse({'results': list(Category.objects.order_by('name').values('id', 'name'))})


@csrf_exempt
def product_attributes(request):
    if request.method == 'GET':
        return JsonResponse({'results': [
            {'id': str(item.id), 'name': item.name, 'values': item.values}
            for item in ProductAttribute.objects.order_by('name')
        ]})
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    data = _payload(request)
    if not isinstance(data, list):
        return JsonResponse({'message': 'Thuộc tính không hợp lệ.'}, status=400)
    normalized = []
    for item in data:
        name = str(item.get('name', '')).strip() if isinstance(item, dict) else ''
        values = item.get('values', []) if isinstance(item, dict) else []
        if not name or not isinstance(values, list):
            return JsonResponse({'message': 'Thuộc tính không hợp lệ.'}, status=400)
        normalized.append((name, [str(value).strip() for value in values if str(value).strip()]))
    with transaction.atomic():
        ProductAttribute.objects.exclude(name__in=[name for name, _ in normalized]).delete()
        for name, values in normalized:
            ProductAttribute.objects.update_or_create(name=name, defaults={'values': values})
    return JsonResponse({'results': [
        {'id': str(item.id), 'name': item.name, 'values': item.values}
        for item in ProductAttribute.objects.order_by('name')
    ]})


@csrf_exempt
def products(request):
    if request.method == 'GET':
        return JsonResponse({'results': [product.payload for product in Product.objects.order_by('-updated_at')]})
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    data = _payload(request)
    if not isinstance(data, list):
        return JsonResponse({'message': 'Sản phẩm không hợp lệ.'}, status=400)
    with transaction.atomic():
        Product.objects.all().delete()
        for item in data:
            if not isinstance(item, dict) or not item.get('id') or not str(item.get('name', '')).strip():
                return JsonResponse({'message': 'Sản phẩm không hợp lệ.'}, status=400)
            category_name = str(item.get('cat', '')).strip()
            category = Category.objects.filter(name=category_name).first() if category_name else None
            Product.objects.create(external_id=str(item['id']), category=category, payload=item)
    return JsonResponse({'results': [product.payload for product in Product.objects.order_by('-updated_at')]})


def _serialize_order(order):
    return {
        'id': order.id, 'code': order.code, 'status': order.status,
        'payment_status': order.payment_status, 'payment_method': order.payment_method,
        'shipping_method': order.shipping_method, 'recipient': {
            'name': order.recipient_name, 'phone': order.recipient_phone,
            'province': order.province, 'address': order.address,
        },
        'totals': {'subtotal': order.subtotal, 'shipping': order.shipping_fee, 'grand_total': order.grand_total},
        'handler': {'id': order.handler_id, 'name': order.handler.get_full_name() or order.handler.username} if order.handler else None,
        'created_at': order.created_at.isoformat(),
        'items': [{'product_id': item.product_external_id, 'sku': item.sku, 'name': item.name, 'image': item.image,
                   'price': item.unit_price, 'quantity': item.quantity, 'total': item.total} for item in order.items.all()],
    }


@csrf_exempt
@require_POST
def create_order(request):
    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Dữ liệu đơn hàng không hợp lệ.'}, status=400)
    recipient, totals, items = data.get('address', {}), data.get('totals', {}), data.get('items', [])
    required = ('name', 'phone', 'province', 'address')
    if not isinstance(items, list) or not items or any(not str(recipient.get(key, '')).strip() for key in required):
        return JsonResponse({'message': 'Thiếu thông tin đơn hàng.'}, status=400)
    code = str(data.get('code', '')).strip()
    if not code or Order.objects.filter(code=code).exists():
        return JsonResponse({'message': 'Mã đơn hàng không hợp lệ hoặc đã tồn tại.'}, status=400)
    customer = Customer.objects.filter(user=request.user).first() if request.user.is_authenticated else None
    with transaction.atomic():
        order = Order.objects.create(
            code=code, customer=customer, status=data.get('status', Order.Status.CONFIRMED),
            payment_status=data.get('payment_status', 'UNPAID'), payment_method=data.get('payment_method', 'COD'),
            shipping_method=data.get('shipping_method', 'standard'), recipient_name=recipient['name'].strip(),
            recipient_phone=recipient['phone'].strip(), province=recipient['province'].strip(), address=recipient['address'].strip(),
            subtotal=int(totals.get('subtotal', 0)), shipping_fee=int(totals.get('shipping', 0)), grand_total=int(totals.get('grand_total', 0)),
        )
        OrderItem.objects.bulk_create([OrderItem(order=order, product_external_id=str(item.get('productId', '')),
            sku=str(item.get('sku', '')), name=str(item.get('name', '')), image=str(item.get('img', '')),
            unit_price=int(item.get('price', 0)), quantity=int(item.get('quantity', 0)), total=int(item.get('total', 0))) for item in items])
    return JsonResponse({'order': _serialize_order(Order.objects.prefetch_related('items').get(pk=order.pk))}, status=201)


@csrf_exempt
def admin_orders(request, order_id=None):
    if request.method == 'GET' and order_id is None:
        records = Order.objects.select_related('handler').prefetch_related('items').order_by('-created_at')
        return JsonResponse({'results': [_serialize_order(order) for order in records]})
    if request.method == 'PATCH' and order_id is not None:
        data = _payload(request) or {}
        order = Order.objects.select_related('handler').prefetch_related('items').filter(pk=order_id).first()
        if not order:
            return JsonResponse({'message': 'Không tìm thấy đơn hàng.'}, status=404)
        status = data.get('status')
        if status in Order.Status.values:
            order.status = status
        handler_name = str(data.get('handler_name', '')).strip()
        if handler_name:
            if request.user.is_authenticated:
                order.handler = request.user
            else:
                order.handler, _ = User.objects.get_or_create(username=handler_name, defaults={'first_name': handler_name})
        order.save()
        return JsonResponse({'order': _serialize_order(order)})
    return JsonResponse({'message': 'Method not allowed.'}, status=405)


@csrf_exempt
@require_POST
def register(request):
    """FR-AUTH-01: create an account from the public registration form."""
    try:
        payload = json.loads(request.body)
    except (TypeError, json.JSONDecodeError):
        return JsonResponse({'message': 'Dữ liệu gửi lên không hợp lệ.'}, status=400)

    full_name = str(payload.get('full_name', '')).strip()
    email = str(payload.get('email', '')).strip().lower()
    phone = str(payload.get('phone', '')).strip()
    password = str(payload.get('password', ''))
    password_confirmation = str(payload.get('password_confirmation', ''))
    errors = {}
    if not full_name:
        errors['full_name'] = 'Vui lòng nhập họ và tên.'
    if not email or '@' not in email:
        errors['email'] = 'Vui lòng nhập email hợp lệ.'
    elif User.objects.filter(email__iexact=email).exists():
        errors['email'] = 'Email này đã được đăng ký.'
    if not re.fullmatch(r'(?:0|\+84)\d{9}', phone):
        errors['phone'] = 'Vui lòng nhập số điện thoại Việt Nam hợp lệ.'
    elif Customer.objects.filter(phone=phone).exists():
        errors['phone'] = 'Số điện thoại này đã được đăng ký.'
    if password != password_confirmation:
        errors['password_confirmation'] = 'Mật khẩu xác nhận không khớp.'
    if not errors:
        try:
            validate_password(password)
        except ValidationError as error:
            errors['password'] = list(error.messages)
    if errors:
        return JsonResponse({'message': 'Thông tin đăng ký chưa hợp lệ.', 'errors': errors}, status=400)

    first_name, *remaining_name = full_name.split()
    with transaction.atomic():
        user = User.objects.create_user(username=email, email=email, password=password,
                                        first_name=first_name, last_name=' '.join(remaining_name))
        Customer.objects.create(user=user, full_name=full_name, phone=phone)
    auth_login(request, user)
    return JsonResponse({'message': 'Đăng ký tài khoản thành công.',
                         'user': _serialize_account(user)}, status=201)


@csrf_exempt
@require_POST
def login(request):
    """FR-AUTH-02: authenticate by password with a generic error and rate limiting."""
    payload = _payload(request)
    if not isinstance(payload, dict):
        return JsonResponse({'message': 'Dữ liệu gửi lên không hợp lệ.'}, status=400)

    email = str(payload.get('email', '')).strip().lower()
    password = str(payload.get('password', ''))
    generic_error = {'message': 'Email hoặc mật khẩu không đúng.'}

    rate_key = f'login-attempts:{_client_ip(request)}:{email}'
    if cache.get(rate_key, 0) >= LOGIN_RATE_LIMIT_ATTEMPTS:
        return JsonResponse({'message': 'Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau ít phút.'}, status=429)

    if not email or not password:
        return JsonResponse(generic_error, status=400)

    user = authenticate(request, username=email, password=password)
    if user is None or not user.is_active:
        cache.set(rate_key, cache.get(rate_key, 0) + 1, LOGIN_RATE_LIMIT_WINDOW_SECONDS)
        return JsonResponse(generic_error, status=400)

    cache.delete(rate_key)
    auth_login(request, user)
    return JsonResponse({'message': 'Đăng nhập thành công.', 'user': _serialize_account(user)})


@csrf_exempt
@require_POST
def logout(request):
    """FR-AUTH-02: invalidate the current session."""
    auth_logout(request)
    return JsonResponse({'message': 'Đã đăng xuất.'})


def _serialize_address(address):
    return {
        'id': address.id,
        'fullName': address.full_name,
        'phone': address.phone,
        'provinceCode': address.province_code,
        'provinceName': address.province_name,
        'wardCode': address.ward_code,
        'wardName': address.ward_name,
        'detail': address.detail,
        'isDefault': address.is_default,
    }


def _owned_customer(request):
    if not request.user.is_authenticated:
        return None
    return Customer.objects.filter(user=request.user).first()


@csrf_exempt
def profile(request):
    """FR-ACC-01: view and edit the account's basic profile information."""
    customer = _owned_customer(request)
    if customer is None:
        return JsonResponse({'message': 'Vui lòng đăng nhập để xem thông tin tài khoản.'}, status=401)
    user = customer.user

    if request.method == 'GET':
        return JsonResponse({'user': _serialize_account(user)})
    if request.method != 'PATCH':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)

    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Dữ liệu gửi lên không hợp lệ.'}, status=400)

    full_name = str(data.get('full_name', customer.full_name)).strip()
    email = str(data.get('email', user.email)).strip().lower()
    phone = str(data.get('phone', customer.phone)).strip()
    avatar_url = str(data.get('avatar_url', customer.avatar_url)).strip()

    errors = {}
    if not full_name:
        errors['full_name'] = 'Vui lòng nhập họ và tên.'
    if not email or '@' not in email:
        errors['email'] = 'Vui lòng nhập email hợp lệ.'
    elif User.objects.exclude(pk=user.pk).filter(email__iexact=email).exists():
        errors['email'] = 'Email này đã được sử dụng.'
    if not re.fullmatch(r'(?:0|\+84)\d{9}', phone):
        errors['phone'] = 'Vui lòng nhập số điện thoại Việt Nam hợp lệ.'
    elif Customer.objects.exclude(pk=customer.pk).filter(phone=phone).exists():
        errors['phone'] = 'Số điện thoại này đã được sử dụng.'
    if errors:
        return JsonResponse({'message': 'Thông tin chưa hợp lệ.', 'errors': errors}, status=400)

    identity_changed = email != user.email.lower() or phone != customer.phone
    if identity_changed:
        current_password = str(data.get('current_password', ''))
        if not current_password or not user.check_password(current_password):
            return JsonResponse({'message': 'Mật khẩu hiện tại không đúng. Vui lòng xác nhận lại để đổi email/số điện thoại.'}, status=400)

    with transaction.atomic():
        user.email = email
        user.username = email
        first_name, *remaining_name = full_name.split()
        user.first_name = first_name
        user.last_name = ' '.join(remaining_name)
        user.save()
        customer.full_name = full_name
        customer.phone = phone
        customer.avatar_url = avatar_url
        customer.save()

    return JsonResponse({'message': 'Đã cập nhật thông tin tài khoản.', 'user': _serialize_account(user)})


def _validate_address_fields(full_name, phone, province_code, ward_code, detail):
    return bool(full_name) and bool(re.fullmatch(r'0\d{9}', phone)) and bool(province_code) and bool(ward_code) and bool(detail)


@csrf_exempt
def addresses(request):
    """FR-ADDR-01: address book scoped to the authenticated account only."""
    customer = _owned_customer(request)
    if customer is None:
        return JsonResponse({'message': 'Vui lòng đăng nhập để quản lý sổ địa chỉ.'}, status=401)

    if request.method == 'GET':
        return JsonResponse({'results': [_serialize_address(a) for a in customer.addresses.all()]})
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)

    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Dữ liệu địa chỉ không hợp lệ.'}, status=400)

    full_name = str(data.get('fullName', '')).strip()
    phone = str(data.get('phone', '')).strip()
    province_code = str(data.get('provinceCode', '')).strip()
    province_name = str(data.get('provinceName', '')).strip()
    ward_code = str(data.get('wardCode', '')).strip()
    ward_name = str(data.get('wardName', '')).strip()
    detail = str(data.get('detail', '')).strip()
    if not _validate_address_fields(full_name, phone, province_code, ward_code, detail):
        return JsonResponse({'message': 'Vui lòng nhập đầy đủ thông tin và số điện thoại hợp lệ.'}, status=400)

    make_default = bool(data.get('isDefault')) or not customer.addresses.exists()
    with transaction.atomic():
        if make_default:
            customer.addresses.update(is_default=False)
        address = customer.addresses.create(
            full_name=full_name, phone=phone, province_code=province_code, province_name=province_name,
            ward_code=ward_code, ward_name=ward_name, detail=detail, is_default=make_default,
        )
    return JsonResponse({'result': _serialize_address(address)}, status=201)


@csrf_exempt
def address_detail(request, address_id):
    """FR-ADDR-01: only the owning account may edit or delete its own address."""
    customer = _owned_customer(request)
    if customer is None:
        return JsonResponse({'message': 'Vui lòng đăng nhập để quản lý sổ địa chỉ.'}, status=401)
    address = customer.addresses.filter(pk=address_id).first()
    if address is None:
        return JsonResponse({'message': 'Không tìm thấy địa chỉ.'}, status=404)

    if request.method == 'PATCH':
        data = _payload(request)
        if not isinstance(data, dict):
            return JsonResponse({'message': 'Dữ liệu địa chỉ không hợp lệ.'}, status=400)
        field_map = (
            ('full_name', 'fullName'), ('phone', 'phone'), ('province_code', 'provinceCode'),
            ('province_name', 'provinceName'), ('ward_code', 'wardCode'), ('ward_name', 'wardName'),
            ('detail', 'detail'),
        )
        for model_field, payload_key in field_map:
            if payload_key in data:
                setattr(address, model_field, str(data[payload_key]).strip())
        if not _validate_address_fields(address.full_name, address.phone, address.province_code, address.ward_code, address.detail):
            return JsonResponse({'message': 'Vui lòng nhập đầy đủ thông tin và số điện thoại hợp lệ.'}, status=400)

        make_default = bool(data.get('isDefault', address.is_default))
        with transaction.atomic():
            if make_default:
                customer.addresses.exclude(pk=address.pk).update(is_default=False)
            address.is_default = make_default
            address.save()
            if not customer.addresses.filter(is_default=True).exists():
                fallback = customer.addresses.order_by('created_at').first()
                if fallback:
                    fallback.is_default = True
                    fallback.save(update_fields=['is_default'])
        return JsonResponse({'result': _serialize_address(customer.addresses.get(pk=address.pk))})

    if request.method == 'DELETE':
        if customer.addresses.count() <= 1:
            return JsonResponse({'message': 'Cần giữ lại ít nhất một địa chỉ để sử dụng khi thanh toán.'}, status=400)
        was_default = address.is_default
        address.delete()
        if was_default:
            fallback = customer.addresses.order_by('-created_at').first()
            if fallback:
                fallback.is_default = True
                fallback.save(update_fields=['is_default'])
        return JsonResponse({'message': 'Đã xóa địa chỉ.'})

    return JsonResponse({'message': 'Method not allowed.'}, status=405)

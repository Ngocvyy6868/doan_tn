import json
import re

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Customer


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
        customer = Customer.objects.create(user=user, full_name=full_name, phone=phone)
    login(request, user)
    return JsonResponse({'message': 'Đăng ký tài khoản thành công.',
                         'user': {'id': user.id, 'full_name': customer.full_name,
                                  'email': user.email, 'phone': customer.phone}}, status=201)

import io
import json
import warnings

from PIL import Image, UnidentifiedImageError
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import Category, CompatibilityRule, Product, ProductAttribute, ProductImage


@csrf_exempt
@require_http_methods(['PATCH'])
def edit_category(request):
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        data = None
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Danh mục không hợp lệ.'}, status=400)
    old_name, name = data.get('old_name'), data.get('name')
    if any(not isinstance(value, str) or not value.strip() or len(value.strip()) > 100 for value in [old_name, name]):
        return JsonResponse({'message': 'Tên danh mục phải có từ 1 đến 100 ký tự.'}, status=400)
    old_name, name = old_name.strip(), name.strip()
    with transaction.atomic():
        category = Category.objects.select_for_update().filter(name=old_name).first()
        if Category.objects.exclude(pk=category.pk if category else None).filter(name__iexact=name).exists():
            return JsonResponse({'message': 'Tên danh mục đã tồn tại.'}, status=400)
        # The demo catalog may still contain categories that have not been saved yet.
        if category is None:
            category = Category.objects.create(name=old_name)
        category.name = name
        category.save(update_fields=['name'])
        for product in Product.objects.select_for_update():
            if product.category_id == category.pk or product.payload.get('cat') == old_name:
                product.category = category
                product.payload['cat'] = name
                product.save(update_fields=['category', 'payload', 'updated_at'])
        CompatibilityRule.objects.filter(source_category=old_name).update(source_category=name)
        CompatibilityRule.objects.filter(target_category=old_name).update(target_category=name)
    return JsonResponse({'category': {'id': category.pk, 'name': name}})


@csrf_exempt
@require_POST
def upload_product_image(request):
    upload = request.FILES.get('file')
    if not upload or upload.size > 5 * 1024 * 1024:
        return JsonResponse({'message': 'Chọn ảnh JPG, PNG hoặc WebP tối đa 5 MB.'}, status=400)
    content = upload.read()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                content_type = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}.get(image.format)
                if not content_type:
                    raise ValueError('Unsupported image')
                image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return JsonResponse({'message': 'Ảnh không hợp lệ. Chỉ hỗ trợ JPG, PNG và WebP.'}, status=400)
    stored = ProductImage.objects.create(content=content, content_type=content_type)
    url = request.build_absolute_uri(reverse('product-image', args=[stored.pk]))
    return JsonResponse({'url': url}, status=201)


@require_GET
def product_image(request, image_id):
    image = get_object_or_404(ProductImage, pk=image_id)
    response = HttpResponse(bytes(image.content), content_type=image.content_type)
    response['Cache-Control'] = 'public, max-age=31536000, immutable'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@csrf_exempt
@require_http_methods(['PATCH'])
def edit_product_attribute(request, attribute_id):
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        data = None
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Thuộc tính không hợp lệ.'}, status=400)
    name, values = data.get('name'), data.get('values')
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100 or not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        return JsonResponse({'message': 'Nhập tên thuộc tính và danh sách giá trị hợp lệ.'}, status=400)
    name = name.strip()
    with transaction.atomic():
        attribute = get_object_or_404(ProductAttribute.objects.select_for_update(), pk=attribute_id)
        if ProductAttribute.objects.exclude(pk=attribute.pk).filter(name__iexact=name).exists():
            return JsonResponse({'message': 'Tên thuộc tính đã tồn tại.'}, status=400)
        old_name = attribute.name
        attribute.name = name
        attribute.values = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        attribute.save(update_fields=['name', 'values'])
        if old_name != name:
            for product in Product.objects.select_for_update():
                changed = False
                for item in product.payload.get('attributes', []):
                    if item.get('name') == old_name:
                        item['name'] = name
                        changed = True
                if changed:
                    product.save(update_fields=['payload', 'updated_at'])
            CompatibilityRule.objects.filter(source_attribute=old_name).update(source_attribute=name)
            CompatibilityRule.objects.filter(target_attribute=old_name).update(target_attribute=name)
    return JsonResponse({'attribute': {'id': str(attribute.pk), 'name': attribute.name, 'values': attribute.values}})

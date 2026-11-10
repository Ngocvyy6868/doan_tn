"""Re-read prices/stock and recheck rules for cart edits and chat proposals."""
from .catalog import adapt, available, number
from .rules import blocked, check_build
from ..models import Product

BUILD_CATEGORIES = {'cpu', 'mainboard', 'ram', 'gpu', 'cooler', 'ssd', 'psu', 'case'}


def validate_cart(items):
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        raise ValueError('Giỏ cần từ 1 đến 20 dòng sản phẩm.')
    quantities = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or type(item.get('quantity')) is not int or not 1 <= item['quantity'] <= 99:
            raise ValueError('Mã sản phẩm hoặc số lượng không hợp lệ.')
        key = item['id']
        quantities[key] = quantities.get(key, 0) + item['quantity']
    products, checks, errors, cats = [], [], [], set()
    records = {p.external_id: p for p in Product.objects.select_related('category').defer('embedding').filter(external_id__in=quantities)}
    for key, quantity in quantities.items():
        record = records.get(key)
        if not record:
            errors.append('Sản phẩm không còn tồn tại: ' + key)
            continue
        p = adapt(record)
        if not available(p) or p['stock'] < quantity:
            errors.append('Không đủ tồn kho: ' + p.get('name', key))
        if p['cat'] in cats and p['cat'] in BUILD_CATEGORIES:
            errors.append('Có nhiều sản phẩm cùng nhóm: ' + p['cat'])
        cats.add(p['cat'])
        p['quantity'] = quantity
        if quantity > 1:
            if p['cat'] == 'ram':
                p['specs'] = dict(p['specs'])
                for field in ('modules', 'capacity_gb'):
                    amount = number(p['specs'].get(field))
                    p['specs'][field] = amount * quantity if amount is not None else None
            elif p['cat'] in BUILD_CATEGORIES:
                errors.append('Một cấu hình chỉ dùng một sản phẩm mỗi nhóm, ngoại trừ RAM.')
        products.append(p)
    checks = check_build(products)
    return {'products': products, 'checks': checks, 'errors': errors,
            'total': sum(p['price'] * p['quantity'] for p in products if available(p)),
            'can_add_to_cart': not errors and not blocked(checks)}

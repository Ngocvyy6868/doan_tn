"""Thêm thuộc tính điện năng để tính công suất nguồn trong Build PC.

- "TDP" (W): điện năng tiêu thụ của mọi linh kiện; "Công suất" (W): công suất của bộ nguồn.
- Điền sẵn từ specs.tdp_w / specs.watt. Linh kiện chưa có số liệu dùng mức tiêu thụ ước tính
  theo danh mục (admin sửa được). specs.tdp_w của tản nhiệt là khả năng tản nhiệt, không phải
  điện năng tiêu thụ, nên tản nhiệt dùng mức ước tính.
"""
from django.db import migrations

TDP, PSU_WATT = 'TDP', 'Công suất'
PSU_CATEGORY = 'Nguồn'
SPEC_TDP_CATEGORIES = {'CPU', 'VGA'}
# Mức tiêu thụ điển hình (W) cho linh kiện chưa có thông số.
ESTIMATED_TDP = {'Mainboard': 50, 'RAM': 5, 'SSD': 7, 'HDD': 8, 'hdd': 8, 'Case': 10, 'Tản nhiệt': 10}


def _number(value):
    try:
        number = float(str(value).strip().replace(',', '.').rstrip('Ww').strip())
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return int(number) if number.is_integer() else number


def seed(apps, schema_editor):
    ProductAttribute = apps.get_model('core', 'ProductAttribute')
    Product = apps.get_model('core', 'Product')
    for name in (TDP, PSU_WATT):
        ProductAttribute.objects.get_or_create(name=name, defaults={'values': []})

    for product in Product.objects.defer('embedding').iterator():
        payload = product.payload or {}
        cat, specs = payload.get('cat'), payload.get('specs') or {}
        if cat == PSU_CATEGORY:
            name, value = PSU_WATT, _number(specs.get('watt'))
        elif cat in SPEC_TDP_CATEGORIES:
            name, value = TDP, _number(specs.get('tdp_w'))
        elif cat in ESTIMATED_TDP:
            name, value = TDP, ESTIMATED_TDP[cat]
        else:
            continue
        attributes = list(payload.get('attributes') or [])
        existing = next((a for a in attributes if str(a.get('name', '')).strip().lower() == name.lower()), None)
        if existing is not None and str(existing.get('value', '')).strip():
            continue
        if value is None:
            continue
        entry = {'name': name, 'value': str(value), 'unit': 'W'}
        if existing is not None:
            attributes[attributes.index(existing)] = entry
        else:
            attributes.append(entry)
        payload['attributes'] = attributes
        product.payload = payload
        product.save(update_fields=['payload'])


def unseed(apps, schema_editor):
    apps.get_model('core', 'ProductAttribute').objects.filter(name__in=[TDP, PSU_WATT]).delete()


class Migration(migrations.Migration):
    dependencies = [('core', '0017_orderitem_allocations')]

    operations = [migrations.RunPython(seed, unseed)]

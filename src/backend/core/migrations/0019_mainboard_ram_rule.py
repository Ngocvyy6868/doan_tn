"""Luật Build PC: thế hệ RAM phải nằm trong các thế hệ RAM mainboard hỗ trợ (board chỉ chạy DDR4 hoặc DDR5).

- Thêm luật Mainboard "Thế hệ RAM hỗ trợ" overlap RAM "Thế hệ RAM" (giống luật CPU).
- Điền sẵn "Thế hệ RAM hỗ trợ" (CPU, Mainboard) và "Thế hệ RAM" (RAM) từ specs.ram_type cho sản phẩm
  chưa có giá trị; giá trị admin đã nhập được giữ nguyên.
"""
from django.db import migrations

SUPPORTED, RAM_GEN = 'Thế hệ RAM hỗ trợ', 'Thế hệ RAM'
ATTRIBUTE_BY_CATEGORY = {'CPU': SUPPORTED, 'Mainboard': SUPPORTED, 'RAM': RAM_GEN}
RULE = {'source_category': 'Mainboard', 'source_attribute': SUPPORTED,
        'target_category': 'RAM', 'target_attribute': RAM_GEN}


def ram_generations(value):
    # "DDR4/DDR5" -> "DDR4, DDR5": luật overlap tách giá trị theo dấu phẩy.
    parts = [p.strip().upper() for p in str(value or '').replace(',', '/').split('/') if p.strip()]
    return ', '.join(parts)


def seed(apps, schema_editor):
    ProductAttribute = apps.get_model('core', 'ProductAttribute')
    for name in (SUPPORTED, RAM_GEN):
        ProductAttribute.objects.get_or_create(name=name, defaults={'values': ['DDR4', 'DDR5']})
    apps.get_model('core', 'CompatibilityRule').objects.get_or_create(
        **RULE, defaults={'name': 'Thế hệ RAM và Mainboard', 'operator': 'overlap', 'active': True})

    for product in apps.get_model('core', 'Product').objects.defer('embedding').iterator():
        payload = product.payload or {}
        name = ATTRIBUTE_BY_CATEGORY.get(payload.get('cat'))
        value = ram_generations((payload.get('specs') or {}).get('ram_type'))
        if not name or not value:
            continue
        attributes = list(payload.get('attributes') or [])
        existing = next((a for a in attributes if str(a.get('name', '')).strip().lower() == name.lower()), None)
        if existing is not None and str(existing.get('value', '')).strip():
            continue
        if existing is not None:
            attributes.remove(existing)
        payload['attributes'] = attributes + [{'name': name, 'value': value}]
        product.payload = payload
        product.save(update_fields=['payload'])


def unseed(apps, schema_editor):
    apps.get_model('core', 'CompatibilityRule').objects.filter(**RULE).delete()


class Migration(migrations.Migration):
    dependencies = [('core', '0018_power_attributes')]

    operations = [migrations.RunPython(seed, unseed)]

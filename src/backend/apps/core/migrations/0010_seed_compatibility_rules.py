from django.db import migrations

ATTRIBUTE_DEFINITIONS = [
    ('Socket', ['AM5', 'AM4', 'LGA1700', 'LGA1200']),
    ('Khe RAM', ['DDR4', 'DDR5']),
    ('Thế hệ RAM hỗ trợ', ['DDR4', 'DDR5']),
    ('Thế hệ RAM', ['DDR4', 'DDR5']),
    ('Kích thước', ['ATX', 'Micro-ATX', 'Mini-ITX', 'E-ATX']),
    ('Kích thước hỗ trợ', ['ATX', 'Micro-ATX', 'Mini-ITX', 'E-ATX']),
]

COMPATIBILITY_RULES = [
    {
        'name': 'Socket CPU và Mainboard',
        'source_category': 'Mainboard', 'source_attribute': 'Socket',
        'target_category': 'CPU', 'target_attribute': 'Socket',
        'operator': 'equal', 'active': True,
    },
    {
        'name': 'Khe RAM và Mainboard',
        'source_category': 'Mainboard', 'source_attribute': 'Khe RAM',
        'target_category': 'RAM', 'target_attribute': 'Thế hệ RAM',
        'operator': 'overlap', 'active': True,
    },
    {
        'name': 'Thế hệ RAM và CPU',
        'source_category': 'CPU', 'source_attribute': 'Thế hệ RAM hỗ trợ',
        'target_category': 'RAM', 'target_attribute': 'Thế hệ RAM',
        'operator': 'overlap', 'active': True,
    },
    {
        'name': 'Kích thước Mainboard và Vỏ case',
        'source_category': 'Mainboard', 'source_attribute': 'Kích thước',
        'target_category': 'Case', 'target_attribute': 'Kích thước hỗ trợ',
        'operator': 'overlap', 'active': True,
    },
]


def seed(apps, schema_editor):
    ProductAttribute = apps.get_model('core', 'ProductAttribute')
    for name, values in ATTRIBUTE_DEFINITIONS:
        ProductAttribute.objects.get_or_create(name=name, defaults={'values': values})

    CompatibilityRule = apps.get_model('core', 'CompatibilityRule')
    for rule in COMPATIBILITY_RULES:
        CompatibilityRule.objects.get_or_create(
            source_category=rule['source_category'], source_attribute=rule['source_attribute'],
            target_category=rule['target_category'], target_attribute=rule['target_attribute'],
            defaults={'name': rule['name'], 'operator': rule['operator'], 'active': rule['active']},
        )


def unseed(apps, schema_editor):
    ProductAttribute = apps.get_model('core', 'ProductAttribute')
    ProductAttribute.objects.filter(name__in=[name for name, _ in ATTRIBUTE_DEFINITIONS]).delete()

    CompatibilityRule = apps.get_model('core', 'CompatibilityRule')
    for rule in COMPATIBILITY_RULES:
        CompatibilityRule.objects.filter(
            source_category=rule['source_category'], source_attribute=rule['source_attribute'],
            target_category=rule['target_category'], target_attribute=rule['target_attribute'],
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_flashsale'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]

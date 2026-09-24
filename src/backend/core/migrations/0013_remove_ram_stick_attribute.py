from django.db import migrations


def remove_redundant_attribute(apps, schema_editor):
    apps.get_model('core', 'ProductAttribute').objects.filter(name='Số thanh RAM').delete()
    Product = apps.get_model('core', 'Product')
    for product in Product.objects.all():
        attributes = product.payload.get('attributes', [])
        remaining = [item for item in attributes if item.get('name') != 'Số thanh RAM']
        if len(remaining) != len(attributes):
            product.payload['attributes'] = remaining
            product.save(update_fields=['payload'])


class Migration(migrations.Migration):
    dependencies = [('core', '0012_ram_slot_attributes')]
    operations = [migrations.RunPython(remove_redundant_attribute, migrations.RunPython.noop)]

from django.db import migrations
from django.db.models import Q


def remove_attribute(apps, schema_editor):
    apps.get_model('core', 'ProductAttribute').objects.filter(name__iexact='Khe RAM').delete()
    # Remove rules that would otherwise refer to an attribute that no longer exists.
    apps.get_model('core', 'CompatibilityRule').objects.filter(
        Q(source_attribute__iexact='Khe RAM') | Q(target_attribute__iexact='Khe RAM')
    ).delete()
    for product in apps.get_model('core', 'Product').objects.all():
        attributes = product.payload.get('attributes', [])
        remaining = [item for item in attributes if str(item.get('name', '')).strip().casefold() != 'khe ram']
        if len(remaining) != len(attributes):
            product.payload['attributes'] = remaining
            product.save(update_fields=['payload'])


class Migration(migrations.Migration):
    dependencies = [('core', '0013_remove_ram_stick_attribute')]
    operations = [migrations.RunPython(remove_attribute, migrations.RunPython.noop)]

from django.db import migrations


def seed(apps, schema_editor):
    attribute = apps.get_model('core', 'ProductAttribute')
    for name in ['Số khe RAM', 'Số thanh RAM']:
        attribute.objects.get_or_create(name=name, defaults={'values': []})


class Migration(migrations.Migration):
    dependencies = [('core', '0011_productimage')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]

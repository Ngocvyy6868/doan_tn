from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0016_warehouse')]

    operations = [
        migrations.AddField(model_name='orderitem', name='allocations', field=models.JSONField(blank=True, default=list)),
    ]

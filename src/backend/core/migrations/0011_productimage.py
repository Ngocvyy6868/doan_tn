from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0010_seed_compatibility_rules')]
    operations = [migrations.CreateModel(
        name='ProductImage',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('content', models.BinaryField()),
            ('content_type', models.CharField(max_length=32)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ],
    )]

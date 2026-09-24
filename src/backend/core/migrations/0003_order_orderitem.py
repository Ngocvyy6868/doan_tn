from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('core', '0002_catalog_models'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('status', models.CharField(choices=[('PENDING_PAYMENT', 'Chờ thanh toán'), ('CONFIRMED', 'Đã xác nhận'), ('PACKING', 'Đang đóng gói'), ('DELIVERING', 'Đang giao'), ('DELIVERED', 'Đã giao'), ('CANCELLED', 'Đã hủy')], default='CONFIRMED', max_length=24)),
                ('payment_status', models.CharField(default='UNPAID', max_length=20)),
                ('payment_method', models.CharField(max_length=30)),
                ('shipping_method', models.CharField(max_length=30)),
                ('recipient_name', models.CharField(max_length=150)), ('recipient_phone', models.CharField(max_length=15)),
                ('province', models.CharField(max_length=100)), ('address', models.TextField()),
                ('subtotal', models.BigIntegerField(default=0)), ('shipping_fee', models.BigIntegerField(default=0)), ('grand_total', models.BigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='core.customer')),
                ('handler', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='handled_orders', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_external_id', models.CharField(max_length=64)), ('sku', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=255)), ('image', models.URLField(blank=True)),
                ('unit_price', models.BigIntegerField()), ('quantity', models.PositiveIntegerField()), ('total', models.BigIntegerField()),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='core.order')),
            ],
        ),
    ]

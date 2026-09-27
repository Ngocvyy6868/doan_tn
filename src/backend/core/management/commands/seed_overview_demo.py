from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import Order, OrderItem, Product


class Command(BaseCommand):
    help = 'Add repeatable demo orders for the current month without changing existing orders or stock.'

    @transaction.atomic
    def handle(self, *args, **options):
        products = [p for p in Product.objects.order_by('external_id')
                    if p.payload.get('active', True) and isinstance(p.payload.get('price'), (int, float))
                    and p.payload['price'] > 0]
        if not products:
            raise CommandError('Add products with prices before seeding overview orders.')
        categories = {}
        for product in products:
            categories.setdefault(product.payload.get('cat', 'Other'), []).append(product)
        catalog = []
        while any(categories.values()):
            for group in categories.values():
                if group:
                    catalog.append(group.pop(0))
        today = timezone.localdate()
        created = 0
        for index in range(24):
            code = f'DEMO-{today:%Y%m}-{index+1:03d}'
            if Order.objects.filter(code=code).exists():
                continue
            lines = []
            for offset in range(1 + index % 3):
                product = catalog[(index * 3 + offset) % len(catalog)]
                payload = product.payload
                quantity = 1 + (index + offset) % 2
                price = int(payload['price'])
                lines.append(dict(product_external_id=product.external_id,
                                  sku=payload.get('sku', '') or f'DEMO-{product.external_id}',
                                  name=payload.get('name', product.external_id), image=payload.get('img', ''),
                                  unit_price=price, quantity=quantity, total=price * quantity))
            subtotal = sum(line['total'] for line in lines)
            order = Order.objects.create(
                code=code, status=Order.Status.DELIVERED, payment_status='PAID',
                payment_method='COD', shipping_method='standard',
                recipient_name=f'Khách hàng mẫu {index+1:02d}', recipient_phone='0900000000',
                province='TP. Hồ Chí Minh', address='Địa chỉ minh họa — dữ liệu mẫu báo cáo',
                subtotal=subtotal, shipping_fee=30000, grand_total=subtotal+30000,
            )
            OrderItem.objects.bulk_create([OrderItem(order=order, **line) for line in lines])
            placed_on = today.replace(day=1 + index * today.day // 24)
            timestamp = timezone.make_aware(datetime.combine(placed_on, time.min))
            Order.objects.filter(pk=order.pk).update(created_at=timestamp, updated_at=timestamp)
            created += 1
        self.stdout.write(self.style.SUCCESS(f'Created {created} demo orders for {today:%Y-%m}.'))

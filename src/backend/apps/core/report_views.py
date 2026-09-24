from datetime import date, timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from .models import Order, Product


@require_GET
def overview(request):
    today = timezone.localdate()
    try:
        start = date.fromisoformat(request.GET.get('start', str(today.replace(day=1))))
        end = date.fromisoformat(request.GET.get('end', str(today)))
        if start > end or (end - start).days > 1095:
            raise ValueError()
    except ValueError:
        return JsonResponse({'message': 'Chọn khoảng thời gian hợp lệ, tối đa 3 năm.'}, status=400)
    category, brand = request.GET.get('category', ''), request.GET.get('brand', '')
    catalog = {p.external_id: p.payload for p in Product.objects.all()}
    def matches(p):
        return (not category or p.get('cat') == category) and (not brand or p.get('brand') == brand)
    rows = {}
    for product_id, p in catalog.items():
        if matches(p):
            rows[product_id] = {'id': product_id, 'sku': p.get('sku', ''), 'name': p.get('name', ''),
                                'category': p.get('cat', 'Chưa phân nhóm'), 'quantity': 0, 'revenue': 0,
                                'profit': None, 'margin': None, 'stock': p.get('stock')}
    monthly = request.GET.get('group') == 'month'
    buckets = {}
    current = start
    while current <= end:
        buckets[current.strftime('%Y-%m' if monthly else '%Y-%m-%d')] = 0
        current += timedelta(days=1)
    groups, order_count, quantity, revenue = {}, 0, 0, 0
    orders = Order.objects.filter(status=Order.Status.DELIVERED, created_at__date__gte=start,
                                  created_at__date__lte=end).prefetch_related('items')
    for order in orders:
        matched = False
        period = timezone.localtime(order.created_at).strftime('%Y-%m' if monthly else '%Y-%m-%d')
        for item in order.items.all():
            product = catalog.get(item.product_external_id, {})
            if not matches(product):
                continue
            matched = True
            row = rows.setdefault(item.product_external_id, {'id': item.product_external_id, 'sku': item.sku,
                                  'name': item.name, 'category': 'Chưa phân nhóm', 'quantity': 0,
                                  'revenue': 0, 'profit': None, 'margin': None, 'stock': None})
            row['quantity'] += item.quantity
            row['revenue'] += item.total
            revenue += item.total
            quantity += item.quantity
            buckets[period] = buckets.get(period, 0) + item.total
            groups[row['category']] = groups.get(row['category'], 0) + item.total
        order_count += int(matched)
    products = sorted(rows.values(), key=lambda row: row['revenue'], reverse=True)
    return JsonResponse({'summary': {'revenue': revenue, 'profit': None, 'margin': None, 'orders': order_count, 'quantity': quantity},
                         'series': [{'label': key, 'value': value} for key, value in buckets.items()],
                         'groups': [{'label': key, 'value': value} for key, value in groups.items()],
                         'channels': [{'label': 'Web', 'value': revenue}], 'products': products,
                         'low_stock': [row for row in products if isinstance(row['stock'], (int, float)) and row['stock'] <= 5],
                         'categories': sorted({p.get('cat') for p in catalog.values() if p.get('cat')}),
                         'brands': sorted({p.get('brand') for p in catalog.values() if p.get('brand')})})

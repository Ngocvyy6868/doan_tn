from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import FlashSale, Product
from .views import _payload


def serialize(sale, products):
    product = products.get(sale.product_external_id)
    return {'id': sale.pk, 'product_id': sale.product_external_id, 'product': product,
            'quantity': sale.quantity, 'sold': sale.sold, 'remaining': sale.quantity-sale.sold,
            'starts_at': sale.starts_at.isoformat(), 'ends_at': sale.ends_at.isoformat(), 'active': sale.active}


@csrf_exempt
@transaction.atomic
def flash_sales(request, sale_id=None, public=False):
    products = {p.external_id: {k:v for k,v in p.payload.items() if k != 'cost'} for p in Product.objects.all()}
    if request.method == 'GET':
        sales = FlashSale.objects.order_by('starts_at')
        if public:
            sales = sales.filter(active=True, ends_at__gt=timezone.now())
        return JsonResponse({'results': [serialize(s, products) for s in sales
                             if not public or (s.quantity > s.sold and products.get(s.product_external_id, {}).get('active', True) and s.product_external_id in products)]})
    if public or request.method not in ('POST', 'PATCH'):
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Dữ liệu không hợp lệ.'}, status=400)
    sale = FlashSale.objects.select_for_update().filter(pk=sale_id).first() if sale_id else None
    if sale_id and not sale:
        return JsonResponse({'message': 'Không tìm thấy Flash sale.'}, status=404)
    try:
        product_id = str(data.get('product_id', sale.product_external_id if sale else ''))
        product = Product.objects.select_for_update().filter(external_id=product_id).first()
        quantity = data.get('quantity', sale.quantity if sale else None)
        start = parse_datetime(data['starts_at']) if 'starts_at' in data else sale.starts_at if sale else None
        end = parse_datetime(data['ends_at']) if 'ends_at' in data else sale.ends_at if sale else None
        active = data.get('active', sale.active if sale else True)
        if not product or not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0 or not isinstance(active, bool):
            raise ValueError()
        if not start or not end or timezone.is_naive(start) or timezone.is_naive(end) or start >= end:
            raise ValueError()
        if sale and (quantity < sale.sold or (sale.sold and product_id != sale.product_external_id)):
            raise ValueError()
        if active and FlashSale.objects.filter(product_external_id=product_id, active=True, starts_at__lt=end, ends_at__gt=start).exclude(pk=sale_id).exists():
            return JsonResponse({'message': 'Sản phẩm đã có Flash sale trong khoảng thời gian này.'}, status=400)
    except (ValueError, TypeError, KeyError):
        return JsonResponse({'message': 'Chọn sản phẩm, số lượng nguyên dương và thời gian kết thúc sau bắt đầu. Số lượng không được nhỏ hơn số đã bán.'}, status=400)
    if not sale:
        sale = FlashSale()
    sale.product_external_id, sale.quantity, sale.starts_at, sale.ends_at, sale.active = product_id, quantity, start, end, active
    sale.save()
    return JsonResponse({'sale': serialize(sale, products)}, status=200 if sale_id else 201)

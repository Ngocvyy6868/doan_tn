"""Quản lý kho: danh sách kho, tồn kho theo từng kho và tình trạng còn hàng tại cửa hàng."""
import random
import re

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Product, Warehouse, WarehouseStock
from .views import _payload

CODE_RE = re.compile(r'^[A-Z0-9][A-Z0-9_-]{1,19}$')
MAX_QUANTITY = 1_000_000


def _staff_only(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'message': 'Cần đăng nhập tài khoản quản trị.'}, status=403)
    return None


def sync_product_stock(product_ids=None):
    """Ghi tồn kho tổng vào payload để giỏ hàng, tư vấn AI và báo cáo dùng chung một con số.

    Chỉ áp dụng cho sản phẩm đã có dòng tồn kho theo kho; sản phẩm chưa phân kho giữ tồn kho nhập tay.
    """
    managed = WarehouseStock.objects.all()
    if product_ids is not None:
        managed = managed.filter(product_id__in=product_ids)
    ids = set(managed.values_list('product_id', flat=True))
    totals = dict(WarehouseStock.objects.filter(product_id__in=ids, warehouse__active=True)
                  .values_list('product_id').annotate(total=Sum('quantity')))
    for product in Product.objects.select_for_update().filter(pk__in=ids).defer('embedding'):
        total = int(totals.get(product.pk) or 0)
        if product.payload.get('stock') != total or not product.payload.get('warehouse_managed'):
            product.payload = {**product.payload, 'stock': total, 'warehouse_managed': True}
            product.save(update_fields=['payload', 'updated_at'])


def _warehouse_data(warehouse, totals=None):
    total = (totals or {}).get(warehouse.pk, 0)
    return {'id': warehouse.pk, 'code': warehouse.code, 'address': warehouse.address,
            'active': warehouse.active, 'total_quantity': int(total or 0),
            'created_at': warehouse.created_at.isoformat()}


def _clean_warehouse(data, current=None):
    code = str(data.get('code', current.code if current else '')).strip().upper()
    address = str(data.get('address', current.address if current else '')).strip()
    active = data.get('active', current.active if current else True)
    if not CODE_RE.match(code):
        raise ValueError('Mã kho gồm 2–20 ký tự: chữ in hoa, số, "-" hoặc "_".')
    if not 5 <= len(address) <= 255:
        raise ValueError('Địa chỉ kho cần từ 5 đến 255 ký tự.')
    if not isinstance(active, bool):
        raise ValueError('Trạng thái kho không hợp lệ.')
    return code, address, active


@csrf_exempt
def warehouses(request, warehouse_id=None):
    denied = _staff_only(request)
    if denied:
        return denied
    if request.method == 'GET' and warehouse_id is None:
        totals = dict(WarehouseStock.objects.values_list('warehouse_id').annotate(total=Sum('quantity')))
        return JsonResponse({'results': [_warehouse_data(w, totals) for w in Warehouse.objects.all()]})
    if request.method not in ('POST', 'PATCH', 'DELETE') or (request.method == 'POST') != (warehouse_id is None):
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    with transaction.atomic():
        warehouse = None
        if warehouse_id is not None:
            warehouse = Warehouse.objects.select_for_update().filter(pk=warehouse_id).first()
            if not warehouse:
                return JsonResponse({'message': 'Không tìm thấy kho.'}, status=404)
        if request.method == 'DELETE':
            product_ids = list(warehouse.stocks.values_list('product_id', flat=True))
            if warehouse.stocks.filter(quantity__gt=0).exists():
                return JsonResponse({'message': 'Kho còn hàng. Hãy chuyển tồn kho về 0 hoặc ngừng hoạt động kho thay vì xóa.'}, status=400)
            warehouse.delete()
            sync_product_stock(product_ids)
            # Sản phẩm không còn dòng tồn kho nào thì trở lại tồn kho nhập tay với giá trị 0.
            for product in Product.objects.select_for_update().filter(pk__in=product_ids, warehouse_stocks__isnull=True):
                product.payload = {k: v for k, v in product.payload.items() if k != 'warehouse_managed'}
                product.save(update_fields=['payload', 'updated_at'])
            return JsonResponse({'deleted': True})
        data = _payload(request)
        if not isinstance(data, dict):
            return JsonResponse({'message': 'Dữ liệu kho không hợp lệ.'}, status=400)
        try:
            code, address, active = _clean_warehouse(data, warehouse)
        except ValueError as error:
            return JsonResponse({'message': str(error)}, status=400)
        active_changed = warehouse is not None and warehouse.active != active
        warehouse = warehouse or Warehouse()
        warehouse.code, warehouse.address, warehouse.active = code, address, active
        try:
            with transaction.atomic():
                warehouse.save()
        except IntegrityError:
            return JsonResponse({'message': f'Mã kho {code} đã tồn tại.'}, status=400)
        if active_changed:
            sync_product_stock(list(warehouse.stocks.values_list('product_id', flat=True)))
        total = warehouse.stocks.aggregate(total=Sum('quantity'))['total'] or 0
    return JsonResponse({'warehouse': _warehouse_data(warehouse, {warehouse.pk: total})}, status=201 if warehouse_id is None else 200)


def _stock_rows(product_ids=None):
    rows = WarehouseStock.objects.select_related('product')
    if product_ids is not None:
        rows = rows.filter(product_id__in=product_ids)
    result = {}
    for row in rows:
        result.setdefault(row.product.external_id, {})[str(row.warehouse_id)] = row.quantity
    return result


@csrf_exempt
def inventory(request):
    """GET: tồn kho theo kho của mọi sản phẩm. POST: nhập thêm (add) hoặc đặt lại (set) số lượng một kho."""
    denied = _staff_only(request)
    if denied:
        return denied
    if request.method == 'GET':
        return JsonResponse({'results': _stock_rows()})
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Dữ liệu không hợp lệ.'}, status=400)
    quantity, mode = data.get('quantity'), data.get('mode', 'add')
    if mode not in ('add', 'set') or isinstance(quantity, bool) or not isinstance(quantity, int):
        return JsonResponse({'message': 'Số lượng phải là số nguyên.'}, status=400)
    if (mode == 'set' and quantity < 0) or (mode == 'add' and quantity == 0) or abs(quantity) > MAX_QUANTITY:
        return JsonResponse({'message': 'Số lượng không hợp lệ.'}, status=400)
    with transaction.atomic():
        product = Product.objects.select_for_update().defer('embedding').filter(external_id=str(data.get('product_id', ''))).first()
        warehouse = Warehouse.objects.filter(pk=data.get('warehouse_id') if isinstance(data.get('warehouse_id'), int) else None).first()
        if not product or not warehouse:
            return JsonResponse({'message': 'Không tìm thấy sản phẩm hoặc kho.'}, status=404)
        row, _ = WarehouseStock.objects.select_for_update().get_or_create(warehouse=warehouse, product=product)
        new_quantity = quantity if mode == 'set' else row.quantity + quantity
        if new_quantity < 0:
            return JsonResponse({'message': f'Kho {warehouse.code} chỉ còn {row.quantity} sản phẩm, không thể xuất {-quantity}.'}, status=400)
        if new_quantity > MAX_QUANTITY:
            return JsonResponse({'message': 'Số lượng vượt giới hạn cho phép.'}, status=400)
        row.quantity = new_quantity
        row.save()
        sync_product_stock([product.pk])
        product.refresh_from_db(fields=['payload'])
    return JsonResponse({'product_id': product.external_id, 'stocks': _stock_rows([product.pk]).get(product.external_id, {}),
                         'stock': product.payload.get('stock')})


def product_availability(request, product_id):
    """Công khai: các cửa hàng đang hoạt động còn hàng của một sản phẩm."""
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    product = Product.objects.defer('embedding').filter(external_id=product_id).first()
    if not product or product.payload.get('active') is False:
        return JsonResponse({'message': 'Không tìm thấy sản phẩm.'}, status=404)
    rows = (WarehouseStock.objects.select_related('warehouse')
            .filter(product=product, warehouse__active=True, quantity__gt=0).order_by('warehouse__code'))
    return JsonResponse({'managed': product.warehouse_stocks.exists(),
                         'stores': [{'code': r.warehouse.code, 'address': r.warehouse.address, 'quantity': r.quantity} for r in rows]})


class OutOfStock(Exception):
    def __init__(self, product_id, name, remaining):
        super().__init__(f'{name}: chỉ còn {remaining} sản phẩm trong kho. Vui lòng giảm số lượng.')
        self.product_id, self.remaining = product_id, remaining


def allocate_stock(product_id, quantity, name=''):
    """Trừ tồn kho khi đặt hàng; chưa có luồng fulfilment nên chọn kho ngẫu nhiên. Gọi trong transaction.

    Trả về danh sách phân bổ để hoàn kho khi hủy đơn. Sản phẩm không có trong catalog hoặc không theo dõi tồn thì bỏ qua.
    """
    product = Product.objects.select_for_update().defer('embedding').filter(external_id=product_id).first()
    if not product:
        return []
    label = name or product.payload.get('name') or product_id
    if product.warehouse_stocks.exists():
        rows = list(WarehouseStock.objects.select_for_update()
                    .filter(product=product, warehouse__active=True, quantity__gt=0))
        available = sum(r.quantity for r in rows)
        if available < quantity:
            raise OutOfStock(product_id, label, available)
        random.shuffle(rows)
        allocations, needed = [], quantity
        for row in rows:
            if not needed:
                break
            take = min(row.quantity, needed)
            row.quantity -= take
            row.save(update_fields=['quantity', 'updated_at'])
            allocations.append({'warehouse_id': row.warehouse_id, 'quantity': take})
            needed -= take
        sync_product_stock([product.pk])
        return allocations
    stock = product.payload.get('stock')
    if isinstance(stock, bool) or not isinstance(stock, (int, float)):
        return []
    if stock < quantity:
        raise OutOfStock(product_id, label, max(0, int(stock)))
    product.payload = {**product.payload, 'stock': int(stock) - quantity}
    product.save(update_fields=['payload', 'updated_at'])
    return [{'warehouse_id': None, 'quantity': quantity}]


def release_stock(product_id, allocations):
    """Hoàn lại đúng các kho đã trừ (dùng khi hủy đơn). Gọi trong transaction."""
    product = Product.objects.select_for_update().defer('embedding').filter(external_id=product_id).first()
    if not product or not allocations:
        return
    for allocation in allocations:
        amount = int(allocation.get('quantity') or 0)
        if amount <= 0:
            continue
        warehouse_id = allocation.get('warehouse_id')
        if warehouse_id is None:
            stock = product.payload.get('stock')
            if isinstance(stock, (int, float)) and not isinstance(stock, bool):
                product.payload = {**product.payload, 'stock': int(stock) + amount}
                product.save(update_fields=['payload', 'updated_at'])
            continue
        warehouse = Warehouse.objects.filter(pk=warehouse_id).first()
        if not warehouse:
            continue  # Kho đã bị xóa: không còn chỗ để hoàn.
        row, _ = WarehouseStock.objects.select_for_update().get_or_create(warehouse=warehouse, product=product)
        row.quantity += amount
        row.save(update_fields=['quantity', 'updated_at'])
    sync_product_stock([product.pk])

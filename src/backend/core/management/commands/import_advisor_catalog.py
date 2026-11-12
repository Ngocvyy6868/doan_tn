"""Nhập catalog linh kiện từ JSON hoặc CSV (mẫu: data/import-template.csv).

- Kiểm tra toàn bộ file trước, báo tất cả lỗi một lượt; có lỗi thì không ghi gì.
- Chuẩn hóa giá trị để luật tương thích so khớp được (socket, chuẩn RAM, kích thước mainboard...).
- Upsert theo id/sku, không xóa sản phẩm khác. Trường admin đã sửa mà file không có (giá gốc, giá vốn,
  ảnh tải lên...) được giữ nguyên; tồn kho của sản phẩm đã phân kho vẫn do module Kho quyết định.
"""
import csv
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.advisor.catalog import category, fold
from core.models import Category, Product

SPEC_KEYS = {
    'cpu': ('socket', 'cores', 'threads', 'boost_ghz', 'tdp_w', 'has_igpu', 'stock_cooler'),
    'mainboard': ('socket', 'chipset', 'form_factor', 'ram_type', 'ram_slots', 'max_ram_gb', 'm2_slots'),
    'ram': ('ram_type', 'capacity_gb', 'modules', 'speed_mhz'),
    'gpu': ('chip', 'vram_gb', 'tdp_w', 'length_mm'),
    'cooler': ('cooler_type', 'sockets', 'height_mm', 'tdp_w'),
    'ssd': ('interface', 'capacity_gb', 'pcie_gen'),
    'psu': ('watt', 'efficiency', 'modular'),
    'case': ('supported_mb', 'max_gpu_length_mm', 'max_cooler_height_mm'),
    'license': (),
    **{cat: () for cat in ('hdd', 'fan', 'monitor', 'keyboard', 'mouse', 'headphones',
                           'optical_drive', 'network_adapter', 'fan_controller', 'expansion_card')},
}
LABELS = {'cpu': 'CPU', 'mainboard': 'Mainboard', 'ram': 'RAM', 'gpu': 'VGA',
          'cooler': 'Tản nhiệt', 'ssd': 'SSD', 'psu': 'Nguồn', 'case': 'Case', 'license': 'Bản quyền'}
LABELS.update({cat: 'Thiết bị ngoại vi' for cat in (
    'expansion_card', 'keyboard', 'headphones', 'monitor', 'network_adapter', 'optical_drive', 'mouse')})
LABELS.update({cat: 'Tản nhiệt' for cat in ('fan', 'fan_controller')})

NUMERIC = {'cores', 'threads', 'base_ghz', 'boost_ghz', 'tdp_w', 'ram_slots', 'max_ram_gb', 'm2_slots',
           'capacity_gb', 'modules', 'speed_mhz', 'cas_latency', 'vram_gb', 'length_mm', 'height_mm',
           'radiator_mm', 'pcie_gen', 'watt', 'max_gpu_length_mm', 'max_cooler_height_mm', 'airflow_cfm',
           'diameter_mm', 'pack_quantity', 'rpm', 'refresh_hz', 'diagonal_inches'}
BOOLEAN = {'has_igpu', 'stock_cooler', 'modular'}
LISTS = {'sockets', 'supported_mb', 'connectivity'}
ALL_SPEC_KEYS = {k for keys in SPEC_KEYS.values() for k in keys} | NUMERIC | BOOLEAN | LISTS | {'resolution'}
TRUE, FALSE = {'true', '1', 'co', 'yes', 'x'}, {'false', '0', 'khong', 'no'}
RAM_TYPES = {'DDR3', 'DDR4', 'DDR5'}
# Tên chuẩn của kích thước mainboard; khóa là dạng đã bỏ dấu, khoảng trắng và gạch nối.
FORM_FACTORS = {'atx': 'ATX', 'microatx': 'Micro ATX', 'matx': 'Micro ATX', 'uatx': 'Micro ATX',
                'miniitx': 'Mini ITX', 'itx': 'Mini ITX', 'eatx': 'E-ATX', 'extendedatx': 'E-ATX'}
COOLER_TYPES = {'air': 'air', 'khi': 'air', 'tankhi': 'air', 'liquid': 'liquid', 'aio': 'liquid',
                'nuoc': 'liquid', 'tannuoc': 'liquid'}
PRODUCT_FIELDS = ('name', 'brand', 'description', 'img', 'old', 'active', 'productInfo', 'badge')
DEFAULT_CPU_TDP_W = 65  # CPU thiếu TDP: dùng mức phổ biến để Build PC vẫn tính được công suất nguồn.
DEFAULT_STOCK_PER_WAREHOUSE = 10  # Sản phẩm mới: 10 cái ở mỗi kho đang hoạt động.
POWER_ATTRIBUTE = 'Công suất'  # Thuộc tính công suất cấp của bộ nguồn (W).
# Thuộc tính mà luật tương thích RAM dùng: CPU/Mainboard ghi các thế hệ hỗ trợ, RAM ghi thế hệ của nó.
RAM_ATTRIBUTE = {'cpu': 'Thế hệ RAM hỗ trợ', 'mainboard': 'Thế hệ RAM hỗ trợ', 'ram': 'Thế hệ RAM'}


class Invalid(ValueError):
    pass


def compact(value):
    return re.sub(r'[\s\-_]+', '', fold(value))


def to_number(key, value):
    if isinstance(value, bool):
        raise Invalid(f'specs.{key} phải là số')
    if isinstance(value, (int, float)):
        number = value
    else:
        text = str(value).strip().replace(',', '.')
        text = re.sub(r'(?i)\s*(ghz|mhz|gb|tb|mm|w|cfm|rpm|hz|inch|")$', '', text)
        try:
            number = float(text)
        except ValueError as exc:
            raise Invalid(f'specs.{key}="{value}" không phải số') from exc
    if number < 0:
        raise Invalid(f'specs.{key} không được âm')
    return int(number) if float(number).is_integer() else number


def to_bool(key, value):
    if isinstance(value, bool):
        return value
    text = fold(str(value))
    if text in TRUE:
        return True
    if text in FALSE:
        return False
    raise Invalid(f'specs.{key}="{value}" phải là có/không')


def to_list(key, value):
    items = value if isinstance(value, list) else re.split(r'[;,|]', str(value))
    if any(not isinstance(v, str) for v in items):
        raise Invalid(f'specs.{key} phải là danh sách chuỗi')
    return [v.strip() for v in items if v.strip()]


def socket(value):
    # "LGA 1700" -> "LGA1700", "am5" -> "AM5": luật so socket theo chuỗi.
    return re.sub(r'\s+', '', str(value)).upper()


def form_factor(key, value):
    result = FORM_FACTORS.get(compact(value))
    if result is None:
        raise Invalid(f'specs.{key}="{value}" phải là một trong {sorted(set(FORM_FACTORS.values()))}')
    return result


def normalize_specs(cat, specs):
    out = {}
    for key, value in specs.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            out[key] = None
            continue
        if key in NUMERIC:
            value = to_number(key, value)
        elif key in BOOLEAN:
            value = to_bool(key, value)
        elif key in LISTS:
            value = to_list(key, value)
        elif isinstance(value, str):
            value = value.strip()
        if key == 'socket':
            value = socket(value)
        elif key == 'sockets':
            value = [socket(v) for v in value]
        elif key == 'ram_type':
            parts = [p.strip().upper() for p in re.split(r'[,;/]', value) if p.strip()]
            if not parts or any(p not in RAM_TYPES for p in parts):
                raise Invalid(f'specs.ram_type="{value}" phải là DDR3/DDR4/DDR5 (mainboard hỗ trợ nhiều loại thì ghi "DDR4/DDR5")')
            value = '/'.join(parts)
        elif key == 'interface' and cat in ('ssd', 'hdd'):
            value = fold(value)
            if value not in ('nvme', 'sata'):
                raise Invalid(f'specs.interface="{value}" phải là nvme hoặc sata')
        elif key == 'cooler_type':
            if compact(value) not in COOLER_TYPES:
                raise Invalid(f'specs.cooler_type="{value}" phải là air (tản khí) hoặc liquid (tản nước)')
            value = COOLER_TYPES[compact(value)]
        elif key == 'form_factor' and cat == 'mainboard':
            value = form_factor(key, value)
        elif key == 'supported_mb':
            value = [form_factor(key, v) for v in value]
        out[key] = value
    return out


def to_int(field, value):
    if isinstance(value, bool):
        raise Invalid(f'{field} phải là số nguyên không âm')
    if isinstance(value, str):
        digits = re.sub(r'[^\d]', '', value)  # "25.990.000₫" -> 25990000
        if not digits:
            raise Invalid(f'{field} phải là số nguyên không âm')
        value = int(digits)
    if type(value) is not int or value < 0:
        raise Invalid(f'{field} phải là số nguyên không âm')
    return value


def read_items(path):
    if path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        items = []
        for row in rows:
            row = {(k or '').strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            item = {k: v for k, v in row.items() if k not in ALL_SPEC_KEYS and v not in (None, '')}
            # Cột thông số có mặt trong file thì luôn có khóa (ô trống = chưa có dữ liệu).
            item['specs'] = {k: (v or None) for k, v in row.items() if k in ALL_SPEC_KEYS}
            items.append(item)
        return items
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, list):
        raise CommandError('Dữ liệu JSON phải là danh sách sản phẩm.')
    return data


def prepare(item, seen):
    if not isinstance(item, dict):
        raise Invalid('mỗi sản phẩm phải là object')
    key = item.get('id') or item.get('sku')
    if not isinstance(key, str) or not 1 <= len(key.strip()) <= 64:
        raise Invalid('thiếu id/sku hoặc dài hơn 64 ký tự')
    key = key.strip()
    if key in seen:
        raise Invalid('id/sku bị trùng trong file')
    cat = category(item.get('product_type') or item.get('cat') or item.get('category') or '')
    if cat not in SPEC_KEYS:
        raise Invalid(f'danh mục "{cat}" không hỗ trợ; dùng một trong {sorted(SPEC_KEYS)}')
    if not isinstance(item.get('name'), str) or not item['name'].strip():
        raise Invalid('thiếu tên sản phẩm')
    specs = item.get('specs')
    if not isinstance(specs, dict):
        raise Invalid('thiếu specs')
    missing = [k for k in SPEC_KEYS[cat] if k not in specs]
    if missing:
        raise Invalid(f'thiếu thông số {missing} (để trống/null nếu chưa có dữ liệu)')
    payload = {k: item[k] for k in PRODUCT_FIELDS if k in item}
    payload['name'] = item['name'].strip()
    payload.update(price=to_int('price', item.get('price')), stock=to_int('stock', item.get('stock')))
    if 'old' in payload:
        payload['old'] = to_int('old', payload['old'])
    if 'active' in payload:
        payload['active'] = to_bool('active', payload['active'])
    if item.get('sku'):
        payload['sku'] = str(item['sku']).strip()
    specs = normalize_specs(cat, specs)
    # CSV có đủ cột của mọi nhóm: bỏ cột trống không thuộc nhóm này để specs gọn.
    specs = {k: v for k, v in specs.items() if v is not None or k in SPEC_KEYS[cat]}
    if cat == 'cpu' and specs.get('tdp_w') is None:
        specs['tdp_w'] = DEFAULT_CPU_TDP_W
    if cat == 'psu':
        if specs.get('watt') is not None:  # nguồn: công suất cấp, không phải điện tiêu thụ
            payload['attributes'] = [{'name': POWER_ATTRIBUTE, 'value': str(specs['watt']), 'unit': 'W'}]
    elif specs.get('tdp_w') is not None and cat != 'cooler':  # tdp_w của tản nhiệt là khả năng tản, không phải điện tiêu thụ
        payload['attributes'] = [{'name': 'TDP', 'value': str(specs['tdp_w']), 'unit': 'W'}]
    if cat in RAM_ATTRIBUTE and specs.get('ram_type'):  # luật Build PC so thế hệ RAM qua thuộc tính
        payload.setdefault('attributes', []).append(
            {'name': RAM_ATTRIBUTE[cat], 'value': ', '.join(specs['ram_type'].split('/'))})
    payload.update(id=key, product_type=cat, cat=LABELS.get(cat, cat), specs=specs)
    return key, cat, payload


class Command(BaseCommand):
    help = 'Validate and upsert normalized product JSON/CSV; never delete the existing catalog.'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Đường dẫn .json hoặc .csv')
        parser.add_argument('--dry-run', action='store_true', help='Chỉ kiểm tra, không ghi database.')

    def handle(self, *args, **options):
        path = Path(options['file'])
        try:
            items = read_items(path)
        except (OSError, ValueError, csv.Error) as exc:
            raise CommandError(f'Không đọc được file sản phẩm: {exc}') from exc
        prepared, seen, errors = [], set(), []
        for index, item in enumerate(items, start=1):
            label = (item.get('id') or item.get('sku') or f'dòng {index}') if isinstance(item, dict) else f'dòng {index}'
            try:
                key, cat, payload = prepare(item, seen)
            except Invalid as exc:
                errors.append(f'{label}: {exc}')
                continue
            seen.add(key)
            prepared.append((key, cat, payload))
        if errors:
            shown = '\n'.join(f'  - {e}' for e in errors[:100])
            more = f'\n  ... và {len(errors) - 100} lỗi khác' if len(errors) > 100 else ''
            raise CommandError(f'{len(errors)}/{len(items)} sản phẩm không hợp lệ, chưa ghi gì:\n{shown}{more}')
        if options['dry_run']:
            self.stdout.write(f'Validated {len(prepared)} products; no changes.')
            return
        from core.inventory_views import sync_product_stock
        from core.models import Warehouse, WarehouseStock
        created, new_products = 0, []
        with transaction.atomic():
            existing = {p.external_id: p for p in Product.objects.select_for_update().defer('embedding')
                        .filter(external_id__in=[key for key, _, _ in prepared])}
            for key, cat, payload in prepared:
                group, _ = Category.objects.get_or_create(name=LABELS.get(cat, cat))
                product = existing.get(key)
                if product is None:  # sản phẩm mới hiển thị trên cửa hàng, trừ khi file ghi active
                    new_products.append(Product.objects.create(
                        external_id=key, category=group, payload={'active': True, **payload}))
                    created += 1
                else:
                    # Giữ trường file không có (giá vốn, giá gốc, ảnh tải lên, cờ phân kho...).
                    merged = {**product.payload, **payload}
                    if 'attributes' in payload:  # chỉ ghi đè thuộc tính file có, giữ các thuộc tính admin đã nhập
                        names = {a['name'] for a in payload['attributes']}
                        merged['attributes'] = [a for a in product.payload.get('attributes', [])
                                                if a.get('name') not in names] + payload['attributes']
                    product.category, product.payload = group, merged
                    product.save(update_fields=['category', 'payload', 'updated_at'])
            warehouses = list(Warehouse.objects.filter(active=True))
            WarehouseStock.objects.bulk_create([
                WarehouseStock(warehouse=w, product=p, quantity=DEFAULT_STOCK_PER_WAREHOUSE)
                for p in new_products for w in warehouses])
            # Sản phẩm đã phân kho: tồn kho tổng tính lại từ các kho, không lấy số trong file.
            sync_product_stock([p.pk for p in [*existing.values(), *new_products]])
        self.stdout.write(self.style.SUCCESS(
            f'Imported {len(prepared)} products ({created} mới, {len(prepared) - created} cập nhật). '
            'Run index_advisor_catalog next.'))

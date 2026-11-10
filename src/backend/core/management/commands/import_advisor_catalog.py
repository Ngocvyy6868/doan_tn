import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.advisor.catalog import category
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
    'expansion_card', 'keyboard', 'headphones', 'monitor', 'network_adapter', 'optical_drive')})
LABELS.update({cat: 'Tản nhiệt' for cat in ('fan', 'fan_controller')})


class Command(BaseCommand):
    help = 'Validate and upsert normalized product JSON; never delete the existing catalog.'

    def add_arguments(self, parser):
        parser.add_argument('file')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        try:
            data = json.loads(Path(options['file']).read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            raise CommandError('Không đọc được JSON sản phẩm.') from exc
        if not isinstance(data, list):
            raise CommandError('Dữ liệu phải là danh sách sản phẩm.')
        prepared, seen = [], set()
        for item in data:
            if not isinstance(item, dict):
                raise CommandError('Mỗi sản phẩm phải là object.')
            key = item.get('id') or item.get('sku')
            cat = category(item.get('product_type') or item.get('cat', item.get('category', '')))
            specs = item.get('specs')
            if not isinstance(key, str) or not 1 <= len(key) <= 64 or key in seen:
                raise CommandError('Mã sản phẩm thiếu, trùng hoặc dài hơn 64 ký tự.')
            if cat not in SPEC_KEYS or not isinstance(specs, dict) or any(k not in specs for k in SPEC_KEYS[cat]):
                raise CommandError(f'{key}: thiếu danh mục/thông số chuẩn; xem docs/Chatbot.md.')
            if not isinstance(item.get('name'), str) or not item['name'].strip():
                raise CommandError(f'{key}: thiếu tên sản phẩm.')
            for field in ('price', 'stock'):
                if type(item.get(field)) is not int or item[field] < 0:
                    raise CommandError(f'{key}: {field} phải là số nguyên không âm.')
            for field in ('has_igpu', 'stock_cooler', 'modular'):
                if specs.get(field) is not None and type(specs[field]) is not bool:
                    raise CommandError(f'{key}: specs.{field} phải là boolean.')
            for field in ('sockets', 'supported_mb'):
                if specs.get(field) is not None and (not isinstance(specs[field], list) or
                                       any(not isinstance(v, str) for v in specs[field])):
                    raise CommandError(f'{key}: specs.{field} phải là danh sách chuỗi.')
            seen.add(key)
            prepared.append((key, cat, {**item, 'id': key, 'product_type': cat, 'cat': LABELS.get(cat, cat)}))
        if options['dry_run']:
            self.stdout.write(f'Validated {len(prepared)} products; no changes.')
            return
        with transaction.atomic():
            for key, cat, payload in prepared:
                group, _ = Category.objects.get_or_create(name=LABELS.get(cat, cat))
                Product.objects.update_or_create(external_id=key, defaults={'category': group, 'payload': payload})
        self.stdout.write(self.style.SUCCESS(f'Imported {len(prepared)} products. Run index_advisor_catalog next.'))

from decimal import Decimal, ROUND_HALF_UP
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Category, Product


# Transcribed from the user's screenshot; no specifications or prices inferred.
ROWS = [
    ('intel-i9-12900kf', 'Intel Core i9-12900KF 3.2 GHz 16-Core', 'CPU', 'Intel', '342.67'),
    ('arctic-liquid-freezer-iii-pro-360', 'ARCTIC Liquid Freezer III Pro A-RGB 360 77 CFM Liquid', 'Tản nhiệt CPU', 'ARCTIC', '76.99'),
    ('msi-mpg-z790-carbon-wifi', 'MSI MPG Z790 CARBON WIFI ATX LGA1700', 'Mainboard', 'MSI', None),
    ('gskill-trident-z5-rgb-32gb-6000', 'G.Skill Trident Z5 RGB 32 GB (2 x 16 GB) DDR5-6000 CL30', 'RAM', 'G.Skill', '599.99'),
    ('samsung-870-evo-500gb', 'Samsung 870 Evo 500 GB 2.5" SSD', 'SSD', 'Samsung', '222.95'),
    ('wd-black-sn850x-4tb', 'Western Digital WD_Black SN850X 4 TB M.2-2280 PCIe 4.0 X4 NVME SSD', 'SSD', 'Western Digital', '699.99'),
    ('wd-black-10tb-7200', 'Western Digital WD_BLACK 10 TB 3.5" 7200 RPM', 'HDD', 'Western Digital', None),
    ('msi-shadow-3x-4070-ti-super', 'MSI SHADOW 3X OC GeForce RTX 4070 Ti SUPER 16 GB', 'VGA', 'MSI', None),
    ('lian-li-o11d-evo-rgb', 'Lian Li O11D EVO RGB ATX Mid Tower', 'Case', 'Lian Li', '159.99'),
    ('lian-li-edge-gold-1000', 'Lian Li EDGE GOLD 1000 W 80+ Gold Certified Fully Modular ATX', 'Nguồn', 'Lian Li', '147.99'),
]


class Command(BaseCommand):
    help = 'Import the 10 products from the supplied screenshot without overwriting existing products.'

    def add_arguments(self, parser):
        parser.add_argument('--rate', required=True, type=Decimal, help='VND per USD')
        parser.add_argument('--stock', default=0, type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        rate, stock = options['rate'], options['stock']
        if not rate.is_finite() or rate <= 0 or stock < 0:
            raise CommandError('Rate must be positive and stock must be nonnegative.')
        created = 0
        for code, name, category_name, brand, usd in ROWS:
            external_id = f'screenshot-{code}'
            if Product.objects.filter(external_id=external_id).exists() or Product.objects.filter(payload__name=name).exists():
                self.stdout.write(f'Skipped existing: {name}')
                continue
            category, _ = Category.objects.get_or_create(name=category_name)
            price = int((Decimal(usd) * rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)) if usd else 0
            description = f'Nhập từ ảnh do người dùng cung cấp. Giá gốc: {usd} USD; tỷ giá: {rate} VND/USD.' if usd else 'Nhập từ ảnh do người dùng cung cấp. Chưa có giá bán; sản phẩm đang ở trạng thái nháp.'
            attributes = []
            if category_name == 'Nguồn':
                attributes = [{'name': 'Công suất', 'value': '1000', 'unit': 'W'}]
            elif category_name == 'Mainboard':
                attributes = [{'name': 'Socket', 'value': 'LGA1700'}, {'name': 'Kích thước', 'value': 'ATX'}]
            elif category_name == 'RAM':
                attributes = [{'name': 'Thế hệ RAM', 'value': 'DDR5'}, {'name': 'Dung lượng', 'value': '32', 'unit': 'GB'}]
                description += ' Sản phẩm bán theo kit 2 × 16 GB; giá áp dụng cho cả kit.'
            payload = dict(id=external_id, name=name, sku=f'IMPORT-{code.upper()}', cat=category_name,
                brand=brand, price=price, old=price, cost=None, stock=stock, active=bool(usd),
                featured=False, img='', badge='', rate=0, reviews=0, description=description,
                productInfo=description, attributes=attributes,
                import_source={'type': 'user_screenshot', 'price_usd': usd, 'vnd_per_usd': str(rate)})
            Product.objects.create(external_id=external_id, category=category, payload=payload)
            created += 1
            self.stdout.write(f'Created: {name} | {price} VND | stock={stock} | active={bool(usd)}')
        self.stdout.write(self.style.SUCCESS(f'Created {created} products.'))

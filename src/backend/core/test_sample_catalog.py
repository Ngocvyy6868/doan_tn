import json
from tempfile import TemporaryDirectory
from pathlib import Path
from django.core.management import call_command, CommandError
from django.test import TestCase
from core.models import Product
from core.advisor.catalog import adapt, available, category


class SampleCatalogImportTests(TestCase):
    def invoke(self, items, **options):
        with TemporaryDirectory() as directory:
            file = Path(directory) / 'catalog.json'
            file.write_text(json.dumps(items), encoding='utf8')
            call_command('import_advisor_catalog', str(file), **options)

    def test_unknown_specs_are_preserved_and_inactive_product_is_unavailable(self):
        item = dict(id='sample', cat='cpu', name='CPU sample', price=0, stock=0, active=False,
                    specs={k: None for k in ('socket', 'cores', 'threads', 'boost_ghz', 'tdp_w', 'has_igpu', 'stock_cooler')})
        self.invoke([item], dry_run=True)
        self.assertFalse(Product.objects.exists())
        self.invoke([item])
        self.invoke([item])
        self.assertEqual(Product.objects.count(), 1)
        product = adapt(Product.objects.get())
        self.assertIsNone(product['specs']['has_igpu'])
        self.assertFalse(available(product))

    def test_hdd_and_peripherals_keep_separate_categories(self):
        self.invoke([dict(id=cat, cat=cat, name=cat, price=100, stock=1, specs={})
                     for cat in ('hdd', 'monitor', 'fan')])
        self.assertEqual(Product.objects.get(external_id='monitor').category.name, 'Thiết bị ngoại vi')
        self.assertEqual(Product.objects.get(external_id='fan').category.name, 'Tản nhiệt')
        self.assertEqual(Product.objects.get(external_id='fan').payload['cat'], 'Tản nhiệt')
        self.assertEqual(category('HDD'), 'hdd')
        self.assertEqual({adapt(p)['cat'] for p in Product.objects.all()}, {'hdd', 'monitor', 'fan'})

    def test_unknown_does_not_allow_malformed_boolean(self):
        item = dict(id='bad', cat='psu', name='PSU', price=100, stock=1,
                    specs=dict(watt=650, efficiency='Gold', modular='unknown'))
        with self.assertRaises(CommandError):
            self.invoke([item])


class CatalogImportValidationTests(TestCase):
    CPU_SPECS = dict(socket='LGA 1700', cores='6', threads=12, boost_ghz='4,4 GHz', tdp_w=65,
                     has_igpu='không', stock_cooler='có')

    def invoke_file(self, name, content, **options):
        with TemporaryDirectory() as directory:
            file = Path(directory) / name
            file.write_text(content, encoding='utf-8-sig')
            call_command('import_advisor_catalog', str(file), **options)

    def invoke(self, items, **options):
        self.invoke_file('catalog.json', json.dumps(items, ensure_ascii=False), **options)

    def test_values_are_normalized_for_rules(self):
        self.invoke([
            dict(id='cpu', cat='cpu', name='CPU', price='2.990.000₫', stock=3, specs=self.CPU_SPECS),
            dict(id='mb', cat='mainboard', name='MB', price=100, stock=1, specs=dict(
                socket='lga1700', chipset='B760', form_factor='mATX', ram_type='ddr4 / ddr5',
                ram_slots=4, max_ram_gb=128, m2_slots=2)),
            dict(id='case', cat='case', name='Case', price=100, stock=1, specs=dict(
                supported_mb='ATX; micro-atx; ITX', max_gpu_length_mm='360 mm', max_cooler_height_mm=165)),
            dict(id='cool', cat='tản nhiệt', name='Cooler', price=100, stock=1, specs=dict(
                cooler_type='Tản nước', sockets='LGA 1700, am5', height_mm=None, tdp_w=None)),
            dict(id='ssd', cat='ssd', name='SSD', price=100, stock=1, specs=dict(interface='NVMe', capacity_gb=1000, pcie_gen=4)),
        ])
        specs = {p.external_id: p.payload['specs'] for p in Product.objects.all()}
        self.assertEqual(Product.objects.get(external_id='cpu').payload['price'], 2990000)
        self.assertEqual((specs['cpu']['socket'], specs['cpu']['cores'], specs['cpu']['boost_ghz']), ('LGA1700', 6, 4.4))
        self.assertEqual((specs['cpu']['has_igpu'], specs['cpu']['stock_cooler']), (False, True))
        self.assertEqual((specs['mb']['socket'], specs['mb']['form_factor'], specs['mb']['ram_type']), ('LGA1700', 'Micro ATX', 'DDR4/DDR5'))
        attributes = {a['name']: a['value'] for a in Product.objects.get(external_id='mb').payload['attributes']}
        self.assertEqual(attributes['Thế hệ RAM hỗ trợ'], 'DDR4, DDR5')  # luật Mainboard–RAM tách theo dấu phẩy
        self.assertEqual(specs['case']['supported_mb'], ['ATX', 'Micro ATX', 'Mini ITX'])
        self.assertEqual(specs['case']['max_gpu_length_mm'], 360)
        self.assertEqual((specs['cool']['cooler_type'], specs['cool']['sockets']), ('liquid', ['LGA1700', 'AM5']))
        self.assertEqual(specs['ssd']['interface'], 'nvme')
        from core.advisor.rules import check_build
        checks = {c['code']: c['status'] for c in check_build([adapt(p) for p in Product.objects.filter(
            external_id__in=['cpu', 'mb', 'case'])], final=False)}
        self.assertEqual((checks['R1'], checks['R9']), ('pass', 'pass'))

    def test_all_errors_are_reported_and_nothing_is_written(self):
        items = [
            dict(id='ok', cat='cpu', name='CPU', price=1, stock=1, specs=self.CPU_SPECS),
            dict(id='bad-ram', cat='ram', name='RAM', price=1, stock=1, specs=dict(
                ram_type='DDR5-6000', capacity_gb=32, modules=2, speed_mhz=6000)),
            dict(id='bad-mb', cat='mainboard', name='MB', price=1, stock=1, specs=dict(
                socket='AM5', chipset='B650', form_factor='Nano', ram_type='DDR5', ram_slots=4, max_ram_gb=192, m2_slots=2)),
            dict(id='bad-price', cat='psu', name='PSU', price=-5, stock=1, specs=dict(watt=650, efficiency='Gold', modular=False)),
            dict(id='missing', cat='gpu', name='GPU', price=1, stock=1, specs=dict(chip='RTX')),
            dict(id='ok', cat='cpu', name='Dup', price=1, stock=1, specs=self.CPU_SPECS),
        ]
        with self.assertRaises(CommandError) as ctx:
            self.invoke(items)
        message = str(ctx.exception)
        self.assertIn('5/6', message)
        for key in ('bad-ram', 'bad-mb', 'bad-price', 'missing', 'trùng'):
            self.assertIn(key, message)
        self.assertFalse(Product.objects.exists())

    def test_csv_import_uses_template_columns(self):
        header = 'id,name,brand,category,price,stock,active,socket,cores,threads,boost_ghz,tdp_w,has_igpu,stock_cooler,watt,efficiency,modular\n'
        rows = ('c1,CPU A,Intel,cpu,"2.990.000",5,có,LGA1700,6,12,4.4,65,có,có,,,\n'
                'p1,PSU B,CM,nguồn,1290000,2,,,,,,,,,650,80 Plus Bronze,không\n')
        self.invoke_file('catalog.csv', header + rows)
        cpu, psu = Product.objects.get(external_id='c1').payload, Product.objects.get(external_id='p1').payload
        self.assertEqual((cpu['price'], cpu['active'], cpu['product_type']), (2990000, True, 'cpu'))
        self.assertNotIn('watt', cpu['specs'])  # cột của nhóm khác bị bỏ
        self.assertEqual((psu['specs']['watt'], psu['specs']['modular'], psu['cat']), (650, False, 'Nguồn'))
        self.assertIs(psu['active'], True)  # ô active trống: sản phẩm mới mặc định hiển thị

    def test_reimport_keeps_admin_fields_and_warehouse_stock(self):
        from core.models import Warehouse, WarehouseStock
        item = dict(id='cpu', cat='cpu', name='CPU', price=100, stock=50, specs=self.CPU_SPECS)
        self.invoke([item])
        product = Product.objects.get()
        product.payload = {**product.payload, 'cost': 70, 'old': 150, 'img': '/api/product-images/1/'}
        product.save()
        warehouse = Warehouse.objects.create(code='HN01', address='12 Tràng Tiền, Hà Nội')
        WarehouseStock.objects.create(warehouse=warehouse, product=product, quantity=4)
        self.invoke([{**item, 'name': 'CPU mới', 'price': 120}])
        payload = Product.objects.get().payload
        self.assertIs(payload['active'], True)  # nhập mới mặc định hiển thị
        self.assertEqual((payload['name'], payload['price']), ('CPU mới', 120))
        self.assertEqual((payload['cost'], payload['old'], payload['img']), (70, 150, '/api/product-images/1/'))
        self.assertEqual(payload['stock'], 4)

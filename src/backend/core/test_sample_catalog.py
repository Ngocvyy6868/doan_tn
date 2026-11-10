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

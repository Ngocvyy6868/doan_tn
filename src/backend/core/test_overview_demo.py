from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Order, Product


class OverviewDemoTests(TestCase):
    def test_repeatable_seed_and_report_totals(self):
        for index, category in enumerate(['CPU', 'RAM', 'SSD']):
            Product.objects.create(external_id=str(index), payload={
                'name': category, 'cat': category, 'price': (index + 1) * 100000, 'stock': 20,
            })
        existing = Order.objects.create(code='EXISTING', status=Order.Status.CONFIRMED)
        call_command('seed_overview_demo', stdout=StringIO())
        first_count = Order.objects.count()
        call_command('seed_overview_demo', stdout=StringIO())
        self.assertEqual(first_count, 25)
        self.assertEqual(Order.objects.count(), first_count)
        existing.refresh_from_db()
        self.assertEqual(existing.status, Order.Status.CONFIRMED)
        self.assertTrue(all(p.payload['stock'] == 20 for p in Product.objects.all()))
        report = self.client.get(reverse('admin-overview')).json()
        self.assertEqual(report['summary']['orders'], 24)
        self.assertGreater(report['summary']['revenue'], 0)
        self.assertEqual(len(report['groups']), 3)
        for field in ['series', 'groups', 'channels']:
            self.assertEqual(sum(row['value'] for row in report[field]), report['summary']['revenue'])

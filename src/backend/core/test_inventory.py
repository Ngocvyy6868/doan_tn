import json

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Order, Product, Warehouse, WarehouseStock


class InventoryTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('admin@test.vn', password='x', is_staff=True)
        self.customer = User.objects.create_user('khach@test.vn', password='x')
        self.product = Product.objects.create(external_id='ssd-1', payload={'id': 'ssd-1', 'name': 'SSD', 'stock': 7, 'active': True})
        self.client.force_login(self.staff)

    def post(self, url, data, method='post'):
        return getattr(self.client, method)(url, json.dumps(data), content_type='application/json')

    def create_warehouse(self, code='HN01', address='12 Tràng Tiền, Hoàn Kiếm, Hà Nội'):
        response = self.post('/api/admin/warehouses/', {'code': code, 'address': address})
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()['warehouse']

    def test_create_warehouse_normalizes_and_rejects_duplicates(self):
        warehouse = self.create_warehouse(code='hn01')
        self.assertEqual(warehouse['code'], 'HN01')
        duplicate = self.post('/api/admin/warehouses/', {'code': 'HN01', 'address': 'Địa chỉ khác ở Hà Nội'})
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(self.post('/api/admin/warehouses/', {'code': 'A', 'address': '12 Tràng Tiền'}).status_code, 400)
        self.assertEqual(self.post('/api/admin/warehouses/', {'code': 'HCM01', 'address': 'Q1'}).status_code, 400)

    def test_requires_staff(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get('/api/admin/warehouses/').status_code, 403)
        self.assertEqual(self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': 1, 'quantity': 1}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get('/api/admin/inventory/').status_code, 403)

    def test_add_and_set_quantity_sync_total_stock(self):
        hn, hcm = self.create_warehouse(), self.create_warehouse('HCM01', '45 Lê Lợi, Quận 1, TP.HCM')
        self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': 5})
        response = self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': 3})
        self.assertEqual(response.json()['stocks'][str(hn['id'])], 8)
        response = self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hcm['id'], 'quantity': 2, 'mode': 'set'})
        self.assertEqual(response.json()['stock'], 10)
        self.product.refresh_from_db()
        self.assertEqual(self.product.payload['stock'], 10)
        self.assertTrue(self.product.payload['warehouse_managed'])

    def test_rejects_negative_result_and_bad_quantity(self):
        hn = self.create_warehouse()
        self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': 2})
        self.assertEqual(self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': -5}).status_code, 400)
        self.assertEqual(self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': '3'}).status_code, 400)
        self.assertEqual(self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': -1, 'mode': 'set'}).status_code, 400)
        self.assertEqual(self.post('/api/admin/inventory/', {'product_id': 'nope', 'warehouse_id': hn['id'], 'quantity': 1}).status_code, 404)
        self.assertEqual(WarehouseStock.objects.get().quantity, 2)

    def test_inactive_warehouse_excluded_from_total_and_availability(self):
        hn, hcm = self.create_warehouse(), self.create_warehouse('HCM01', '45 Lê Lợi, Quận 1, TP.HCM')
        self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': 4})
        self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hcm['id'], 'quantity': 6})
        self.post(f"/api/admin/warehouses/{hcm['id']}/", {'active': False}, method='patch')
        self.product.refresh_from_db()
        self.assertEqual(self.product.payload['stock'], 4)
        self.client.logout()
        data = self.client.get('/api/products/ssd-1/availability/').json()
        self.assertTrue(data['managed'])
        self.assertEqual([s['code'] for s in data['stores']], ['HN01'])

    def test_availability_for_unmanaged_product(self):
        self.client.logout()
        data = self.client.get('/api/products/ssd-1/availability/').json()
        self.assertEqual(data, {'managed': False, 'stores': []})
        self.assertEqual(self.client.get('/api/products/missing/availability/').status_code, 404)

    def test_delete_warehouse_only_when_empty(self):
        hn = self.create_warehouse()
        self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': 1})
        self.assertEqual(self.client.delete(f"/api/admin/warehouses/{hn['id']}/").status_code, 400)
        self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': 0, 'mode': 'set'})
        self.assertEqual(self.client.delete(f"/api/admin/warehouses/{hn['id']}/").status_code, 200)
        self.assertFalse(Warehouse.objects.exists())
        self.product.refresh_from_db()
        self.assertNotIn('warehouse_managed', self.product.payload)

    def test_product_form_save_cannot_override_warehouse_stock(self):
        hn = self.create_warehouse()
        self.post('/api/admin/inventory/', {'product_id': 'ssd-1', 'warehouse_id': hn['id'], 'quantity': 3})
        response = self.client.put('/api/admin/products/', json.dumps([{'id': 'ssd-1', 'name': 'SSD mới', 'stock': 99}]),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual((self.product.payload['name'], self.product.payload['stock']), ('SSD mới', 3))


class OrderStockTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('admin@test.vn', password='x', is_staff=True)
        self.product = Product.objects.create(external_id='ssd-1', payload={'id': 'ssd-1', 'name': 'SSD', 'stock': 0, 'active': True})
        self.manual = Product.objects.create(external_id='ram-1', payload={'id': 'ram-1', 'name': 'RAM', 'stock': 5, 'active': True})
        self.hn = Warehouse.objects.create(code='HN01', address='12 Tràng Tiền, Hà Nội')
        self.hcm = Warehouse.objects.create(code='HCM01', address='45 Lê Lợi, TP.HCM')
        self.closed = Warehouse.objects.create(code='DN01', address='1 Bạch Đằng, Đà Nẵng', active=False)
        for warehouse, quantity in ((self.hn, 2), (self.hcm, 3), (self.closed, 50)):
            WarehouseStock.objects.create(warehouse=warehouse, product=self.product, quantity=quantity)

    def order(self, code, items):
        body = {'code': code, 'address': {'name': 'Khách', 'phone': '0901234567', 'province': 'Hà Nội', 'address': '1 Phố Huế'},
                'items': [{'productId': pid, 'name': pid, 'quantity': q, 'price': 100, 'total': 100 * q} for pid, q in items],
                'totals': {'subtotal': 0, 'grandTotal': 0}}
        return self.client.post('/api/orders/', json.dumps(body), content_type='application/json')

    def quantities(self):
        return {r.warehouse.code: r.quantity for r in WarehouseStock.objects.select_related('warehouse')}

    def test_order_deducts_from_active_warehouses_and_manual_stock(self):
        response = self.order('TZ1', [('ssd-1', 4), ('ram-1', 2), ('unknown', 1)])
        self.assertEqual(response.status_code, 201, response.content)
        q = self.quantities()
        self.assertEqual(q['HN01'] + q['HCM01'], 1)
        self.assertEqual(q['DN01'], 50)
        self.product.refresh_from_db(); self.manual.refresh_from_db()
        self.assertEqual((self.product.payload['stock'], self.manual.payload['stock']), (1, 3))
        items = {i['product_id']: i for i in response.json()['order']['items']}
        self.assertEqual(sum(w['quantity'] for w in items['ssd-1']['warehouses']), 4)

    def test_insufficient_stock_rejects_whole_order(self):
        response = self.order('TZ2', [('ram-1', 1), ('ssd-1', 6)])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'OUT_OF_STOCK')
        self.assertEqual(response.json()['remaining'], 5)
        self.manual.refresh_from_db()
        self.assertEqual(self.manual.payload['stock'], 5)
        self.assertEqual(self.quantities(), {'HN01': 2, 'HCM01': 3, 'DN01': 50})
        self.assertFalse(Order.objects.exists())

    def test_cancel_returns_stock_to_same_warehouses_once(self):
        self.order('TZ3', [('ssd-1', 5), ('ram-1', 5)])
        self.assertEqual(self.quantities(), {'HN01': 0, 'HCM01': 0, 'DN01': 50})
        order = Order.objects.get(code='TZ3')
        order.status = Order.Status.DELIVERED
        order.save()
        self.client.force_login(self.staff)
        for _ in range(2):
            self.client.patch(f'/api/admin/orders/{order.pk}/', json.dumps({'status': 'CANCELLED'}), content_type='application/json')
        self.assertEqual(self.quantities(), {'HN01': 2, 'HCM01': 3, 'DN01': 50})
        self.product.refresh_from_db(); self.manual.refresh_from_db()
        self.assertEqual((self.product.payload['stock'], self.manual.payload['stock']), (5, 5))

from django.test import TestCase
from django.urls import reverse

from .models import Order
from .models import Employee, KnowledgeDocument
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO


class OrderStatusSyncTests(TestCase):
    def test_checkout_total_and_shipping_details(self):
        for field in ['grandTotal', 'grand_total']:
            response = self.client.post(reverse('create-order'), {
                'code': f'TOTAL-{field}',
                'address': {'name': 'Recipient', 'phone': '0901234567', 'province': 'City', 'address': '123 Street'},
                'totals': {'subtotal': 100000, 'shipping': 30000, field: 130000},
                'shipping_method': 'express',
                'items': [{'productId': '1', 'name': 'Product', 'price': 100000, 'quantity': 1, 'total': 100000}],
            }, content_type='application/json')
            self.assertEqual(response.status_code, 201)
            order = response.json()['order']
            self.assertEqual(order['totals']['grand_total'], 130000)
            self.assertEqual(order['recipient']['address'], '123 Street')
            self.assertEqual(order['shipping_method'], 'express')

    def setUp(self):
        self.order = Order.objects.create(
            code='TZ-STATUS-TEST', recipient_name='Test customer',
            recipient_phone='0901234567', province='Test province',
            address='Test address', payment_method='COD', shipping_method='standard',
            status=Order.Status.PENDING_PAYMENT,
        )

    def status_request(self, phone='0901234567'):
        return self.client.post(reverse('order-status'),
                                {'code': self.order.code, 'phone': phone},
                                content_type='application/json')

    def test_customer_reads_each_status_saved_by_admin(self):
        for status in Order.Status.values:
            with self.subTest(status=status):
                response = self.client.patch(
                    reverse('admin-order-update', args=[self.order.pk]),
                    {'status': status}, content_type='application/json',
                )
                self.assertEqual(response.status_code, 200)
                response = self.status_request()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {
                    'code': self.order.code, 'status': status, 'paymentStatus': 'UNPAID',
                })
                self.assertEqual(response['Cache-Control'], 'no-store')

    def test_wrong_phone_cannot_read_status(self):
        self.assertEqual(self.status_request('0900000000').status_code, 404)

    def test_reject_skipped_backward_and_terminal_transitions(self):
        sequence = Order.Status.values
        for index, current in enumerate(sequence):
            for target in sequence:
                if target == current or (index + 1 < len(sequence) and target == sequence[index + 1]):
                    continue
                with self.subTest(current=current, target=target):
                    self.order.status = current
                    self.order.save()
                    response = self.client.patch(
                        reverse('admin-order-update', args=[self.order.pk]),
                        {'status': target}, content_type='application/json',
                    )
                    self.assertEqual(response.status_code, 400)
                    self.order.refresh_from_db()
                    self.assertEqual(self.order.status, current)

    def test_reject_unknown_status(self):
        for status in ['UNKNOWN', None, '']:
            response = self.client.patch(
                reverse('admin-order-update', args=[self.order.pk]),
                {'status': status}, content_type='application/json',
            )
            self.assertEqual(response.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)

    def test_patch_without_status_preserves_status(self):
        response = self.client.patch(
            reverse('admin-order-update', args=[self.order.pk]),
            {}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)

    def test_invalid_payload(self):
        response = self.client.post(reverse('order-status'), [], content_type='application/json')
        self.assertEqual(response.status_code, 400)


class FlashSaleTests(TestCase):
    def test_schedule_public_listing_and_overlap(self):
        from .models import Product, FlashSale
        from django.utils import timezone
        from datetime import timedelta
        Product.objects.create(external_id='1', payload={'id': 1, 'name': 'CPU', 'price': 100, 'cost': 50})
        now = timezone.now()
        values = {'product_id': '1', 'quantity': 3, 'starts_at': (now-timedelta(hours=1)).isoformat(), 'ends_at': (now+timedelta(hours=1)).isoformat()}
        response = self.client.post(reverse('admin-flash-sales'), values, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.post(reverse('admin-flash-sales'), values, content_type='application/json').status_code, 400)
        public = self.client.get(reverse('flash-sales')).json()['results']
        self.assertEqual(len(public), 1)
        self.assertNotIn('cost', public[0]['product'])
        sale = FlashSale.objects.get()
        sale.ends_at = now-timedelta(minutes=1)
        sale.save()
        self.assertEqual(self.client.get(reverse('flash-sales')).json()['results'], [])

    def test_sale_quantity_is_consumed_and_cannot_be_exceeded(self):
        from .models import FlashSale
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        sale = FlashSale.objects.create(product_external_id='1', quantity=2, starts_at=now-timedelta(hours=1), ends_at=now+timedelta(hours=1))
        values = {'code': 'SALE-1', 'address': {'name': 'Buyer', 'phone': '0901234567', 'province': 'City', 'address': 'Street'}, 'items': [{'productId': '1', 'name': 'CPU', 'quantity': 2, 'price': 100, 'total': 200}], 'totals': {'subtotal': 200, 'grandTotal': 200}}
        self.assertEqual(self.client.post(reverse('create-order'), values, content_type='application/json').status_code, 201)
        sale.refresh_from_db()
        self.assertEqual(sale.sold, 2)
        values['code'] = 'SALE-2'
        self.assertEqual(self.client.post(reverse('create-order'), values, content_type='application/json').status_code, 400)


class ProductCostTests(TestCase):
    def test_cost_persistence_and_validation(self):
        url = reverse('admin-products')
        for cost in [None, 0, 1250000]:
            response = self.client.put(url, [{'id': 'cost-test', 'name': 'Product', 'cost': cost}], content_type='application/json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.client.get(url).json()['results'][0]['cost'], cost)
        for cost in [-1, 'invalid', True, 1.5]:
            response = self.client.put(url, [{'id': 'cost-test', 'name': 'Product', 'cost': cost}], content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.client.get(url).json()['results'][0]['cost'], 1250000)


class OverviewTests(TestCase):
    def test_revenue_filters_and_inventory(self):
        from .models import Product, OrderItem
        from django.utils import timezone
        Product.objects.create(external_id='cpu', payload={'name': 'CPU', 'cat': 'CPU', 'brand': 'AMD', 'stock': 3})
        Product.objects.create(external_id='ram', payload={'name': 'RAM', 'cat': 'RAM', 'brand': 'Corsair', 'stock': 20})
        for status in [Order.Status.DELIVERED, Order.Status.CANCELLED, Order.Status.CONFIRMED]:
            order = Order.objects.create(code=status, status=status)
            OrderItem.objects.create(order=order, product_external_id='cpu', sku='CPU', name='CPU', unit_price=100, quantity=2, total=200)
            OrderItem.objects.create(order=order, product_external_id='ram', sku='RAM', name='RAM', unit_price=50, quantity=1, total=50)
        params = {'start': str(timezone.localdate()), 'end': str(timezone.localdate())}
        response = self.client.get(reverse('admin-overview'), params)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['summary'], {'revenue': 250, 'quantity': 3, 'orders': 1, 'profit': None, 'margin': None})
        self.assertEqual(data['low_stock'][0]['id'], 'cpu')
        self.assertEqual(sum(row['value'] for row in data['series']), 250)
        filtered = self.client.get(reverse('admin-overview'), {**params, 'category': 'CPU', 'brand': 'AMD', 'group': 'month'}).json()
        self.assertEqual(filtered['summary']['revenue'], 200)
        self.assertEqual(len(filtered['products']), 1)
        self.assertEqual(len(filtered['series']), 1)

    def test_bad_dates(self):
        for params in [{'start': 'bad'}, {'start': '2026-02-01', 'end': '2026-01-01'}]:
            self.assertEqual(self.client.get(reverse('admin-overview'), params).status_code, 400)


class CompatibilityRuleTests(TestCase):
    def test_crud_and_validation(self):
        url = reverse('compatibility-rules')
        values = {'name': 'Socket', 'source_category': 'CPU', 'source_attribute': 'Socket',
                  'target_category': 'Mainboard', 'target_attribute': 'Socket', 'operator': 'equal', 'active': True}
        response = self.client.post(url, values, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        detail = reverse('compatibility-rule-detail', args=[response.json()['rule']['id']])
        self.assertEqual(len(self.client.get(url).json()['results']), 1)
        response = self.client.patch(detail, {'active': False}, content_type='application/json')
        self.assertFalse(response.json()['rule']['active'])
        response = self.client.patch(detail, {'operator': 'invalid'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response = self.client.post(url, {**values, 'target_category': 'CPU'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.delete(detail).status_code, 200)
        self.assertEqual(self.client.get(url).json()['results'], [])


class AdminManagementTests(TestCase):
    def test_employee_roles(self):
        for index, role in enumerate(Employee.Role.values):
            response = self.client.post(reverse('admin-employees'), {
                'full_name': 'Role Test', 'phone': f'090123456{index}',
                'email': 'role@example.com', 'role': role,
            }, content_type='application/json')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()['employee']['role'], role)
        for role in [None, '', 'ADMIN']:
            response = self.client.post(reverse('admin-employees'), {
                'full_name': 'Invalid Role', 'phone': '0901234599',
                'email': 'role@example.com', 'role': role,
            }, content_type='application/json')
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Employee.objects.count(), 2)

    def test_create_assign_and_deactivate_employee(self):
        response = self.client.post(reverse('admin-employees'), {
            'role': 'WAREHOUSE', 'full_name': 'Test Employee', 'phone': '0901234567', 'email': 'employee@example.com',
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        employee = Employee.objects.get()
        self.assertEqual(employee.role, Employee.Role.WAREHOUSE)
        self.assertEqual(response.json()['employee']['role'], 'WAREHOUSE')
        self.assertFalse(employee.user.has_usable_password())
        self.assertFalse(employee.user.is_staff)
        order = Order.objects.create(code='ASSIGN', recipient_name='Customer', recipient_phone='0900000000')
        url = reverse('admin-order-update', args=[order.pk])
        response = self.client.patch(url, {'handler_id': employee.user_id}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.handler_id, employee.user_id)
        self.client.patch(reverse('admin-employee-detail', args=[employee.pk]), {'active': False}, content_type='application/json')
        self.assertEqual(self.client.patch(url, {'handler_id': employee.user_id}, content_type='application/json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'handler_id': None}, content_type='application/json').status_code, 200)
        order.refresh_from_db()
        self.assertIsNone(order.handler_id)

    def test_import_formats_and_preview(self):
        from docx import Document
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        docx = BytesIO()
        document = Document()
        document.add_paragraph('Knowledge Word')
        document.save(docx)
        pdf = BytesIO()
        writer = PdfWriter()
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 20 250 Td (Knowledge PDF) Tj ET')
        page[NameObject('/Contents')] = stream
        writer.write(pdf)
        for name, data in [('test.md', b'# Knowledge MD'), ('test.csv', b'name,value\nKnowledge,CSV'), ('test.docx', docx.getvalue()), ('test.pdf', pdf.getvalue())]:
            with self.subTest(name=name):
                response = self.client.post(reverse('admin-documents'), {'file': SimpleUploadedFile(name, data)})
                self.assertEqual(response.status_code, 201, response.content)
                document_id = response.json()['document']['id']
                document = KnowledgeDocument.objects.get(pk=document_id)
                self.assertEqual(bytes(document.content), data)
                response = self.client.get(reverse('admin-document-detail', args=[document_id]))
                self.assertIn('Knowledge', response.json()['document']['text'])

    def test_reject_invalid_files(self):
        for name, data in [('bad.exe', b'content'), ('bad.pdf', b'broken'), ('empty.md', b''), ('large.csv', b'x' * (5 * 1024 * 1024 + 1))]:
            response = self.client.post(reverse('admin-documents'), {'file': SimpleUploadedFile(name, data)})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(KnowledgeDocument.objects.count(), 0)

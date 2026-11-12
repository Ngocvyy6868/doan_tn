import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Customer, CustomerEvent, Order, OrderItem, Product


class CustomerCrmTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff', is_staff=True, first_name='Lan')
        self.user = User.objects.create_user(username='buyer@example.com', email='buyer@example.com', password='Test-password-123')
        self.customer = Customer.objects.create(user=self.user, full_name='Buyer', phone='0901234567')
        self.other = Customer.objects.create(user=User.objects.create_user(username='other'), full_name='Other', phone='0901234568')

    def url(self, name, *extra):
        return reverse(name, args=[self.customer.pk, *extra])

    def test_staff_required(self):
        for user in (None, self.user):
            if user:
                self.client.force_login(user)
            for name in ('admin-customer-profile', 'admin-customer-events', 'admin-customer-notes', 'admin-customer-tasks'):
                self.assertEqual(self.client.get(self.url(name)).status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('admin-customer-profile', args=[99999])).status_code, 404)

    def test_profile_stats_tier_and_interests(self):
        Product.objects.create(external_id='cpu-1', payload={'name': 'CPU', 'cat': 'CPU'})
        paid = Order.objects.create(customer=self.customer, code='A1', recipient_name='B', recipient_phone='0901234567',
                                    grand_total=6_000_000)
        OrderItem.objects.create(order=paid, product_external_id='cpu-1', sku='C', name='CPU', unit_price=3_000_000, quantity=2, total=6_000_000)
        Order.objects.create(customer=self.customer, code='A2', recipient_name='B', recipient_phone='0901234567',
                             grand_total=90_000_000, status=Order.Status.CANCELLED)
        self.client.force_login(self.staff)
        profile = self.client.get(self.url('admin-customer-profile')).json()['profile']
        self.assertEqual((profile['stats']['orders'], profile['stats']['cancelled'], profile['stats']['total_spent']), (1, 1, 6_000_000))
        self.assertEqual(profile['tier'], 'Bạc')
        self.assertEqual(profile['next_tier'], {'name': 'Vàng', 'remaining': 14_000_000})
        self.assertEqual(profile['interests'], [{'category': 'CPU', 'quantity': 2}])

    def test_customer_actions_are_recorded_as_events(self):
        self.client.post(reverse('login'), {'email': 'buyer@example.com', 'password': 'Test-password-123'}, content_type='application/json')
        self.client.patch(reverse('profile'), {'full_name': 'Buyer Mới'}, content_type='application/json')
        address = dict(fullName='Buyer', phone='0901234567', provinceCode='01', provinceName='Hà Nội', wardCode='001', wardName='Ba Đình', detail='1 Phố')
        self.client.post(reverse('addresses'), address, content_type='application/json')
        types = list(self.customer.events.values_list('type', flat=True))
        for expected in ('LOGIN', 'PROFILE_UPDATED', 'ADDRESS_ADDED'):
            self.assertIn(expected, types)
        change = self.customer.events.get(type='PROFILE_UPDATED').data['changes']
        self.assertEqual(change, [{'field': 'Họ tên', 'from': 'Buyer', 'to': 'Buyer Mới'}])
        self.assertTrue(all(source == 'customer' for source in self.customer.events.values_list('source', flat=True)))

    def test_staff_order_status_event_and_event_filters(self):
        order = Order.objects.create(customer=self.customer, code='S1', recipient_name='B', recipient_phone='0901234567')
        self.client.force_login(self.staff)
        self.client.patch(reverse('admin-order-update', args=[order.pk]), {'status': 'PACKING'}, content_type='application/json')
        event = self.customer.events.get(type='ORDER_STATUS')
        self.assertEqual((event.source, event.actor, event.data['to_label']), ('staff', self.staff, 'Đang đóng gói'))
        CustomerEvent.objects.create(customer=self.customer, type='LOGIN', title='Đăng nhập',
                                     created_at=timezone.now() - datetime.timedelta(days=60))
        CustomerEvent.objects.create(customer=self.other, type='LOGIN', title='Đăng nhập')
        recent = self.client.get(self.url('admin-customer-events')).json()
        self.assertEqual([e['type'] for e in recent['results']], ['ORDER_STATUS'])
        everything = self.client.get(self.url('admin-customer-events') + '?days=all&types=LOGIN').json()
        self.assertEqual(everything['total'], 1)
        self.assertEqual(self.client.get(self.url('admin-customer-events') + '?days=abc').status_code, 400)

    def test_notes_crud(self):
        self.client.force_login(self.staff)
        created = self.client.post(self.url('admin-customer-notes'), {'content': ' Khách thích tản nhiệt nước '}, content_type='application/json')
        self.assertEqual(created.status_code, 201)
        note = created.json()['result']
        self.assertEqual((note['content'], note['author']), ('Khách thích tản nhiệt nước', 'Lan'))
        self.assertTrue(self.customer.events.filter(type='NOTE_ADDED').exists())
        detail = self.url('admin-customer-note-detail', note['id'])
        self.assertTrue(self.client.patch(detail, {'pinned': True}, content_type='application/json').json()['result']['pinned'])
        self.assertEqual(self.client.post(self.url('admin-customer-notes'), {'content': ' '}, content_type='application/json').status_code, 400)
        wrong = reverse('admin-customer-note-detail', args=[self.other.pk, note['id']])
        self.assertEqual(self.client.delete(wrong).status_code, 404)
        self.assertEqual(self.client.delete(detail).status_code, 200)
        self.assertFalse(self.customer.notes.exists())

    def test_tasks_lifecycle(self):
        order = Order.objects.create(customer=self.customer, code='T1', recipient_name='B', recipient_phone='0901234567')
        foreign = Order.objects.create(customer=self.other, code='T2', recipient_name='O', recipient_phone='0901234568')
        self.client.force_login(self.staff)
        url = self.url('admin-customer-tasks')
        bad = self.client.post(url, {'type': 'COMPLAINT', 'order_id': foreign.pk}, content_type='application/json')
        self.assertEqual(bad.status_code, 400)
        task = self.client.post(url, {'type': 'COMPLAINT', 'title': 'Giao hàng chậm', 'order_id': order.pk, 'channel': 'phone',
                                      'due_at': '2026-11-20T09:00:00'}, content_type='application/json').json()['result']
        self.assertEqual((task['status'], task['order']['code'], task['assignee']['name']), ('TODO', 'T1', 'Lan'))
        done = self.client.patch(self.url('admin-customer-task-detail', task['id']),
                                 {'status': 'DONE', 'result': 'Đã gọi xin lỗi, tặng voucher'}, content_type='application/json').json()['result']
        self.assertEqual((done['status_label'], bool(done['completed_at'])), ('Đã phản hồi phản ánh', True))
        events = list(self.customer.events.order_by('id').values_list('type', 'title'))
        self.assertEqual(events, [('TASK_CREATED', 'Tạo công việc: Giao hàng chậm'),
                                  ('TASK_COMPLETED', 'Đã phản hồi phản ánh: Giao hàng chậm')])
        listing = self.client.get(url).json()
        self.assertEqual(len(listing['results']), 1)
        self.assertIn({'value': order.pk, 'label': 'T1'}, listing['options']['orders'])
        self.assertNotIn({'value': foreign.pk, 'label': 'T2'}, listing['options']['orders'])
        quick = self.client.post(url, {'type': 'CONTACT', 'status': 'DONE', 'channel': 'zalo'}, content_type='application/json').json()['result']
        self.assertEqual((quick['title'], quick['status_label']), ('Liên hệ khách hàng', 'Đã liên hệ'))
        self.assertEqual(self.client.post(url, {'channel': 'pigeon'}, content_type='application/json').status_code, 400)

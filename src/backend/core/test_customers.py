from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Address, Customer, Order


class AdminCustomerTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='admin', is_staff=True)
        self.user = User.objects.create_user(username='buyer')
        self.customer = Customer.objects.create(user=self.user, full_name='Buyer', phone='0901234567')
        self.other = Customer.objects.create(user=User.objects.create_user(username='other'), full_name='Other', phone='0901234568')
        self.payload = dict(fullName='Buyer', phone='0901234567', provinceCode='01', provinceName='City', wardCode='001', wardName='Ward', detail='Street')
        self.url = reverse('admin-customer-addresses', args=[self.customer.pk])

    def test_admin_access_required(self):
        for user in [None, self.user]:
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.client.post(self.url, self.payload, content_type='application/json').status_code, 403)
            self.assertEqual(self.client.get(reverse('admin-customer-orders', args=[self.customer.pk])).status_code, 403)

    def test_address_management_and_customer_scope(self):
        self.client.force_login(self.staff)
        first = self.client.post(self.url, self.payload, content_type='application/json')
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.json()['result']['isDefault'])
        second = self.client.post(self.url, {**self.payload, 'detail': 'Second'}, content_type='application/json').json()['result']
        detail = reverse('admin-customer-address-detail', args=[self.customer.pk, second['id']])
        self.assertEqual(self.client.patch(detail, {'isDefault': True}, content_type='application/json').status_code, 200)
        self.assertEqual(self.customer.addresses.filter(is_default=True).count(), 1)
        wrong = reverse('admin-customer-address-detail', args=[self.other.pk, second['id']])
        self.assertEqual(self.client.delete(wrong).status_code, 404)
        self.assertEqual(self.client.delete(detail).status_code, 200)
        self.assertTrue(self.customer.addresses.get().is_default)

    def test_purchase_history_excludes_other_customers(self):
        self.client.force_login(self.staff)
        Order.objects.create(customer=self.customer, code='OWN', recipient_name='Buyer', recipient_phone='0901234567')
        Order.objects.create(customer=self.other, code='OTHER', recipient_name='Other', recipient_phone='0901234568')
        response = self.client.get(reverse('admin-customer-orders', args=[self.customer.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([o['code'] for o in response.json()['results']], ['OWN'])
        self.assertEqual(self.client.get(reverse('admin-customer-orders', args=[99999])).status_code, 404)

    def test_admin_login_rejects_customer_without_starting_session(self):
        self.user.set_password('Test-password-123')
        self.user.save()
        response = self.client.post(reverse('login'), {'email': self.user.username, 'password': 'Test-password-123', 'admin_only': True}, content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_admin_login_allows_staff_to_read_customer_details(self):
        self.staff.set_password('Test-password-123')
        self.staff.save()
        response = self.client.post(reverse('login'), {'email': self.staff.username, 'password': 'Test-password-123', 'admin_only': True}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_admin_session_and_logout(self):
        url = reverse('admin-session')
        self.assertIsNone(self.client.get(url).json()['user'])
        self.client.force_login(self.user)
        self.assertIsNone(self.client.get(url).json()['user'])
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).json()['user']['id'], self.staff.pk)
        self.assertEqual(self.client.post(reverse('logout')).status_code, 200)
        self.assertIsNone(self.client.get(url).json()['user'])
        self.assertEqual(self.client.get(self.url).status_code, 403)

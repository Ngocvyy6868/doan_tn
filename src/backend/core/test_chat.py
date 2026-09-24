from unittest.mock import patch
from urllib.error import HTTPError

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase, override_settings

from .chat_service import ChatUnavailable, advise, check_compatibility, generate
from .models import Product


class RuleTests(SimpleTestCase):
    def test_rules_and_missing_units(self):
        products = [
            {'name': 'CPU', 'cat': 'CPU', 'attributes': [{'name': 'Socket', 'value': 'AM5'}]},
            {'name': 'Board', 'cat': 'Mainboard', 'attributes': [{'name': 'Socket', 'value': 'LGA1700'}]},
        ]
        rule = {'name': 'Socket', 'active': True, 'source_category': 'CPU',
                'target_category': 'Mainboard', 'source_attribute': 'Socket',
                'target_attribute': 'Socket', 'operator': 'equal'}
        self.assertEqual(check_compatibility(products, [rule])[0]['status'], 'fail')
        products[1]['attributes'][0]['value'] = 'am5'
        self.assertEqual(check_compatibility(products, [rule])[0]['status'], 'pass')
        products[1]['attributes'] = []
        self.assertEqual(check_compatibility(products, [rule])[0]['status'], 'unknown')
        self.assertEqual(check_compatibility(products[:1], [rule]), [])
        products[0]['attributes'] = [{'name': 'Socket', 'value': '10', 'unit': 'W'}]
        products[1]['attributes'] = [{'name': 'Socket', 'value': '5', 'unit': 'mm'}]
        rule['operator'] = 'gte'
        self.assertEqual(check_compatibility(products, [rule])[0]['status'], 'unknown')
        products[1]['attributes'][0]['unit'] = 'W'
        self.assertEqual(check_compatibility(products, [rule])[0]['status'], 'pass')
        rule['operator'] = 'lte'
        self.assertEqual(check_compatibility(products, [rule])[0]['status'], 'fail')
        rule['operator'] = 'overlap'
        products[0]['attributes'][0]['value'] = 'ATX, Mini-ITX'
        products[1]['attributes'][0]['value'] = 'atx'
        self.assertEqual(check_compatibility(products, [rule])[0]['status'], 'pass')

    @patch('core.chat_service.generate', return_value={'product_ids': ['invented']})
    def test_rejects_invented_products(self, mocked):
        with self.assertRaises(ChatUnavailable):
            advise('test', [], [], [], [])
        self.assertEqual(mocked.call_count, 1)

    @override_settings(GEMINI_API_KEY='')
    def test_missing_key(self):
        with self.assertRaises(ChatUnavailable):
            generate('test', {})

    @override_settings(GEMINI_API_KEY='test')
    @patch('core.chat_service.urlopen')
    def test_quota_error_is_safe(self, mocked):
        mocked.side_effect = HTTPError('url', 429, 'secret provider details', {}, None)
        with self.assertRaisesMessage(ChatUnavailable, 'hạn mức'):
            generate('test', {})


class ChatTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='chat-user', password='test-password')
        self.client.force_login(self.user)
        Product.objects.create(external_id='cpu', payload={'name': 'CPU', 'cat': 'CPU', 'price': 100})

    def post(self, data):
        return self.client.post('/api/chat/', data, content_type='application/json')

    def test_login_and_validation(self):
        self.assertEqual(Client().get('/api/chat/').status_code, 401)
        for data in ([], {}, {'message': ''}, {'message': 'x' * 2001}, {'message': 'test', 'product_ids': [1]}):
            self.assertEqual(self.post(data).status_code, 400)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/api/chat/', {'message': 'test'}, content_type='application/json').status_code, 403)
        token = client.get('/api/chat/').json()['csrf_token']
        self.assertEqual(client.delete('/api/chat/', HTTP_X_CSRFTOKEN=token).status_code, 200)

    @patch('core.chat_service.generate')
    def test_catalog_history_and_reset(self, mocked):
        Product.objects.create(external_id='hidden', payload={'name': 'Hidden', 'active': False})
        Product.objects.create(external_id='sold', payload={'name': 'Sold', 'stock': 0})
        mocked.side_effect = [{'product_ids': ['cpu']}, 'CPU giá 100 đồng.']
        result = self.post({'message': 'Tư vấn CPU'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['products'][0]['price'], 100)
        catalog = mocked.call_args_list[0].args[1]['catalog']
        self.assertEqual([p['id'] for p in catalog], ['cpu'])
        self.assertEqual(len(self.client.get('/api/chat/').json()['history']), 2)
        other = Client()
        other.force_login(User.objects.create_user(username='other'))
        self.assertEqual(other.get('/api/chat/').json()['history'], [])
        self.client.delete('/api/chat/')
        self.assertEqual(self.client.get('/api/chat/').json()['history'], [])

    @patch('core.chat_views.advise', side_effect=ChatUnavailable('Tạm thời không khả dụng.'))
    def test_failure_and_rate_limit(self, mocked):
        for _ in range(5):
            self.assertEqual(self.post({'message': 'test'}).status_code, 503)
        self.assertEqual(self.post({'message': 'test'}).status_code, 429)
        self.assertEqual(self.client.get('/api/chat/').json()['history'], [])

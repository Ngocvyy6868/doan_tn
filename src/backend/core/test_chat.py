import json
from unittest.mock import patch
from urllib.error import HTTPError

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase, override_settings

from .chat_service import ChatUnavailable, check_compatibility, generate
from .models import ChatMessage, ChatSession, Product


class TransportTests(SimpleTestCase):
    @override_settings(OLLAMA_BASE_URL='')
    def test_missing_endpoint(self):
        with self.assertRaises(ChatUnavailable):
            generate('test', {})

    @override_settings(OLLAMA_BASE_URL='http://localhost:11434/', OLLAMA_MODEL='test-model')
    @patch('core.advisor.llm.urlopen')
    def test_openai_request_and_content(self, mocked):
        response = mocked.return_value.__enter__.return_value
        response.read.return_value = json.dumps({'choices': [
            {'finish_reason': 'stop', 'message': {'content': '{"product_ids":["cpu"]}'}}]}).encode()
        self.assertEqual(generate('Select', {}, True), {'product_ids': ['cpu']})
        request = mocked.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, 'http://localhost:11434/v1/chat/completions')
        self.assertEqual(body['model'], 'test-model')
        self.assertEqual(body['response_format']['type'], 'json_schema')
        self.assertIn('/no_think', body['messages'][0]['content'])
        self.assertFalse(body['stream'])
        self.assertEqual(body['reasoning_effort'], 'none')
        response.read.return_value = json.dumps({'choices': [
            {'finish_reason': 'stop', 'message': {'content': '<think>\n\n</think>\nTư vấn CPU'}}]}).encode()
        self.assertEqual(generate('test', {}), 'Tư vấn CPU')

    @patch('core.advisor.llm.urlopen')
    def test_incomplete_empty_and_invalid_json(self, mocked):
        response = mocked.return_value.__enter__.return_value
        for reason, content in [('length', 'partial'), ('stop', ''), ('stop', 'not JSON'),
                                ('stop', '<think>private</think>answer')]:
            response.read.return_value = json.dumps({'choices': [
                {'finish_reason': reason, 'message': {'content': content}}]}).encode()
            with self.assertRaises(ChatUnavailable):
                generate('test', {}, True)

    @patch('core.advisor.llm.urlopen')
    def test_provider_details_are_hidden(self, mocked):
        mocked.side_effect = HTTPError('url', 429, 'secret provider details', {}, None)
        with self.assertRaisesMessage(ChatUnavailable, 'quá tải'):
            generate('test', {})


class RuleTests(SimpleTestCase):
    def test_existing_admin_rules(self):
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


class ChatTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='chat-user', password='test-password')
        self.client.force_login(self.user)
        Product.objects.create(external_id='cpu', payload={
            'name': 'CPU', 'cat': 'CPU', 'price': 100, 'stock': 1, 'cost': 50})

    def post(self, data):
        return self.client.post('/api/chat/', data, content_type='application/json')

    def test_login_validation_and_csrf(self):
        self.assertEqual(Client().get('/api/chat/').status_code, 401)
        for data in ([], {}, {'message': ''}, {'message': 'x' * 2001},
                     {'message': 'test', 'product_ids': [1]},
                     {'message': 'Đổi', 'swap': 'yes', 'product_ids': ['cpu']},
                     {'message': 'Đổi', 'swap': True, 'product_ids': []},
                     {'message': 'Đổi', 'swap': True, 'product_ids': ['cpu', 'x']}):
            self.assertEqual(self.post(data).status_code, 400)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/api/chat/', {'message': 'test'},
                                     content_type='application/json').status_code, 403)
        token = client.get('/api/chat/').json()['csrf_token']
        self.assertEqual(client.delete('/api/chat/', HTTP_X_CSRFTOKEN=token).status_code, 200)

    @patch('core.chat_views.generate', return_value={'ngan_sach': 25000000})
    def test_clarification_and_durable_state(self, mocked):
        response = self.post({'message': 'Build PC 25tr'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['stage'], 'clarification')
        self.assertEqual(len(response.json()['questions']), 1)
        self.assertIn('Anh/chị dùng máy chủ yếu', response.json()['questions'][0])
        self.assertEqual(ChatMessage.objects.count(), 2)
        session = ChatSession.objects.get()
        self.assertEqual(session.state['sheet']['ngan_sach'], 25000000)
        self.assertEqual(len(self.client.get('/api/chat/').json()['history']), 2)
        cache.clear()
        self.assertEqual(len(self.client.get('/api/chat/').json()['history']), 2)
        self.client.delete('/api/chat/')
        self.assertEqual(self.client.get('/api/chat/').json()['history'], [])
        self.assertEqual(ChatMessage.objects.count(), 2)
        second = ChatSession.objects.create(user=self.user, active=True)
        restored = self.client.post(f'/api/chat/sessions/{session.pk}/')
        self.assertEqual(len(restored.json()['history']), 2)
        second.refresh_from_db()
        self.assertFalse(second.active)

    @patch('core.chat_views.respond')
    def test_catalog_excludes_unknown_stock_and_inactive(self, mocked):
        for key, extra in [('hidden', {'active': False, 'stock': 2}), ('sold', {'stock': 0}),
                           ('unknown', {}), ('negative', {'stock': -1})]:
            Product.objects.create(external_id=key, payload={'name': key, 'price': 100, **extra})
        mocked.return_value = ({'answer': 'test', 'products': [], 'checks': [], 'latency_ms': 1}, {})
        self.assertEqual(self.post({'message': 'test'}).status_code, 200)
        self.assertEqual([p['id'] for p in mocked.call_args.args[2]], ['cpu'])
        self.assertNotIn('cost', mocked.call_args.args[2][0])

    @patch('core.chat_views.respond', side_effect=ChatUnavailable('Tạm thời không khả dụng.'))
    def test_failure_does_not_advance_state_and_rate_limit(self, mocked):
        for _ in range(5):
            self.assertEqual(self.post({'message': 'test'}).status_code, 503)
        self.assertEqual(self.post({'message': 'test'}).status_code, 429)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_history_owner_is_enforced(self):
        other = User.objects.create_user(username='other')
        session = ChatSession.objects.create(user=other)
        self.assertEqual(self.client.get(f'/api/chat/sessions/{session.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/chat/sessions/{session.pk}/').status_code, 404)
        self.assertEqual(self.client.get('/api/chat/sessions/').json()['results'], [])

    def test_concurrent_request_rejected(self):
        cache.add(f'advisor-lock:{self.user.pk}', True)
        self.assertEqual(self.post({'message': 'test'}).status_code, 409)

    def test_cart_validation_checks_current_stock(self):
        response = self.client.post('/api/advisor/validate/', {
            'items': [{'id': 'cpu', 'quantity': 2}]}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['can_add_to_cart'])
        self.assertTrue(response.json()['errors'])
        self.assertEqual(self.client.post('/api/advisor/validate/', {
            'items': [{'id': 'cpu', 'quantity': True}]}, content_type='application/json').status_code, 400)

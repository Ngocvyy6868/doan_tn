"""Run with config.settings against the Compose PostgreSQL service."""
from unittest import skipUnless
from unittest.mock import patch
from django.conf import settings
from django.db import connection
from django.test import TestCase, override_settings
from .advisor.catalog import adapt, fingerprint
from .advisor.retrieval import hybrid_search, query_vectors
from .chat_service import ChatUnavailable
from .models import Product


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL + pgvector')
@override_settings(ADVISOR_RERANK=False)
class PostgresRetrievalTests(TestCase):
    def setUp(self):
        query_vectors.cache_clear()
        self.vector = [1.0] + [0.0] * 1023
        self.product = Product.objects.create(external_id='cpu', payload={
            'name': 'Bộ xử lý học tập', 'cat': 'CPU', 'price': 1000000, 'stock': 2,
            'brand': 'amd', 'specs': {'socket': 'AM5'}})
        self.product.embedding = self.vector
        self.product.embedding_hash = fingerprint(adapt(self.product), settings.ADVISOR_EMBEDDING_MODEL)
        self.product.save()

    def tearDown(self):
        query_vectors.cache_clear()

    @patch('core.advisor.retrieval.embed')
    def test_vector_and_accent_insensitive_full_text(self, embed):
        embed.return_value = [self.vector]
        ids, trace = hybrid_search('hoc tap', '', [adapt(self.product)])
        self.assertEqual(ids, ['cpu'])
        self.assertEqual(trace['mode'], 'hybrid')
        with connection.cursor() as cursor:
            cursor.execute("SELECT search_tsv @@ plainto_tsquery('simple', public.advisor_unaccent(%s)) FROM core_product WHERE id=%s",
                           ['hoc tap', self.product.pk])
            self.assertTrue(cursor.fetchone()[0])

    @patch('core.advisor.retrieval.embed')
    def test_sql_rechecks_stock_after_catalog_read(self, embed):
        embed.return_value = [self.vector]
        snapshot = adapt(self.product)
        self.product.payload['stock'] = 0
        self.product.save()
        ids, trace = hybrid_search('hoc tap', '', [snapshot])
        self.assertEqual(ids, [])

    @patch('core.advisor.retrieval.embed')
    def test_changed_description_excludes_stale_vector(self, embed):
        embed.return_value = [self.vector]
        self.product.payload['description'] = 'Nội dung đã đổi.'
        self.product.save()
        with self.assertRaises(ChatUnavailable):
            hybrid_search('hoc tap', '', [adapt(self.product)])

    def test_vector_roundtrip(self):
        self.product.refresh_from_db()
        self.assertEqual(self.product.embedding, self.vector)

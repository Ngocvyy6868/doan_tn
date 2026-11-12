"""CPU embeddings/reranking; PostgreSQL hybrid search with reciprocal rank fusion."""
from functools import lru_cache
import json
import math

from django.conf import settings
from django.db import connection

from .catalog import fingerprint, search_text


@lru_cache(maxsize=2)
def embedding_model(name=None):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name or settings.ADVISOR_EMBEDDING_MODEL, device='cpu',
                               local_files_only=settings.ADVISOR_MODELS_OFFLINE)


@lru_cache(maxsize=1)
def reranker_model():
    from sentence_transformers import CrossEncoder
    # 512 token đủ cho tên + thông số + mô tả; giới hạn để mỗi cặp không tốn thời gian như ngữ cảnh 8192.
    return CrossEncoder(settings.ADVISOR_RERANKER_MODEL, device='cpu', max_length=512,
                        local_files_only=settings.ADVISOR_MODELS_OFFLINE)


def embed(texts):
    model = settings.ADVISOR_EMBEDDING_MODEL
    vectors = embedding_model(model).encode(texts, normalize_embeddings=True).tolist()
    # Only the pgvector column is fixed at 1024 dimensions; the in-memory store (TN3 baselines
    # such as MiniLM-L12-v2 with 384 dimensions) accepts any size.
    if settings.ADVISOR_VECTOR_STORE == 'pgvector' and any(len(v) != 1024 for v in vectors):
        raise ValueError('Production BGE-M3 index requires 1024-dimensional vectors.')
    return vectors


@lru_cache(maxsize=16)
def _query_vectors(query, hypothetical, model, store):
    return embed([query, hypothetical] if hypothetical else [query])


def query_vectors(query, hypothetical):
    return _query_vectors(query, hypothetical, settings.ADVISOR_EMBEDDING_MODEL,
                          settings.ADVISOR_VECTOR_STORE)


query_vectors.cache_clear = _query_vectors.cache_clear


def _normalise(vector):
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else vector


def combined_vector(query, hypothetical):
    """ADVISOR_HYDE_MODE: 'combined' averages question and HyDE text, 'only' uses HyDE text alone."""
    vectors = query_vectors(query, hypothetical)
    if len(vectors) == 1:
        return vectors[0]
    if settings.ADVISOR_HYDE_MODE == 'only':
        return vectors[1]
    return _normalise([(a + b) / 2 for a, b in zip(*vectors)])


_memory_index = {}


def memory_semantic(vector, catalog, limit=50):
    """Exact cosine search over the given (already stock/price filtered) candidates.

    Used for embedding comparisons (TN3) without changing the 1024-dimension pgvector column.
    Vectors are cached by fingerprint, so changed text or model is re-embedded.
    """
    model = settings.ADVISOR_EMBEDDING_MODEL
    missing = [p for p in catalog if fingerprint(p, model) not in _memory_index]
    if missing:
        for p, v in zip(missing, embed([search_text(p) for p in missing])):
            _memory_index[fingerprint(p, model)] = v
    scored = [(sum(a * b for a, b in zip(vector, _memory_index[fingerprint(p, model)])), p['id'])
              for p in catalog]
    return [key for _, key in sorted(scored, key=lambda x: (-x[0], x[1]))[:limit]]


def hybrid_search(query, hypothetical, catalog):
    """SQL filters current stock/price before ranking. SQLite is a lexical test baseline."""
    from ..models import Product
    by_id = {p['id']: p for p in catalog}
    if not by_id:
        return [], {'mode': 'empty'}
    if connection.vendor != 'postgresql':
        if settings.ADVISOR_RETRIEVAL != 'lexical':
            from ..chat_service import ChatUnavailable
            raise ChatUnavailable('Truy xuất vector cần PostgreSQL + pgvector.')
        from .catalog import fold
        terms = set(fold(query).split())
        ranked = sorted(catalog, key=lambda p: (-len(terms & set(fold(search_text(p)).split())), p['id']))
        return [p['id'] for p in ranked[:40]], {'mode': 'lexical-test'}
    vector = combined_vector(query, hypothetical)
    ceiling = max(p['price'] for p in catalog)
    if settings.ADVISOR_VECTOR_STORE == 'memory':
        current = list(by_id)
        semantic = memory_semantic(vector, catalog)
    else:
        # Fingerprints prevent use of stale embeddings after text/category/model changes.
        current = [ext_id for ext_id, emb_hash in Product.objects.filter(
                   external_id__in=by_id, embedding__isnull=False).values_list('external_id', 'embedding_hash')
                   if emb_hash == fingerprint(by_id[ext_id], settings.ADVISOR_EMBEDDING_MODEL)]
        if not current:
            from ..chat_service import ChatUnavailable
            raise ChatUnavailable('Chưa có chỉ mục sản phẩm. Hãy chạy index_advisor_catalog.')
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT external_id FROM core_product
                WHERE external_id = ANY(%s) AND embedding IS NOT NULL
                  AND advisor_stock >= 1 AND advisor_price > 0 AND advisor_price <= %s
                  AND payload->>'active' IS DISTINCT FROM 'false'
                ORDER BY embedding <=> %s::vector LIMIT 50
            """, [list(current), ceiling, json.dumps(vector)])
            semantic = [row[0] for row in cursor.fetchall()]
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT external_id FROM core_product
            WHERE external_id = ANY(%s)
              AND advisor_stock >= 1 AND advisor_price > 0 AND advisor_price <= %s
              AND payload->>'active' IS DISTINCT FROM 'false'
              AND search_tsv @@ plainto_tsquery('simple', public.advisor_unaccent(%s))
            ORDER BY ts_rank(search_tsv, plainto_tsquery('simple', public.advisor_unaccent(%s))) DESC
            LIMIT 50
        """, [list(by_id), ceiling, query, query])
        lexical = [row[0] for row in cursor.fetchall()]
    scores = {}
    for ranking in (semantic, lexical):
        for i, key in enumerate(ranking):
            scores[key] = scores.get(key, 0) + 1 / (60 + i + 1)
    ranked = sorted(scores, key=lambda key: (-scores[key], key))[:40]
    # Một ứng viên thì không có gì để xếp hạng lại; bỏ qua để khỏi tốn ~0,6 s CPU mỗi nhóm linh kiện.
    if settings.ADVISOR_RERANK and len(ranked) > 1:
        predictions = reranker_model().predict([(query, search_text(by_id[key])) for key in ranked])
        ranked = [key for _, key in sorted(zip(map(float, predictions), ranked), reverse=True)]
    return ranked, {'mode': 'hybrid', 'hyde': bool(hypothetical),
                    'hyde_mode': settings.ADVISOR_HYDE_MODE if hypothetical else None,
                    'embedding_model': settings.ADVISOR_EMBEDDING_MODEL,
                    'vector_store': settings.ADVISOR_VECTOR_STORE,
                    'reranker': settings.ADVISOR_RERANK, 'retrieved_ids': ranked,
                    'indexed_products': len(current)}

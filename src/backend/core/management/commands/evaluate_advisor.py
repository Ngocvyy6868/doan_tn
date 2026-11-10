"""Run labelled conversations without storing them as customer chat sessions.

Experiments (đề cương 3.4.4):
  TN1  --model qwen3:8b
  TN2  --no-hyde | --hyde-mode only | (mặc định: combined), mỗi biến thể có/không --no-reranker
  TN3  --embedding-model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
       (và --embedding-model BAAI/bge-m3 để so cùng kho vector trong bộ nhớ)
  TN4  --selector llm
"""
import json
import statistics
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings
from core.advisor.catalog import adapt, available
from core.advisor.pipeline import respond
from core.advisor.rules import check_build
from core.chat_service import generate
from core.models import Product

BUDGET_TOLERANCE = 0.05


def budget_metrics(result, sheet):
    """Đề cương 3.4.3: tổng tiền trong khoảng ±5% ngân sách khả dụng (ngân sách trừ dự phòng màn hình/phím chuột)."""
    if result.get('stage') != 'recommendation' or not sheet.get('ngan_sach'):
        return None, None
    usable = sheet['ngan_sach'] - result.get('peripheral_reserve', 0)
    total = result.get('total', 0)
    return abs(total - usable) <= BUDGET_TOLERANCE * usable, total <= usable


def context_text(p):
    """Văn bản sản phẩm cho RAGAS: nội dung truy xuất + giá, tồn kho (dữ liệu mà câu trả lời được phép dùng)."""
    return json.dumps({k: p.get(k) for k in ('name', 'brand', 'cat', 'price', 'stock', 'specs', 'description')},
                      ensure_ascii=False, sort_keys=True)


def rate(rows, key):
    values = [row[key] for row in rows if row[key] is not None]
    return sum(map(bool, values)) / len(values) if values else None


class Command(BaseCommand):
    help = 'Evaluate labelled JSONL conversations and export retrieval/answer traces for RAGAS.'

    def add_arguments(self, parser):
        parser.add_argument('dataset')
        parser.add_argument('--output', required=True)
        parser.add_argument('--model', default=settings.OLLAMA_MODEL)
        parser.add_argument('--no-hyde', action='store_true')
        parser.add_argument('--hyde-mode', choices=('combined', 'only'), default=settings.ADVISOR_HYDE_MODE)
        parser.add_argument('--no-reranker', action='store_true')
        parser.add_argument('--embedding-model', help='Đổi model embedding; dùng kho vector trong bộ nhớ (TN3).')
        parser.add_argument('--selector', choices=('rules', 'llm'), default='rules')
        parser.add_argument('--limit', type=int, help='Chỉ chạy N mẫu đầu (chạy thử).')

    def handle(self, *args, **options):
        try:
            cases = [json.loads(line) for line in Path(options['dataset']).read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        except (ValueError, OSError) as exc:
            raise CommandError('Không đọc được dataset JSONL.') from exc
        if not cases or any(not isinstance(c.get('messages'), list) or not c['messages'] or
                            any(not isinstance(m, str) for m in c['messages']) for c in cases):
            raise CommandError('Mỗi mẫu cần messages là danh sách tin nhắn không rỗng.')
        if options['limit']:
            cases = cases[:options['limit']]
        catalog = [adapt(p) for p in Product.objects.select_related('category').defer('embedding')]
        catalog = [p for p in catalog if available(p)]
        by_id = {p['id']: p for p in catalog}
        overrides = dict(OLLAMA_MODEL=options['model'], ADVISOR_HYDE=not options['no_hyde'],
                         ADVISOR_HYDE_MODE=options['hyde_mode'], ADVISOR_RERANK=not options['no_reranker'])
        if options['embedding_model']:
            overrides.update(ADVISOR_EMBEDDING_MODEL=options['embedding_model'], ADVISOR_VECTOR_STORE='memory')
        config = {'model': options['model'], 'selector': options['selector'],
                  'hyde': 'none' if options['no_hyde'] else options['hyde_mode'],
                  'reranker': not options['no_reranker'],
                  'embedding_model': overrides.get('ADVISOR_EMBEDDING_MODEL', settings.ADVISOR_EMBEDDING_MODEL)}
        rows, latencies = [], []
        with override_settings(**overrides):
            for index, case in enumerate(cases):
                state, history, result = {}, [], {}
                for message in case['messages']:
                    result, state = respond(message, history, catalog, [], state, generate,
                                            selector=options['selector'])
                    history.extend([{'role': 'user', 'text': message}, {'role': 'assistant', 'text': result['answer']}])
                    latencies.append(result['latency_ms'])
                products = result['products']
                groups = result.get('retrieval', {}).get('groups', [])
                retrieved = list(dict.fromkeys(key for group in groups for key in group.get('retrieved_ids', [])))
                # Ngữ cảnh RAGAS = top-K mỗi nhóm, đúng tập mà thuật toán chọn linh kiện ưu tiên.
                top_k = settings.ADVISOR_ASSEMBLY_TOP_K
                context_ids = list(dict.fromkeys(key for group in groups
                                                 for key in group.get('retrieved_ids', [])[:top_k]))
                expected = case.get('requirements', {})
                relevant = set(case.get('relevant_product_ids', []))
                hits = [i for i, key in enumerate(retrieved) if key in relevant]
                precision = sum(sum(key in relevant for key in retrieved[:i+1]) / (i+1) for i in hits) / max(1, len(hits))
                # Independent re-check of the final configuration (tỉ lệ lỗi tương thích).
                checks = check_build(products) if result['stage'] == 'recommendation' else []
                within, not_exceeded = budget_metrics(result, state['sheet'])
                rows.append({
                    'id': case.get('id', index), 'group': case.get('group'), **config,
                    'user_input': '\n'.join(case['messages']), 'response': result['answer'],
                    'stage': result['stage'],
                    'retrieved_contexts': [context_text(by_id[key]) for key in context_ids if key in by_id],
                    'reference': case.get('reference', ''), 'result': result,
                    'field_exact_match': {k: state['sheet'].get(k) == v for k, v in expected.items()},
                    'expected_requirements': expected, 'predicted_requirements': state['sheet'],
                    'retrieval_average_precision': precision if relevant else None,
                    'retrieval_id_recall': len(set(retrieved) & relevant) / len(relevant) if relevant else None,
                    'has_compatibility_error': any(c['status'] == 'fail' and c['severity'] == 'error' for c in checks)
                                               if checks else None,
                    'unknown_checks': sum(c['status'] == 'unknown' for c in checks),
                    'stock_compliant': all(available(p) for p in products) if products else None,
                    'budget_within_5pct': within, 'budget_not_exceeded': not_exceeded,
                    'clarification_correct': (result['stage'] == 'clarification') == case['expect_clarification']
                                            if 'expect_clarification' in case else None,
                    'invalid_llm_ids': result.get('invalid_ids'),
                })
        output = Path(options['output'])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\n', encoding='utf-8')
        latency = sorted(latencies)
        f1 = {}
        for field in {key for row in rows for key in row['expected_requirements']}:
            tp = fp = fn = 0
            for row in rows:
                if field not in row['expected_requirements']:
                    continue
                gold = row['expected_requirements'][field]
                prediction = row['predicted_requirements'].get(field)
                tp += int(gold is not None and prediction == gold)
                fp += int(prediction is not None and prediction != gold)
                fn += int(gold is not None and prediction != gold)
            f1[field] = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
        precisions = [r['retrieval_average_precision'] for r in rows if r['retrieval_average_precision'] is not None]
        recalls = [r['retrieval_id_recall'] for r in rows if r['retrieval_id_recall'] is not None]
        summary = {**config, 'cases': len(rows), 'field_f1': f1,
                   'compatibility_error_rate': rate(rows, 'has_compatibility_error'),
                   'budget_within_5pct_rate': rate(rows, 'budget_within_5pct'),
                   'budget_not_exceeded_rate': rate(rows, 'budget_not_exceeded'),
                   'stock_compliance_rate': rate(rows, 'stock_compliant'),
                   'clarification_accuracy': rate(rows, 'clarification_correct'),
                   'retrieval_map': statistics.mean(precisions) if precisions else None,
                   'retrieval_id_recall': statistics.mean(recalls) if recalls else None,
                   'mean_latency_ms': statistics.mean(latency),
                   'p95_latency_ms': latency[min(len(latency)-1, int(0.95 * len(latency)))]}
        output.with_suffix('.summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n',
                                                       encoding='utf-8')
        self.stdout.write(json.dumps(summary, ensure_ascii=False))

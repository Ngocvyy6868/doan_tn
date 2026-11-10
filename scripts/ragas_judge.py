"""Chấm RAGAS cho file trace của evaluate_advisor (đề cương 3.4.1, 3.4.2).

Bốn chỉ số, chạy thành hai lượt vì hai nhóm chỉ số dùng ngữ cảnh khác nhau:
  - Truy xuất: Context Precision (có tham chiếu), Context Recall
      ngữ cảnh = top-K sản phẩm truy xuất mỗi nhóm (cột retrieved_contexts của trace).
  - Sinh văn bản: Faithfulness, Answer Relevancy
      ngữ cảnh = dữ liệu mà Qwen3-4B thực sự nhận khi viết câu trả lời (sản phẩm đã chọn, tổng tiền,
      kết quả kiểm tra), dựng lại từ trường result của trace.
Mẫu không có ngữ cảnh/tham chiếu (ví dụ nhóm câu mơ hồ dừng ở bước hỏi lại) bị bỏ qua ở lượt tương ứng.

Giám khảo phải là mô hình lớn hơn mô hình được đánh giá (Qwen3-14B hoặc Qwen3-30B-A3B), gọi qua endpoint
tương thích OpenAI:
  - llama.cpp:  llama-server -m Qwen3-30B-A3B-Q4_K_M.gguf -c 16384 --n-cpu-moe 48 --jinja \
                    --reasoning-format deepseek --port 8081      → --base-url http://localhost:8081/v1
  - Ollama:     ollama pull qwen3:14b                               → --base-url http://localhost:11434/v1
Embedding cho Answer Relevancy: BGE-M3 trên CPU (cùng mô hình với hệ thống).

Môi trường riêng, không cài vào backend:
  python -m venv .venv-eval && .venv-eval/Scripts/pip install -r scripts/requirements-ragas.txt
Chạy:
  python scripts/ragas_judge.py results/tn2_combined.jsonl --model qwen3:14b \
      --base-url http://localhost:11434/v1 --output results/tn2_combined.ragas.jsonl
  python scripts/ragas_judge.py results/tn2_combined.jsonl --dry-run      # chỉ kiểm tra dữ liệu
"""
import argparse
import asyncio
import json
import math
import statistics
import sys
from pathlib import Path

RETRIEVAL_METRICS = ('llm_context_precision_with_reference', 'context_recall')
GENERATION_METRICS = ('faithfulness', 'answer_relevancy')
PRODUCT_KEYS = ('name', 'cat', 'price', 'stock', 'specs')
SUMMARY_KEYS = ('requirements', 'assumptions', 'total', 'budget', 'component_budget', 'peripheral_reserve',
                'errors', 'can_add_to_cart')


def generation_contexts(result):
    """Dữ liệu đưa cho LLM sinh câu trả lời (pipeline.respond), mỗi mục một ngữ cảnh."""
    contexts = [json.dumps({k: p.get(k) for k in PRODUCT_KEYS}, ensure_ascii=False, sort_keys=True)
                for p in result.get('products', [])]
    summary = {k: result[k] for k in SUMMARY_KEYS if k in result}
    checks = [f"{c.get('code', '')} {c.get('rule', '')}: {c.get('status')} — {c.get('message', '')}"
              for c in result.get('checks', [])]
    if checks:
        summary['checks'] = checks
    if summary:
        contexts.append(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return contexts


def build_samples(rows):
    retrieval, generation = [], []
    for row in rows:
        if row.get('retrieved_contexts') and row.get('reference'):
            retrieval.append({'id': row['id'], 'user_input': row['user_input'],
                              'retrieved_contexts': row['retrieved_contexts'], 'reference': row['reference']})
        result = row.get('result', {})
        if row.get('stage', result.get('stage')) in ('recommendation', 'lookup') and row.get('response'):
            contexts = generation_contexts(result)
            if contexts:
                generation.append({'id': row['id'], 'user_input': row['user_input'],
                                   'response': row['response'], 'retrieved_contexts': contexts})
    return retrieval, generation


def mean(values):
    values = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    return statistics.mean(values) if values else None


class SentenceTransformerEmbeddings:
    """Bọc sentence-transformers thành embeddings của RAGAS (BaseRagasEmbeddings)."""

    def __new__(cls, name):
        from ragas.embeddings import BaseRagasEmbeddings
        from sentence_transformers import SentenceTransformer

        class _Embeddings(BaseRagasEmbeddings):
            def __init__(self):
                super().__init__()
                self.model = SentenceTransformer(name, device='cpu')

            def embed_documents(self, texts):
                return self.model.encode(list(texts), normalize_embeddings=True).tolist()

            def embed_query(self, text):
                return self.embed_documents([text])[0]

            async def aembed_documents(self, texts):
                return await asyncio.to_thread(self.embed_documents, texts)

            async def aembed_query(self, text):
                return (await self.aembed_documents([text]))[0]

        return _Embeddings()


def run(samples, metrics, llm, embeddings, run_config):
    from ragas import EvaluationDataset, evaluate
    if not samples:
        return []
    data = EvaluationDataset.from_list([{k: v for k, v in s.items() if k != 'id'} for s in samples])
    result = evaluate(data, metrics=metrics, llm=llm, embeddings=embeddings, run_config=run_config,
                      raise_exceptions=False, show_progress=True)
    return [{'id': s['id'], **scores} for s, scores in zip(samples, result.scores)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('trace', help='File JSONL do evaluate_advisor xuất ra.')
    parser.add_argument('--output', help='Mặc định: <trace>.ragas.jsonl (+ .ragas.summary.json).')
    parser.add_argument('--base-url', default='http://localhost:11434/v1')
    parser.add_argument('--model', default='qwen3:14b', help='Mô hình giám khảo, KHÔNG dùng Qwen3-4B.')
    parser.add_argument('--api-key', default='local')
    parser.add_argument('--embedding-model', default='BAAI/bge-m3')
    parser.add_argument('--timeout', type=int, default=600, help='Giây cho mỗi lần gọi giám khảo.')
    parser.add_argument('--workers', type=int, default=2, help='Số lời gọi song song tới giám khảo.')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--dry-run', action='store_true', help='Chỉ dựng dữ liệu và in số mẫu, không gọi giám khảo.')
    args = parser.parse_args()

    trace = Path(args.trace)
    rows = [json.loads(line) for line in trace.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    if any(row.get('model') == args.model for row in rows):
        sys.exit('Mô hình giám khảo trùng mô hình được đánh giá; đề cương yêu cầu dùng mô hình lớn hơn.')
    retrieval, generation = build_samples(rows)
    print(f'{len(rows)} mẫu: {len(retrieval)} chấm truy xuất, {len(generation)} chấm sinh văn bản.')
    if args.dry_run:
        print(json.dumps({'retrieval_example': retrieval[:1], 'generation_example': generation[:1]},
                         ensure_ascii=False, indent=2)[:4000])
        return

    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall, ResponseRelevancy
    from ragas.run_config import RunConfig
    import ragas.llms.base as ragas_llm_base
    # Ollama/llama.cpp không bảo đảm hỗ trợ tham số n>1 của OpenAI; buộc ragas gửi N lời gọi riêng để
    # Answer Relevancy thực sự có N câu hỏi sinh ngược (đề cương 3.4.2).
    ragas_llm_base.is_multiple_completion_supported = lambda _llm: False

    llm =LangchainLLMWrapper(ChatOpenAI(model=args.model, base_url=args.base_url, api_key=args.api_key,
                                         temperature=0, timeout=args.timeout, max_retries=2))
    embeddings = SentenceTransformerEmbeddings(args.embedding_model)
    config = RunConfig(timeout=args.timeout, max_workers=args.workers, max_retries=3)
    scores = {}
    for samples, metrics in ((retrieval, [LLMContextPrecisionWithReference(), LLMContextRecall()]),
                             (generation, [Faithfulness(), ResponseRelevancy(strictness=3)])):
        for item in run(samples, metrics, llm, embeddings, config):
            scores.setdefault(item['id'], {}).update({k: v for k, v in item.items() if k != 'id'})

    output = Path(args.output) if args.output else trace.with_suffix('.ragas.jsonl')
    output.parent.mkdir(parents=True, exist_ok=True)
    meta = {k: rows[0].get(k) for k in ('model', 'selector', 'hyde', 'reranker', 'embedding_model')} if rows else {}
    output.write_text(''.join(json.dumps({'id': row['id'], 'group': row.get('group'), **scores.get(row['id'], {})},
                                         ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    metrics = {name: mean(s.get(name) for s in scores.values()) for name in RETRIEVAL_METRICS + GENERATION_METRICS}
    by_group = {group: {name: mean(scores.get(r['id'], {}).get(name) for r in rows if r.get('group') == group)
                        for name in RETRIEVAL_METRICS + GENERATION_METRICS}
                for group in sorted({r.get('group') for r in rows if r.get('group')})}
    available = [v for v in metrics.values() if v is not None]
    summary = {**meta, 'judge_model': args.model, 'cases': len(rows),
               'retrieval_samples': len(retrieval), 'generation_samples': len(generation),
               # Mỗi mẫu lỗi/không parse được là NaN và không được tính vào trung bình; báo cáo kèm số này.
               'scored_samples': {name: sum(isinstance(s.get(name), (int, float)) and not math.isnan(s[name])
                                            for s in scores.values())
                                  for name in RETRIEVAL_METRICS + GENERATION_METRICS},
               'metrics': metrics, 'by_group': by_group,
               # Đề cương 3.4.4: điểm tổng hợp chỉ để xếp hạng nhanh, không thay bảng chỉ số chi tiết.
               'ragas_mean': statistics.mean(available) if len(available) == 4 else None}
    output.with_suffix('.summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n',
                                                   encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

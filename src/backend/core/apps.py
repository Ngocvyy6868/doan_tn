from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    label = 'core'  # Preserve database tables and existing migration history.

    def ready(self):
        warm_up_advisor_models()


def warm_up_advisor_models():
    """Nạp sẵn BGE-M3 và reranker trong luồng nền khi server khởi động, để lượt chat đầu không phải chờ.

    Chỉ chạy khi ADVISOR_WARMUP=true và không phải lệnh manage.py (migrate, test, shell...).
    """
    import logging
    import sys
    import threading
    from django.conf import settings
    if not settings.ADVISOR_WARMUP or sys.argv and sys.argv[0].endswith('manage.py'):
        return

    def load_llm():
        # Gửi yêu cầu rỗng tới API gốc của Ollama: chỉ nạp Qwen3 lên GPU, không sinh văn bản.
        import json
        from urllib.request import Request, urlopen
        if not settings.OLLAMA_BASE_URL:
            return
        body = json.dumps({'model': settings.OLLAMA_MODEL, 'keep_alive': -1}).encode()
        request = Request(settings.OLLAMA_BASE_URL.rstrip('/') + '/api/generate', data=body,
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=120) as response:
            response.read()

    def run():
        try:
            load_llm()
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).exception('Ollama warm-up failed')
        try:
            from .advisor.retrieval import embed, reranker_model
            embed(['khởi động'])
            if settings.ADVISOR_RERANK:
                reranker_model().predict([('khởi động', 'khởi động')])
            logging.getLogger(__name__).info('Advisor models warmed up.')
        except Exception:  # noqa: BLE001 - lỗi nạp model sẽ được báo lại ở lượt chat thật
            logging.getLogger(__name__).exception('Advisor warm-up failed')

    threading.Thread(target=run, name='advisor-warmup', daemon=True).start()

"""OpenAI-compatible local Ollama transport; no cloud credentials."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from django.conf import settings


def generate(instruction, context, structured=False, temperature=0.2, max_tokens=1024):
    from ..chat_service import ChatUnavailable
    if not settings.OLLAMA_BASE_URL:
        raise ChatUnavailable('Chatbot chưa được cấu hình địa chỉ Ollama.')
    body = {
        'model': settings.OLLAMA_MODEL,
        'messages': [{'role': 'system', 'content': instruction + '\n/no_think'},
                     {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}],
        'stream': False, 'reasoning_effort': 'none', 'temperature': temperature, 'max_tokens': max_tokens,
    }
    if structured:
        schema = structured if isinstance(structured, dict) else {
            'type': 'object', 'properties': {'product_ids': {
                'type': 'array', 'items': {'type': 'string'}, 'maxItems': 10}},
            'required': ['product_ids'], 'additionalProperties': False}
        body['response_format'] = {'type': 'json_schema', 'json_schema': {
            'name': 'advisor_response', 'strict': True, 'schema': schema}}
        body['messages'][0]['content'] += '\nTrả JSON theo schema: ' + json.dumps(schema)
    request = Request(settings.OLLAMA_BASE_URL.rstrip('/') + '/v1/chat/completions',
                      data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=settings.ADVISOR_LLM_TIMEOUT) as response:
            result = json.load(response)
        choice = result['choices'][0]
        if choice.get('finish_reason') != 'stop':
            raise ValueError('Incomplete response')
        text = choice['message']['content']
        if isinstance(text, str):
            text = re.sub(r'^<think>\s*</think>\s*', '', text.strip())
        if not isinstance(text, str) or not text or '<think>' in text:
            raise ValueError('Empty or thinking response')
        return json.loads(text) if structured else text
    except HTTPError as exc:
        raise ChatUnavailable('Qwen3 đang quá tải hoặc chưa nạp model. Vui lòng thử lại sau.') from exc
    except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise ChatUnavailable('Chưa nhận được phản hồi hợp lệ từ Qwen3 cục bộ.') from exc

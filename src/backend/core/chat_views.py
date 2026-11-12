import json
import logging
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods

from . import crm
from .advisor.catalog import adapt, available
from .advisor.pipeline import respond
from .chat_service import ChatUnavailable, generate
from .models import ChatMessage, ChatSession, Product

logger = logging.getLogger(__name__)


def current_session(request):
    session_id = request.session.get('advisor_session_id')
    return ChatSession.objects.filter(pk=session_id, user=request.user, active=True).first() if session_id else None


def serialize_message(message):
    return {**message.data, 'role': message.role, 'text': message.text}


@require_http_methods(['GET', 'POST', 'DELETE'])
def chat(request):
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Vui lòng đăng nhập để dùng chatbot.'}, status=401)
    session = current_session(request)
    if request.method == 'GET':
        history = list(session.messages.order_by('-id')[:12])[::-1] if session else []
        return JsonResponse({'csrf_token': get_token(request),
                             'history': [serialize_message(m) for m in history],
                             'requirements': session.state.get('sheet', {}) if session else {}})
    if request.method == 'DELETE':
        if session:
            session.active = False
            session.save(update_fields=['active', 'updated_at'])
            cache.delete(f'advisor-state:{session.pk}')
        request.session.pop('advisor_session_id', None)
        request.session.pop('chat_history', None)
        return JsonResponse({'ok': True})
    if len(request.body) > 12000:
        return JsonResponse({'message': 'Nội dung quá dài.'}, status=400)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        data = None
    if not isinstance(data, dict) or not isinstance(data.get('message'), str) or not 1 <= len(data['message'].strip()) <= 2000:
        return JsonResponse({'message': 'Câu hỏi cần từ 1 đến 2000 ký tự.'}, status=400)
    selected = data.get('product_ids', [])
    swap = data.get('swap', False)
    if not isinstance(swap, bool) or (swap and len(selected) != 1):
        return JsonResponse({'message': 'Yêu cầu đổi linh kiện không hợp lệ.'}, status=400)
    if not isinstance(selected, list) or len(selected) > 10 or any(not isinstance(i, str) or len(i) > 64 for i in selected) or len(set(selected)) != len(selected):
        return JsonResponse({'message': 'Danh sách sản phẩm không hợp lệ.'}, status=400)
    rate_key = f'chat-rate:{request.user.pk}'
    cache.add(rate_key, 0, timeout=60)
    if cache.incr(rate_key) > 5:
        return JsonResponse({'message': 'Bạn gửi quá nhanh. Vui lòng chờ một phút.'}, status=429)
    lock_key = f'advisor-lock:{request.user.pk}'
    if not cache.add(lock_key, True, timeout=180):
        return JsonResponse({'message': 'Đang xử lý yêu cầu trước. Vui lòng chờ.'}, status=409)
    try:
        catalog = [adapt(p) for p in Product.objects.select_related('category').defer('embedding').order_by('id')]
        catalog = [p for p in catalog if available(p)]
        if any(i not in {p['id'] for p in catalog} for i in selected):
            return JsonResponse({'message': 'Sản phẩm đã chọn không còn khả dụng.'}, status=400)
        if not session:
            ChatSession.objects.filter(user=request.user, active=True).update(active=False)
            session = ChatSession.objects.create(user=request.user)
            request.session['advisor_session_id'] = session.pk
            crm.record(crm.customer_of(request.user), crm.Type.CHAT_STARTED,
                       {'session_id': session.pk, 'message': data['message'].strip()[:300]}, source=crm.Source.CUSTOMER)
        history = [{'role': m.role, 'text': m.text} for m in
                   list(session.messages.order_by('-id')[:12])[::-1]]
        # Database is durable source; cache speeds state reads and recovers after Redis eviction.
        state = cache.get(f'advisor-state:{session.pk}') or session.state
        try:
            result, next_state = respond(data['message'].strip(), history, catalog, selected, state, generate, swap=swap)
        except ChatUnavailable as exc:
            return JsonResponse({'message': str(exc)}, status=503)
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            logger.exception('Local advisor dependency failed')
            return JsonResponse({'message': 'Truy xuất cục bộ chưa sẵn sàng. Kiểm tra model và chỉ mục sản phẩm.'}, status=503)
        with transaction.atomic():
            session.state = next_state
            session.save(update_fields=['state', 'updated_at'])
            ChatMessage.objects.create(session=session, role='user', text=data['message'].strip())
            ChatMessage.objects.create(session=session, role='assistant', text=result['answer'],
                                       data=result, latency_ms=result['latency_ms'])
        cache.set(f'advisor-state:{session.pk}', next_state, timeout=86400)
        return JsonResponse(result)
    finally:
        cache.delete(lock_key)

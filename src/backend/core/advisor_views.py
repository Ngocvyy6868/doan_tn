import json
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods
from .advisor.cart import validate_cart
from .chat_views import serialize_message
from .models import ChatSession


@require_http_methods(['POST'])
def validate_build(request):
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Vui lòng đăng nhập.'}, status=401)
    if len(request.body) > 12000:
        return JsonResponse({'message': 'Nội dung quá dài.'}, status=400)
    try:
        data = json.loads(request.body)
        result = validate_cart(data.get('items') if isinstance(data, dict) else None)
    except (ValueError, UnicodeDecodeError) as exc:
        return JsonResponse({'message': str(exc)}, status=400)
    return JsonResponse(result)


@require_http_methods(['GET', 'POST'])
def sessions(request, session_id=None):
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Vui lòng đăng nhập.'}, status=401)
    owned = ChatSession.objects.filter(user=request.user)
    if session_id is None:
        if request.method != 'GET':
            return JsonResponse({'message': 'Method not allowed.'}, status=405)
        return JsonResponse({'results': [
            {'id': s.pk, 'created_at': s.created_at.isoformat(),
             'requirements': s.state.get('sheet', {})}
            for s in owned.order_by('-updated_at')[:50]]})
    session = owned.filter(pk=session_id).first()
    if not session:
        return JsonResponse({'message': 'Không tìm thấy hội thoại.'}, status=404)
    if request.method == 'POST':
        owned.filter(active=True).exclude(pk=session.pk).update(active=False)
        session.active = True
        session.save(update_fields=['active', 'updated_at'])
        request.session['advisor_session_id'] = session.pk
    messages = list(session.messages.order_by('-id')[:100])[::-1]
    return JsonResponse({'history': [serialize_message(m) for m in messages],
                         'csrf_token': get_token(request), 'requirements': session.state.get('sheet', {})})

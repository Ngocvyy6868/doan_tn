"""Admin: Profile khách hàng (CDP) — thông tin tổng hợp, dòng sự kiện, ghi chú và công việc chăm sóc."""
import datetime
from collections import Counter

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max, Min, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from . import crm
from .models import Customer, CustomerEvent, CustomerNote, CustomerTask, Order, Product
from .views import _payload

# Hạng khách hàng theo tổng chi tiêu (đơn chưa hủy), từ cao xuống thấp.
TIERS = ((50_000_000, 'Kim cương'), (20_000_000, 'Vàng'), (5_000_000, 'Bạc'), (0, 'Thành viên'))
# Kết quả hiển thị khi công việc hoàn thành, theo loại.
DONE_LABELS = {'CONTACT': 'Đã liên hệ', 'COMPLAINT': 'Đã phản hồi phản ánh', 'CONSULT': 'Đã tư vấn',
               'CARE': 'Đã chăm sóc', 'OTHER': 'Đã xong'}
CHANNELS = {'phone': 'Điện thoại', 'email': 'Email', 'zalo': 'Zalo', 'sms': 'SMS', 'store': 'Tại cửa hàng'}
MAX_NOTE = 5000


def _staff_customer(request, customer_id):
    if not (request.user.is_authenticated and request.user.is_staff):
        return None, JsonResponse({'message': 'Administrator access required.'}, status=403)
    customer = Customer.objects.select_related('user').filter(pk=customer_id).first()
    if customer is None:
        return None, JsonResponse({'message': 'Customer not found.'}, status=404)
    return customer, None


def _user_name(user):
    if user is None:
        return None
    customer = getattr(user, 'customer', None)  # nhân viên không có Customer
    return (customer.full_name if customer else None) or user.get_full_name() or user.username


def tier_of(total):
    return next(name for threshold, name in TIERS if total >= threshold)


@csrf_exempt
def customer_profile(request, customer_id):
    customer, error = _staff_customer(request, customer_id)
    if error:
        return error
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    orders = customer.orders.all()
    valid = orders.exclude(status=Order.Status.CANCELLED)
    stats = valid.aggregate(total=Sum('grand_total'), count=Count('id'), first=Min('created_at'), last=Max('created_at'))
    total = int(stats['total'] or 0)
    ids = list(valid.values_list('items__product_external_id', 'items__quantity'))
    cats = dict(Product.objects.filter(external_id__in={i for i, _ in ids if i}).values_list('external_id', 'payload__cat'))
    interests = Counter()
    for product_id, quantity in ids:
        if product_id and cats.get(product_id):
            interests[cats[product_id]] += quantity or 0
    default = customer.addresses.filter(is_default=True).first()
    user = customer.user
    next_tier = next(((t, n) for t, n in reversed(TIERS) if t > total), None)
    return JsonResponse({'profile': {
        'id': customer.id, 'full_name': customer.full_name, 'email': user.email, 'phone': customer.phone,
        'avatar_url': customer.avatar_url, 'created_at': customer.created_at.isoformat(),
        'updated_at': customer.updated_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None, 'active': user.is_active,
        'default_address': crm.address_text(default) if default else '',
        'address_count': customer.addresses.count(),
        'stats': {
            'orders': stats['count'] or 0, 'cancelled': orders.filter(status=Order.Status.CANCELLED).count(),
            'total_spent': total, 'average_order': total // stats['count'] if stats['count'] else 0,
            'first_order_at': stats['first'].isoformat() if stats['first'] else None,
            'last_order_at': stats['last'].isoformat() if stats['last'] else None,
            'chat_sessions': user.advisor_sessions.count(),
            'open_tasks': customer.tasks.filter(status=CustomerTask.Status.TODO).count(),
            'notes': customer.notes.count(),
        },
        'tier': tier_of(total),
        'next_tier': {'name': next_tier[1], 'remaining': next_tier[0] - total} if next_tier else None,
        'interests': [{'category': c, 'quantity': q} for c, q in interests.most_common(5)],
    }})


def _serialize_event(event):
    return {'id': event.id, 'type': event.type, 'source': event.source, 'title': event.title, 'data': event.data,
            'actor': _user_name(event.actor), 'created_at': event.created_at.isoformat()}


@csrf_exempt
def customer_events(request, customer_id):
    customer, error = _staff_customer(request, customer_id)
    if error:
        return error
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    events = customer.events.select_related('actor', 'actor__customer')
    days = request.GET.get('days', '30')
    if days != 'all':
        try:
            days = max(1, min(int(days), 3650))
        except ValueError:
            return JsonResponse({'message': 'Khoảng thời gian không hợp lệ.'}, status=400)
        events = events.filter(created_at__gte=timezone.now() - datetime.timedelta(days=days))
    types = [t for t in request.GET.get('types', '').split(',') if t]
    if types:
        events = events.filter(type__in=types)
    source = request.GET.get('source')
    if source:
        events = events.filter(source=source)
    total = events.count()
    return JsonResponse({'results': [_serialize_event(e) for e in events[:300]], 'total': total,
                         'types': [{'value': v, 'label': l} for v, l in CustomerEvent.Type.choices]})


def _serialize_note(note):
    return {'id': note.id, 'content': note.content, 'pinned': note.pinned, 'author': _user_name(note.author),
            'author_id': note.author_id, 'created_at': note.created_at.isoformat(),
            'updated_at': note.updated_at.isoformat()}


@csrf_exempt
def customer_notes(request, customer_id, note_id=None):
    customer, error = _staff_customer(request, customer_id)
    if error:
        return error
    if note_id is None:
        if request.method == 'GET':
            notes = customer.notes.select_related('author', 'author__customer')
            return JsonResponse({'results': [_serialize_note(n) for n in notes]})
        if request.method != 'POST':
            return JsonResponse({'message': 'Method not allowed.'}, status=405)
    note = None
    if note_id is not None:
        note = customer.notes.filter(pk=note_id).first()
        if note is None:
            return JsonResponse({'message': 'Không tìm thấy ghi chú.'}, status=404)
        if request.method == 'DELETE':
            note.delete()
            return JsonResponse({'deleted': True})
        if request.method != 'PATCH':
            return JsonResponse({'message': 'Method not allowed.'}, status=405)
    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Dữ liệu không hợp lệ.'}, status=400)
    content = str(data.get('content', note.content if note else '')).strip()
    if not content or len(content) > MAX_NOTE:
        return JsonResponse({'message': f'Ghi chú cần từ 1 đến {MAX_NOTE} ký tự.'}, status=400)
    pinned = data.get('pinned', note.pinned if note else False)
    if not isinstance(pinned, bool):
        return JsonResponse({'message': 'Giá trị ghim không hợp lệ.'}, status=400)
    with transaction.atomic():
        if note is None:
            note = CustomerNote.objects.create(customer=customer, author=request.user, content=content, pinned=pinned)
            crm.record(customer, crm.Type.NOTE_ADDED, {'note_id': note.id, 'content': content[:300]},
                       actor=request.user, source=crm.Source.STAFF)
            status = 201
        else:
            note.content, note.pinned = content, pinned
            note.save(update_fields=['content', 'pinned', 'updated_at'])
            status = 200
    return JsonResponse({'result': _serialize_note(note)}, status=status)


def _serialize_task(task):
    return {
        'id': task.id, 'type': task.type, 'type_label': task.get_type_display(), 'status': task.status,
        'status_label': DONE_LABELS.get(task.type) if task.status == 'DONE' else task.get_status_display(),
        'title': task.title, 'description': task.description, 'channel': task.channel,
        'channel_label': CHANNELS.get(task.channel, ''), 'result': task.result,
        'order': {'id': task.order_id, 'code': task.order.code} if task.order else None,
        'assignee': {'id': task.assignee_id, 'name': _user_name(task.assignee)} if task.assignee else None,
        'created_by': _user_name(task.created_by),
        'due_at': task.due_at.isoformat() if task.due_at else None,
        'overdue': bool(task.status == 'TODO' and task.due_at and task.due_at < timezone.now()),
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'created_at': task.created_at.isoformat(), 'updated_at': task.updated_at.isoformat(),
    }


def _apply_task(task, data, customer):
    """Gán trường từ payload; trả về thông báo lỗi hoặc None."""
    if 'type' in data:
        if data['type'] not in CustomerTask.Type.values:
            return 'Loại công việc không hợp lệ.'
        task.type = data['type']
    if 'status' in data:
        if data['status'] not in CustomerTask.Status.values:
            return 'Trạng thái không hợp lệ.'
        task.status = data['status']
    for field, limit in (('title', 255), ('description', MAX_NOTE), ('result', MAX_NOTE)):
        if field in data:
            value = str(data[field] or '').strip()
            if len(value) > limit:
                return f'{field} quá dài.'
            setattr(task, field, value)
    if not task.title:
        task.title = CustomerTask.Type(task.type).label
    if 'channel' in data:
        channel = str(data['channel'] or '')
        if channel and channel not in CHANNELS:
            return 'Kênh liên hệ không hợp lệ.'
        task.channel = channel
    if 'due_at' in data:
        if data['due_at'] in (None, ''):
            task.due_at = None
        else:
            due = parse_datetime(str(data['due_at']))
            if due is None:
                return 'Hạn xử lý không hợp lệ.'
            task.due_at = due if timezone.is_aware(due) else timezone.make_aware(due)
    if 'order_id' in data:
        if data['order_id'] in (None, ''):
            task.order = None
        else:
            order = customer.orders.filter(pk=data['order_id']).first() if str(data['order_id']).isdigit() else None
            if order is None:
                return 'Đơn hàng không thuộc khách hàng này.'
            task.order = order
    if 'assignee_id' in data:
        if data['assignee_id'] in (None, ''):
            task.assignee = None
        else:
            assignee = User.objects.filter(pk=data['assignee_id'], is_staff=True, is_active=True).first() \
                if str(data['assignee_id']).isdigit() else None
            if assignee is None:
                return 'Người phụ trách không hợp lệ.'
            task.assignee = assignee
    return None


@csrf_exempt
def customer_tasks(request, customer_id, task_id=None):
    customer, error = _staff_customer(request, customer_id)
    if error:
        return error
    if task_id is None and request.method == 'GET':
        tasks = customer.tasks.select_related('order', 'assignee', 'assignee__customer', 'created_by', 'created_by__customer')
        rank = {'TODO': 0, 'DONE': 1, 'CANCELLED': 2}
        far = timezone.now() + datetime.timedelta(days=36500)
        tasks = sorted(tasks, key=lambda t: (rank[t.status], t.due_at or far if t.status == 'TODO' else far,
                                             -t.created_at.timestamp()))
        staff = User.objects.filter(is_staff=True, is_active=True).order_by('first_name', 'username')
        return JsonResponse({
            'results': [_serialize_task(t) for t in tasks],
            'options': {
                'types': [{'value': v, 'label': l, 'done_label': DONE_LABELS[v]} for v, l in CustomerTask.Type.choices],
                'statuses': [{'value': v, 'label': l} for v, l in CustomerTask.Status.choices],
                'channels': [{'value': v, 'label': l} for v, l in CHANNELS.items()],
                'assignees': [{'value': u.id, 'label': _user_name(u)} for u in staff],
                'orders': [{'value': o.id, 'label': o.code} for o in customer.orders.order_by('-created_at')[:50]],
            }})
    task = None
    if task_id is not None:
        task = customer.tasks.filter(pk=task_id).first()
        if task is None:
            return JsonResponse({'message': 'Không tìm thấy công việc.'}, status=404)
        if request.method == 'DELETE':
            task.delete()
            return JsonResponse({'deleted': True})
        if request.method != 'PATCH':
            return JsonResponse({'message': 'Method not allowed.'}, status=405)
    elif request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Dữ liệu không hợp lệ.'}, status=400)
    created = task is None
    task = task or CustomerTask(customer=customer, created_by=request.user, assignee=request.user)
    was_done = task.status == CustomerTask.Status.DONE
    message = _apply_task(task, data, customer)
    if message:
        return JsonResponse({'message': message}, status=400)
    done = task.status == CustomerTask.Status.DONE
    task.completed_at = (task.completed_at or timezone.now()) if done else None
    with transaction.atomic():
        task.save()
        summary = {'task_id': task.id, 'task_type': task.type, 'type_label': task.get_type_display(),
                   'channel': CHANNELS.get(task.channel, ''), 'result': task.result[:300],
                   'order': task.order.code if task.order else None}
        if created:
            crm.record(customer, crm.Type.TASK_CREATED, summary, actor=request.user, source=crm.Source.STAFF,
                       title=f'Tạo công việc: {task.title}')
        if done and not was_done:
            crm.record(customer, crm.Type.TASK_COMPLETED, summary, actor=request.user, source=crm.Source.STAFF,
                       title=f'{DONE_LABELS[task.type]}: {task.title}')
    task = CustomerTask.objects.select_related('order', 'assignee', 'created_by').get(pk=task.pk)
    return JsonResponse({'result': _serialize_task(task)}, status=201 if created else 200)

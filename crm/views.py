from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from housing.forms import RejectForm
from housing.models import Booking, Housing
from notifications.models import Notification
from reviews.models import Review
from support.forms import TicketMessageForm, TicketStaffForm
from support.models import Ticket, TicketMessage


def _ctx(active, **extra):
    ctx = {
        'active': active,
        'nav_counts': {
            'moderation': Housing.objects.pending().count(),
            'tickets': Ticket.objects.open_only().count(),
            'reviews': Review.objects.filter(status=Review.PENDING).count(),
        },
    }
    ctx.update(extra)
    return ctx


def _page(request, qs, per_page=25):
    if not qs.query.order_by and not qs.model._meta.ordering:
        qs = qs.order_by('-pk')
    return Paginator(qs, per_page).get_page(request.GET.get('page'))


@staff_member_required
def dashboard(request):
    today = timezone.localdate()
    week_ago = timezone.now() - timedelta(days=7)

    month_start = timezone.make_aware(
        timezone.datetime.combine(today.replace(day=1), timezone.datetime.min.time()))
    gmv = (Booking.objects.filter(status__in=(Booking.CONFIRMED, Booking.COMPLETED),
                                  created_at__gte=month_start)
           .aggregate(s=Sum('total_price'))['s'] or 0)

    stats = [
        dict(label='Пользователи', value=User.objects.count(),
             delta=f'+{User.objects.filter(date_joined__gte=week_ago).count()} за неделю',
             tone='up'),
        dict(label='Активные объявления', value=Housing.objects.public().count(),
             delta=f'всего {Housing.objects.count()}', tone=''),
        dict(label='На модерации', value=Housing.objects.pending().count(),
             delta='требует внимания' if Housing.objects.pending().exists() else 'очередь пуста',
             tone=''),
        dict(label='Открытые тикеты', value=Ticket.objects.open_only().count(),
             delta=f'всего {Ticket.objects.count()}', tone=''),
        dict(label='Броней сегодня', value=Booking.objects.filter(
            created_at__date=today).count(), delta='новых заявок', tone='up'),
        dict(label='Оборот за месяц', value=f'{int(gmv):,}'.replace(',', ' ') + ' ₽',
             delta='подтверждённые брони', tone='up'),
    ]

    activity = []
    for h in Housing.objects.pending().order_by('-updated_at')[:3]:
        activity.append(dict(when=h.updated_at, who=h.owner,
                             what=f'отправил объявление «{h.title}» на модерацию'))
    for b in Booking.objects.select_related('guest', 'housing').order_by('-created_at')[:3]:
        activity.append(dict(when=b.created_at, who=b.guest,
                             what=f'создал бронь #{b.pk} на {b.nights} ноч.'))
    for t in Ticket.objects.with_user().order_by('-created_at')[:3]:
        activity.append(dict(when=t.created_at, who=t.user,
                             what=f'открыл тикет #{t.pk} — {t.subject}'))
    activity.sort(key=lambda x: x['when'], reverse=True)

    return render(request, 'crm/dashboard.html', _ctx(
        'dashboard', stats=stats, activity=activity[:8],
        queue=Housing.objects.pending()[:3]))


@staff_member_required
def moderation(request):
    qs = Housing.objects.pending().prefetch_related('images')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(owner__username__icontains=q))
    return render(request, 'crm/moderation.html', _ctx(
        'moderation', queue=_page(request, qs, 10),
        reject_form=RejectForm(), q=q))


@staff_member_required
def moderate_action(request, pk, action):
    housing = get_object_or_404(Housing.objects.select_related('owner'), pk=pk)
    if request.method != 'POST':
        return redirect('crm_moderation')

    if action == 'approve':
        housing.approve(by=request.user)
        Notification.push(housing.owner,
                          f'Объявление «{housing.title}» одобрено и опубликовано',
                          url=housing.get_absolute_url(), kind=Notification.MODERATION)
        messages.success(request, f'«{housing.title}» одобрено.')

    elif action == 'reject':
        form = RejectForm(request.POST)
        if form.is_valid():
            reason = form.full_reason()
            housing.reject(reason, by=request.user)
            Notification.push(housing.owner,
                              f'Объявление «{housing.title}» отклонено: {reason}',
                              url='/dashboard/listings/', kind=Notification.MODERATION)
            messages.info(request, f'«{housing.title}» отклонено.')
        else:
            messages.error(request, 'Укажите причину отказа.')

    elif action == 'feature':
        housing.is_featured = not housing.is_featured
        housing.save(update_fields=['is_featured'])
        messages.success(request, 'Флаг «на главной» переключён.')

    return redirect(request.META.get('HTTP_REFERER') or 'crm_moderation')


@staff_member_required
def listings(request):
    qs = (Housing.objects.select_related('owner')
          .annotate(bookings_n=Count('bookings')).order_by('-created_at'))
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(owner__username__icontains=q))
    if status in dict(Housing.STATUS_CHOICES):
        qs = qs.filter(status=status)
    return render(request, 'crm/listings.html', _ctx(
        'listings', rows=_page(request, qs), statuses=Housing.STATUS_CHOICES,
        q=q, current_status=status))


@staff_member_required
def bookings(request):
    qs = Booking.objects.select_related('housing', 'guest', 'housing__owner')
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status')
    if q:
        qs = qs.filter(Q(housing__title__icontains=q) | Q(guest__username__icontains=q))
    if status in dict(Booking.STATUS_CHOICES):
        qs = qs.filter(status=status)
    return render(request, 'crm/bookings.html', _ctx(
        'bookings', rows=_page(request, qs), statuses=Booking.STATUS_CHOICES,
        q=q, current_status=status))


@staff_member_required
def booking_action(request, pk, action):
    booking = get_object_or_404(
        Booking.objects.select_related('housing', 'guest', 'housing__owner'), pk=pk)
    if request.method == 'POST':
        if action == 'confirm':
            booking.confirm(by=request.user)
            Notification.push(booking.guest, f'Бронь «{booking.housing.title}» подтверждена',
                              url='/dashboard/bookings/', kind=Notification.BOOKING)
        elif action == 'cancel':
            booking.cancel(by=request.user)
            Notification.push(booking.guest, f'Бронь «{booking.housing.title}» отменена поддержкой',
                              url='/dashboard/bookings/', kind=Notification.BOOKING)
        elif action == 'complete':
            booking.complete()
        messages.success(request, f'Бронь #{pk}: статус обновлён.')
    return redirect(request.META.get('HTTP_REFERER') or 'crm_bookings')


@staff_member_required
def tickets(request):
    qs = Ticket.objects.with_user().annotate(msgs=Count('messages')).order_by('-updated_at')
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status')
    if q:
        qs = qs.filter(Q(subject__icontains=q) | Q(user__username__icontains=q))
    if status in dict(Ticket.STATUS_CHOICES):
        qs = qs.filter(status=status)
    return render(request, 'crm/tickets.html', _ctx(
        'tickets', rows=_page(request, qs), statuses=Ticket.STATUS_CHOICES,
        q=q, current_status=status))


@staff_member_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket.objects.with_user(), pk=pk)

    if request.method == 'POST':
        if 'reply' in request.POST:
            form = TicketMessageForm(request.POST)
            if form.is_valid():
                msg = form.save(commit=False)
                msg.ticket = ticket
                msg.author = request.user
                msg.save()
                Notification.push(ticket.user,
                                  f'Ответ поддержки по обращению #{ticket.pk}',
                                  url=f'/support/{ticket.pk}/', kind=Notification.SUPPORT)
                if 'close' in request.POST:
                    ticket.close()
                messages.success(request, 'Ответ отправлен.')
                return redirect('crm_ticket', pk=pk)
        else:
            staff_form = TicketStaffForm(request.POST, instance=ticket)
            if staff_form.is_valid():
                staff_form.save()
                messages.success(request, 'Тикет обновлён.')
                return redirect('crm_ticket', pk=pk)

    stats = dict(
        bookings=Booking.objects.filter(guest=ticket.user).count(),
        listings=Housing.objects.filter(owner=ticket.user).count(),
        tickets=Ticket.objects.filter(user=ticket.user).count(),
    )
    return render(request, 'crm/ticket.html', _ctx(
        'tickets', ticket=ticket, thread=ticket.messages.select_related('author'),
        form=TicketMessageForm(), staff_form=TicketStaffForm(instance=ticket),
        stats=stats))


@staff_member_required
def reviews(request):
    qs = Review.objects.select_related('housing', 'author')
    status = request.GET.get('status')
    if status in dict(Review.STATUS_CHOICES):
        qs = qs.filter(status=status)
    return render(request, 'crm/reviews.html', _ctx(
        'reviews', rows=_page(request, qs), statuses=Review.STATUS_CHOICES,
        current_status=status))


@staff_member_required
def review_action(request, pk, action):
    review = get_object_or_404(Review.objects.select_related('housing', 'author'), pk=pk)
    if request.method == 'POST':
        if action == 'publish':
            review.publish(by=request.user)
            Notification.push(review.author,
                              f'Ваш отзыв о «{review.housing.title}» опубликован',
                              url=review.housing.get_absolute_url(), kind=Notification.REVIEW)
            messages.success(request, 'Отзыв опубликован, рейтинг пересчитан.')
        elif action == 'reject':
            review.reject(note=request.POST.get('note', ''), by=request.user)
            Notification.push(review.author,
                              f'Отзыв о «{review.housing.title}» отклонён модератором',
                              kind=Notification.REVIEW)
            messages.info(request, 'Отзыв отклонён.')
    return redirect(request.META.get('HTTP_REFERER') or 'crm_reviews')


@staff_member_required
def users(request):
    qs = (User.objects.select_related('profile')
          .annotate(listings_n=Count('listings', distinct=True),
                    bookings_n=Count('bookings', distinct=True))
          .order_by('-date_joined'))
    q = request.GET.get('q', '').strip()
    role = request.GET.get('role')
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if role in ('tenant', 'landlord'):
        qs = qs.filter(profile__role=role)
    if request.GET.get('blocked'):
        qs = qs.filter(profile__is_blocked=True)
    return render(request, 'crm/users.html', _ctx(
        'users', rows=_page(request, qs), q=q, current_role=role))


@staff_member_required
def user_action(request, pk, action):
    target = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    if request.method != 'POST':
        return redirect('crm_users')

    if target == request.user:
        messages.error(request, 'Нельзя изменить собственную учётную запись отсюда.')
    elif action == 'block':
        target.profile.block()
        messages.info(request, f'{target.username} заблокирован.')
    elif action == 'unblock':
        target.profile.unblock()
        messages.success(request, f'{target.username} разблокирован.')
    elif action == 'make_landlord':
        target.profile.make_landlord()
        messages.success(request, f'{target.username} — теперь арендодатель.')
    return redirect(request.META.get('HTTP_REFERER') or 'crm_users')

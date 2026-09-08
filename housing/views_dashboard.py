import calendar as cal
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render

from notifications.models import Notification
from reviews.models import Review
from support.models import Ticket

from .models import Booking, Housing


def _ctx(request, active, **extra):
    user = request.user
    guest_qs = Booking.objects.for_guest(user)
    host_qs = Booking.objects.for_host(user)
    ctx = {
        'active': active,
        'is_host': user.profile.is_landlord,
        'notifications': Notification.objects.filter(user=user)[:5],
        'unread_count': Notification.objects.filter(user=user, is_read=False).count(),
        'counts': {
            'bookings': guest_qs.exclude(status=Booking.CANCELLED).count(),
            'requests': host_qs.filter(status=Booking.PENDING).count(),
            'listings': Housing.objects.filter(owner=user).count(),
            'tickets': Ticket.objects.filter(user=user).open_only().count(),
        },
    }
    ctx.update(extra)
    return ctx


def _grouped(qs):
    items = list(qs)
    return {
        'upcoming': [b for b in items if b.status == Booking.CONFIRMED],
        'pending': [b for b in items if b.status == Booking.PENDING],
        'past': [b for b in items if b.status == Booking.COMPLETED],
        'cancelled': [b for b in items
                      if b.status in (Booking.CANCELLED, Booking.DECLINED)],
        'all': items,
    }


@login_required
def dashboard(request):
    user = request.user
    grouped = _grouped(Booking.objects.for_guest(user))
    earned = (Booking.objects.for_host(user)
              .filter(status__in=(Booking.CONFIRMED, Booking.COMPLETED))
              .aggregate(total=Sum('total_price'))['total'] or 0)
    return render(request, 'housing/dashboard/overview.html', _ctx(
        request, 'overview',
        grouped=grouped,
        listings=Housing.objects.filter(owner=user)[:4],
        earned=earned,
        pending_reviews=Booking.objects.for_guest(user).filter(
            status=Booking.COMPLETED, review__isnull=True)[:3],
    ))


@login_required
def my_bookings(request):
    return render(request, 'housing/dashboard/bookings.html', _ctx(
        request, 'bookings',
        grouped=_grouped(Booking.objects.for_guest(request.user))))


@login_required
def booking_requests(request):
    return render(request, 'housing/dashboard/requests.html', _ctx(
        request, 'requests',
        grouped=_grouped(Booking.objects.for_host(request.user))))


@login_required
def my_listings(request):
    qs = (Housing.objects.filter(owner=request.user)
          .annotate(bookings_n=Count('bookings'))
          .prefetch_related('amenities').order_by('-created_at'))
    status = request.GET.get('status')
    if status in dict(Housing.STATUS_CHOICES):
        qs = qs.filter(status=status)
    return render(request, 'housing/dashboard/listings.html', _ctx(
        request, 'listings', listings=qs,
        statuses=Housing.STATUS_CHOICES, current_status=status))


@login_required
def my_reviews(request):
    user = request.user
    written = Review.objects.filter(author=user).select_related('housing')
    received = (Review.objects.filter(housing__owner=user, status=Review.PUBLISHED)
                .select_related('housing', 'author'))
    awaiting = Booking.objects.for_guest(user).filter(
        status=Booking.COMPLETED, review__isnull=True)
    return render(request, 'housing/dashboard/reviews.html', _ctx(
        request, 'reviews', written=written, received=received, awaiting=awaiting))


@login_required
def favorites(request):
    ids = request.session.get('favorites', [])
    return render(request, 'housing/dashboard/favorites.html', _ctx(
        request, 'favorites',
        listings=Housing.objects.public().filter(pk__in=ids)))


@login_required
def favorite_toggle(request, pk):
    ids = request.session.get('favorites', [])
    if pk in ids:
        ids.remove(pk)
        messages.info(request, 'Убрано из избранного.')
    else:
        ids.append(pk)
        messages.success(request, 'Добавлено в избранное.')
    request.session['favorites'] = ids
    return redirect(request.META.get('HTTP_REFERER', 'catalog'))


@login_required
def host_calendar(request):
    today = date.today()
    weeks = cal.Calendar(firstweekday=0).monthdatescalendar(today.year, today.month)

    booked = {}
    qs = (Booking.objects.for_host(request.user)
          .filter(status__in=Booking.BLOCKING))
    for b in qs:
        d = b.check_in
        while d < b.check_out:
            booked[d] = b
            d += timedelta(days=1)

    grid = [[{'date': d, 'other': d.month != today.month, 'today': d == today,
              'booking': booked.get(d)} for d in w] for w in weeks]
    return render(request, 'housing/dashboard/calendar.html', _ctx(
        request, 'calendar', grid=grid, month=today, upcoming=qs[:5],
        weekdays=['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']))


@login_required
def earnings(request):
    qs = Booking.objects.for_host(request.user).filter(
        status__in=(Booking.CONFIRMED, Booking.COMPLETED))
    gross = qs.aggregate(s=Sum('total_price'))['s'] or 0
    pending = (Booking.objects.for_host(request.user)
               .filter(status=Booking.PENDING)
               .aggregate(s=Sum('total_price'))['s'] or 0)
    fee = round(float(gross) * 0.10, 2)

    rows = {}
    for b in qs:
        key = b.check_in.strftime('%Y-%m')
        r = rows.setdefault(key, {'period': b.check_in.strftime('%m.%Y'),
                                  'bookings': 0, 'gross': 0})
        r['bookings'] += 1
        r['gross'] += float(b.total_price)
    for r in rows.values():
        r['fee'] = round(r['gross'] * 0.10, 2)
        r['net'] = round(r['gross'] - r['fee'], 2)

    return render(request, 'housing/dashboard/earnings.html', _ctx(
        request, 'earnings',
        gross=gross, pending=pending, fee=fee, payout=float(gross) - fee,
        rows=sorted(rows.values(), key=lambda x: x['period'], reverse=True)))


@login_required
def settings_view(request):
    from users.forms import ProfileForm
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        email = request.POST.get('email', '').strip()
        if form.is_valid():
            form.save()
            if email and email != request.user.email:
                request.user.email = email
                request.user.save(update_fields=['email'])
            messages.success(request, 'Профиль сохранён.')
            return redirect('dashboard_settings')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'housing/dashboard/settings.html',
                  _ctx(request, 'settings', form=form))

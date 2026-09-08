from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from notifications.models import Notification
from reviews.models import Review

from .forms import BookingForm, HousingForm
from .models import Amenity, Booking, Housing

SORT_OPTIONS = [
    ('-created_at', 'Сначала новые'), ('price', 'Сначала дешёвые'),
    ('-price', 'Сначала дорогие'), ('-rating', 'По рейтингу'),
]


def styleguide(request):
    if not settings.DEBUG and not request.user.is_staff:
        raise Http404
    colors = [
        ('accent', '--color-accent'), ('accent-hover', '--color-accent-hover'),
        ('bg', '--color-bg'), ('surface', '--color-surface'),
        ('surface-alt', '--color-surface-alt'), ('ink', '--color-ink'),
        ('ink-muted', '--color-ink-muted'), ('ink-faint', '--color-ink-faint'),
        ('border', '--color-border'), ('success', '--color-success'),
        ('warning', '--color-warning'), ('danger', '--color-danger'),
        ('info', '--color-info'), ('dark', '--color-dark'),
    ]
    return render(request, 'housing/styleguide.html',
                  {'colors': colors, 'demo_cards': Housing.objects.public()[:3]})


def index(request):
    return render(request, 'housing/index.html', {
        'featured': Housing.objects.featured()[:8],
        'stats': {
            'listings': Housing.objects.public().count(),
            'reviews': Review.objects.filter(status=Review.PUBLISHED).count(),
        },
    })


def catalog(request):
    qs = Housing.objects.public()
    g = request.GET
    active = []

    deal = g.get('deal_type')
    if deal in (Housing.RENT, Housing.SALE):
        qs = qs.filter(deal_type=deal)
        active.append({'param': 'deal_type', 'label': dict(Housing.DEAL_CHOICES)[deal]})

    rooms = g.get('rooms')
    if rooms and rooms.isdigit():
        n = int(rooms)
        qs = qs.filter(rooms__gte=n) if n >= 4 else qs.filter(rooms=n)
        active.append({'param': 'rooms',
                       'label': f'{n}+ комнат' if n >= 4 else f'{n} комн.'})

    guests = g.get('guests')
    if guests and guests.isdigit():
        qs = qs.filter(guests__gte=int(guests))
        active.append({'param': 'guests', 'label': f'от {guests} гостей'})

    price_min = g.get('price_min')
    if price_min and price_min.isdigit():
        qs = qs.filter(price__gte=int(price_min))
        active.append({'param': 'price_min', 'label': f'от {price_min} ₽'})

    price_max = g.get('price_max')
    if price_max and price_max.isdigit():
        qs = qs.filter(price__lte=int(price_max))
        active.append({'param': 'price_max', 'label': f'до {price_max} ₽'})

    htype = g.get('type')
    if htype in dict(Housing.TYPE_CHOICES):
        qs = qs.filter(housing_type=htype)
        active.append({'param': 'type', 'label': dict(Housing.TYPE_CHOICES)[htype]})

    picked = [a for a in g.getlist('amenity') if a]
    if picked:
        for code in picked:
            qs = qs.filter(amenities__code=code)
        qs = qs.distinct()
        names = dict(Amenity.objects.filter(code__in=picked).values_list('code', 'name'))
        for code in picked:
            active.append({'param': 'amenity', 'label': names.get(code, code)})

    sort = g.get('sort')
    qs = qs.order_by(sort if sort in dict(SORT_OPTIONS) else '-created_at')

    paginator = Paginator(qs, 12)
    page = paginator.get_page(g.get('page'))

    params = g.copy()
    params.pop('page', None)
    for item in active:
        rest = params.copy()
        rest.pop(item['param'], None)
        item['url'] = ('?' + rest.urlencode()) if rest else request.path

    return render(request, 'housing/catalog.html', {
        'page_obj': page,
        'housings': page.object_list,
        'total': paginator.count,
        'querystring': params.urlencode(),
        'active_filters': active,
        'sort_options': SORT_OPTIONS,
        'sort_label': dict(SORT_OPTIONS).get(sort, 'Сначала новые'),
        'amenities': Amenity.objects.all(),
        'housing_types': Housing.TYPE_CHOICES,
        'active_catalog': True,
        'get': g,
    })


def service(request):
    return render(request, 'housing/service.html', {'active_service': True})


def help_center(request):
    faq = [
        ('Как забронировать жильё?',
         'Выберите объект в каталоге, укажите даты и число гостей и отправьте заявку. '
         'Хозяин подтверждает бронь — вы получите уведомление.'),
        ('Когда списываются деньги?',
         'Оплата происходит после подтверждения брони хозяином. До подтверждения '
         'деньги не списываются.'),
        ('Как отменить бронирование?',
         'В личном кабинете → «Мои бронирования» нажмите «Отменить».'),
        ('Как разместить своё жильё?',
         'Зарегистрируйтесь и нажмите «Разместить». Заполните карточку объекта и '
         'отправьте на модерацию — проверка занимает до 24 часов.'),
        ('Почему объявление отклонили?',
         'Причина приходит в уведомлении и видна в карточке объявления. Исправьте '
         'и отправьте снова.'),
        ('Как оставить отзыв?',
         'Отзыв можно оставить после завершения поездки — приглашение появится '
         'в разделе «Отзывы» личного кабинета.'),
    ]
    return render(request, 'housing/help.html', {'faq': faq, 'active_support': True})


def housing_detail(request, pk):
    housing = get_object_or_404(
        Housing.objects.select_related('owner').prefetch_related('amenities', 'images'),
        pk=pk)

    if not housing.is_published and not (
            request.user.is_staff or housing.owner_id == request.user.id):
        raise Http404

    Housing.objects.filter(pk=pk).update(views_count=F('views_count') + 1)

    reviews = (Review.objects.filter(housing=housing, status=Review.PUBLISHED)
               .select_related('author'))
    breakdown = []
    total = reviews.count()
    for score in (5, 4, 3, 2, 1):
        n = sum(1 for r in reviews if r.rating == score)
        breakdown.append((score, round(n * 100 / total) if total else 0))

    return render(request, 'housing/detail.html', {
        'housing': housing,
        'similar': Housing.objects.public().exclude(pk=pk)[:4],
        'reviews': reviews,
        'breakdown': breakdown,
        'booking_form': BookingForm(housing=housing, guest=request.user
                                    if request.user.is_authenticated else None),
        'active_catalog': True,
    })


@login_required
def housing_add(request):
    if request.method == 'POST':
        form = HousingForm(request.POST, request.FILES)
        if form.is_valid():
            housing = form.save(commit=False)
            housing.owner = request.user
            housing.status = (Housing.PENDING if 'submit' in request.POST
                              else Housing.DRAFT)
            housing.save()
            form.save_m2m()
            request.user.profile.make_landlord()
            if housing.status == Housing.PENDING:
                messages.success(request, 'Объявление отправлено на модерацию.')
            else:
                messages.success(request, 'Черновик сохранён.')
            return redirect('my_listings')
    else:
        form = HousingForm()
    return render(request, 'housing/housing_form.html', {'form': form})


@login_required
def housing_edit(request, pk):
    housing = get_object_or_404(Housing, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = HousingForm(request.POST, request.FILES, instance=housing)
        if form.is_valid():
            obj = form.save()
            if 'submit' in request.POST:
                obj.submit_for_moderation()
                messages.success(request, 'Объявление отправлено на модерацию.')
            else:
                messages.success(request, 'Изменения сохранены.')
            return redirect('my_listings')
    else:
        form = HousingForm(instance=housing)
    return render(request, 'housing/housing_form.html',
                  {'form': form, 'housing': housing})


@login_required
def housing_submit(request, pk):
    housing = get_object_or_404(Housing, pk=pk, owner=request.user)
    if request.method == 'POST':
        housing.submit_for_moderation()
        messages.success(request, f'«{housing.title}» отправлено на модерацию.')
    return redirect('my_listings')


@login_required
def housing_delete(request, pk):
    housing = get_object_or_404(Housing, pk=pk, owner=request.user)
    if request.method == 'POST':
        title = housing.title
        housing.delete()
        messages.success(request, f'Объявление «{title}» удалено.')
        return redirect('my_listings')
    return render(request, 'housing/housing_confirm_delete.html', {'housing': housing})


@login_required
def booking_create(request, pk):
    housing = get_object_or_404(Housing.objects.public(), pk=pk)
    if request.method != 'POST':
        return redirect(housing.get_absolute_url())

    form = BookingForm(request.POST, housing=housing, guest=request.user)
    if form.is_valid():
        booking = form.save()
        Notification.push(
            housing.owner,
            f'Новая заявка на бронь «{housing.title}» от {request.user.username}',
            url='/dashboard/requests/', kind=Notification.BOOKING)
        messages.success(request, 'Заявка отправлена. Хозяин ответит в ближайшее время.')
        return redirect('my_bookings')

    for error in form.non_field_errors():
        messages.error(request, error)
    for field, errs in form.errors.items():
        if field != '__all__':
            messages.error(request, f'{form.fields[field].label}: {errs[0]}')
    return redirect(housing.get_absolute_url())


@login_required
def booking_action(request, pk, action):
    booking = get_object_or_404(
        Booking.objects.select_related('housing', 'guest', 'housing__owner'), pk=pk)
    is_host = booking.housing.owner_id == request.user.id
    is_guest = booking.guest_id == request.user.id

    if request.method != 'POST' or not (is_host or is_guest):
        raise Http404

    if action == 'confirm' and is_host and booking.status == Booking.PENDING:
        booking.confirm(by=request.user)
        Notification.push(booking.guest,
                          f'Бронь «{booking.housing.title}» подтверждена',
                          url='/dashboard/bookings/', kind=Notification.BOOKING)
        messages.success(request, 'Бронь подтверждена.')

    elif action == 'decline' and is_host and booking.status == Booking.PENDING:
        booking.decline(by=request.user)
        Notification.push(booking.guest,
                          f'Бронь «{booking.housing.title}» отклонена',
                          url='/dashboard/bookings/', kind=Notification.BOOKING)
        messages.info(request, 'Заявка отклонена.')

    elif action == 'cancel' and is_guest and booking.status in (
            Booking.PENDING, Booking.CONFIRMED):
        booking.cancel(by=request.user)
        Notification.push(booking.housing.owner,
                          f'Гость отменил бронь «{booking.housing.title}»',
                          url='/dashboard/requests/', kind=Notification.BOOKING)
        messages.info(request, 'Бронь отменена.')
    else:
        messages.error(request, 'Действие недоступно для текущего статуса брони.')

    return redirect('booking_requests' if is_host and not is_guest else 'my_bookings')

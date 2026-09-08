from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from housing.models import Booking
from notifications.models import Notification

from .forms import ReviewForm
from .models import Review


@login_required
def review_create(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('housing', 'housing__owner'),
        pk=booking_id, guest=request.user)

    if booking.status != Booking.COMPLETED:
        messages.error(request, 'Отзыв можно оставить только после завершения поездки.')
        return redirect('my_reviews')
    if hasattr(booking, 'review'):
        messages.info(request, 'Вы уже оставили отзыв об этой поездке.')
        return redirect('my_reviews')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.housing = booking.housing
            review.author = request.user
            review.save()
            Notification.push(
                booking.housing.owner,
                f'Новый отзыв о «{booking.housing.title}» — ждёт модерации',
                url='/dashboard/reviews/', kind=Notification.REVIEW)
            messages.success(request, 'Спасибо! Отзыв отправлен на модерацию.')
        else:
            messages.error(request, 'Проверьте форму: нужны оценка и текст отзыва.')
    return redirect('my_reviews')


@login_required
def review_reply(request, pk):
    review = get_object_or_404(Review.objects.select_related('housing', 'author'),
                               pk=pk, housing__owner=request.user)
    if request.method == 'POST':
        text = request.POST.get('reply', '').strip()
        if text:
            review.add_reply(text)
            Notification.push(review.author,
                              f'Хозяин ответил на ваш отзыв о «{review.housing.title}»',
                              url='/dashboard/reviews/', kind=Notification.REVIEW)
            messages.success(request, 'Ответ опубликован.')
    return redirect('my_reviews')

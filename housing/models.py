from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Amenity(models.Model):
    code = models.SlugField('Код', max_length=32, unique=True)
    name = models.CharField('Название', max_length=64)
    icon = models.CharField('Иконка', max_length=8, blank=True)
    order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Удобство'
        verbose_name_plural = 'Удобства'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class HousingQuerySet(models.QuerySet):
    def public(self):
        return self.filter(status=Housing.APPROVED).select_related('owner')

    def featured(self):
        return self.public().filter(is_featured=True)

    def pending(self):
        return self.filter(status=Housing.PENDING).select_related('owner')


class Housing(models.Model):
    RENT, SALE = 'rent', 'sale'
    DEAL_CHOICES = [(RENT, 'Аренда'), (SALE, 'Продажа')]


    TYPE_CHOICES = [
        ('apartment', 'Квартира'), ('studio', 'Студия'),
        ('apartments', 'Апартаменты'), ('house', 'Дом'), ('room', 'Комната'),
    ]


    DRAFT, PENDING, APPROVED, REJECTED = 'draft', 'pending', 'approved', 'rejected'
    STATUS_CHOICES = [
        (DRAFT, 'Черновик'), (PENDING, 'На модерации'),
        (APPROVED, 'Опубликовано'), (REJECTED, 'Отклонено'),
    ]
    STATUS_TONE = {DRAFT: 'neutral', PENDING: 'warning',
                   APPROVED: 'success', REJECTED: 'danger'}

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='listings', verbose_name='Владелец', null=True, blank=True)

    title = models.CharField('Заголовок', max_length=64, unique=True)
    slug = models.SlugField('Слаг', max_length=80, blank=True)
    short_description = models.CharField('Краткое описание', max_length=128, blank=True)
    description = models.TextField('Описание', blank=True)

    city = models.CharField('Город', max_length=64, default='Рязань')
    address = models.CharField('Адрес', max_length=255, blank=True)

    housing_type = models.CharField('Тип жилья', max_length=16,
                                    choices=TYPE_CHOICES, default='apartment')
    deal_type = models.CharField('Тип сделки', max_length=8,
                                 choices=DEAL_CHOICES, default=RENT)
    price = models.DecimalField('Цена', max_digits=11, decimal_places=2)
    rooms = models.PositiveIntegerField('Комнат', default=1)
    guests = models.PositiveIntegerField('Гостей', default=2)
    area = models.PositiveIntegerField('Площадь, м²', null=True, blank=True)

    amenities = models.ManyToManyField(Amenity, blank=True,
                                       related_name='housings', verbose_name='Удобства')
    image = models.ImageField('Главное фото', upload_to='housing/', blank=True, null=True)


    rating = models.DecimalField('Рейтинг', max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField('Отзывов', default=0)
    views_count = models.PositiveIntegerField('Просмотров', default=0)


    status = models.CharField('Статус', max_length=10,
                              choices=STATUS_CHOICES, default=DRAFT, db_index=True)
    rejection_reason = models.TextField('Причина отказа', blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moderated_listings', verbose_name='Проверил')
    moderated_at = models.DateTimeField('Проверено', null=True, blank=True)

    is_featured = models.BooleanField('Показывать на главной', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Изменено', auto_now=True)

    objects = HousingQuerySet.as_manager()

    class Meta:
        verbose_name = 'Жильё'
        verbose_name_plural = 'Жильё'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['deal_type', 'price']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)[:80]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('housing_detail', args=[self.pk])


    @property
    def is_published(self):
        return self.status == self.APPROVED

    @property
    def status_tone(self):
        return self.STATUS_TONE.get(self.status, 'neutral')

    @property
    def is_editable(self):
        return self.status in (self.DRAFT, self.REJECTED, self.APPROVED)


    def submit_for_moderation(self):
        self.status = self.PENDING
        self.rejection_reason = ''
        self.save(update_fields=['status', 'rejection_reason', 'updated_at'])

    def approve(self, by=None):
        self.status = self.APPROVED
        self.rejection_reason = ''
        self.moderated_by = by
        self.moderated_at = timezone.now()
        self.save(update_fields=['status', 'rejection_reason', 'moderated_by',
                                 'moderated_at', 'updated_at'])

    def reject(self, reason, by=None):
        self.status = self.REJECTED
        self.rejection_reason = reason
        self.moderated_by = by
        self.moderated_at = timezone.now()
        self.save(update_fields=['status', 'rejection_reason', 'moderated_by',
                                 'moderated_at', 'updated_at'])

    def recalc_rating(self):
        from reviews.models import Review
        agg = Review.objects.filter(
            housing=self, status=Review.PUBLISHED
        ).aggregate(avg=models.Avg('rating'), n=models.Count('id'))
        self.rating = Decimal(str(round(agg['avg'] or 0, 2)))
        self.reviews_count = agg['n'] or 0
        self.save(update_fields=['rating', 'reviews_count'])

    def busy_dates(self):
        dates = set()
        for b in self.bookings.filter(status__in=(Booking.CONFIRMED, Booking.COMPLETED)):
            d = b.check_in
            while d < b.check_out:
                dates.add(d)
                d += timedelta(days=1)
        return dates


class HousingImage(models.Model):
    housing = models.ForeignKey(Housing, on_delete=models.CASCADE,
                                related_name='images', verbose_name='Жильё')
    image = models.ImageField('Изображение', upload_to='housing/')
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_cover = models.BooleanField('Обложка', default=False)

    class Meta:
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии'
        ordering = ['-is_cover', 'order', 'id']

    def __str__(self):
        return f'Фото #{self.pk} — {self.housing.title}'


class BookingQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(status__in=(Booking.DECLINED, Booking.CANCELLED))

    def for_guest(self, user):
        return self.filter(guest=user).select_related('housing', 'housing__owner')

    def for_host(self, user):
        return self.filter(housing__owner=user).select_related('housing', 'guest')


class Booking(models.Model):
    PENDING, CONFIRMED, DECLINED, CANCELLED, COMPLETED = (
        'pending', 'confirmed', 'declined', 'cancelled', 'completed')
    STATUS_CHOICES = [
        (PENDING, 'Ожидает подтверждения'), (CONFIRMED, 'Подтверждена'),
        (DECLINED, 'Отклонена'), (CANCELLED, 'Отменена'), (COMPLETED, 'Завершена'),
    ]
    STATUS_TONE = {PENDING: 'warning', CONFIRMED: 'success', DECLINED: 'danger',
                   CANCELLED: 'neutral', COMPLETED: 'info'}

    BLOCKING = (CONFIRMED, COMPLETED)

    housing = models.ForeignKey(Housing, on_delete=models.CASCADE,
                                related_name='bookings', verbose_name='Жильё')
    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='bookings', verbose_name='Гость')
    check_in = models.DateField('Заезд')
    check_out = models.DateField('Выезд')
    guests = models.PositiveSmallIntegerField('Гостей', default=1)
    message = models.TextField('Сообщение хозяину', blank=True)

    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES,
                              default=PENDING, db_index=True)
    total_price = models.DecimalField('Сумма', max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField('Создана', auto_now_add=True)
    decided_at = models.DateTimeField('Решение принято', null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='decided_bookings', verbose_name='Решение принял')

    objects = BookingQuerySet.as_manager()

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'check_in'])]

    def __str__(self):
        return f'{self.housing.title}: {self.check_in}–{self.check_out}'


    @property
    def nights(self):
        return max((self.check_out - self.check_in).days, 0)

    @property
    def status_label(self):
        return self.get_status_display()

    @property
    def status_tone(self):
        return self.STATUS_TONE.get(self.status, 'neutral')

    @property
    def can_be_reviewed(self):
        return self.status == self.COMPLETED and not hasattr(self, 'review')

    def calc_total(self):
        return (self.housing.price or 0) * self.nights


    def clean(self):
        errors = {}
        if self.check_in and self.check_out:
            if self.check_out <= self.check_in:
                errors['check_out'] = 'Дата выезда должна быть позже даты заезда.'
            elif self.check_in < timezone.localdate() and not self.pk:
                errors['check_in'] = 'Нельзя забронировать прошедшую дату.'
        if self.housing_id and self.guests and self.guests > self.housing.guests:
            errors['guests'] = f'Максимум гостей для этого объекта — {self.housing.guests}.'
        if self.housing_id and self.guest_id and self.housing.owner_id == self.guest_id:
            errors['__all__'] = 'Нельзя забронировать собственное объявление.'
        if self.housing_id and self.check_in and self.check_out and not errors:
            if self.overlapping().exists():
                errors['__all__'] = 'Эти даты уже заняты подтверждённой бронью.'
        if errors:
            raise ValidationError(errors)

    def overlapping(self):
        qs = Booking.objects.filter(
            housing_id=self.housing_id,
            status__in=self.BLOCKING,
            check_in__lt=self.check_out,
            check_out__gt=self.check_in,
        )
        return qs.exclude(pk=self.pk) if self.pk else qs

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.calc_total()
        super().save(*args, **kwargs)


    def confirm(self, by=None):
        self.status = self.CONFIRMED
        self.decided_at = timezone.now()
        self.decided_by = by
        self.save(update_fields=['status', 'decided_at', 'decided_by'])

    def decline(self, by=None):
        self.status = self.DECLINED
        self.decided_at = timezone.now()
        self.decided_by = by
        self.save(update_fields=['status', 'decided_at', 'decided_by'])

    def cancel(self, by=None):
        self.status = self.CANCELLED
        self.decided_at = timezone.now()
        self.decided_by = by
        self.save(update_fields=['status', 'decided_at', 'decided_by'])

    def complete(self):
        self.status = self.COMPLETED
        self.save(update_fields=['status'])

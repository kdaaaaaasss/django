from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone


class Review(models.Model):
    PENDING, PUBLISHED, REJECTED = 'pending', 'published', 'rejected'
    STATUS_CHOICES = [
        (PENDING, 'На модерации'), (PUBLISHED, 'Опубликован'), (REJECTED, 'Отклонён'),
    ]
    STATUS_TONE = {PENDING: 'warning', PUBLISHED: 'success', REJECTED: 'danger'}

    booking = models.OneToOneField(
        'housing.Booking', on_delete=models.CASCADE,
        related_name='review', verbose_name='Бронирование')
    housing = models.ForeignKey(
        'housing.Housing', on_delete=models.CASCADE,
        related_name='reviews', verbose_name='Жильё')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reviews', verbose_name='Автор')

    rating = models.PositiveSmallIntegerField(
        'Оценка', validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField('Текст отзыва')

    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES,
                              default=PENDING, db_index=True)
    moderation_note = models.TextField('Заметка модератора', blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moderated_reviews', verbose_name='Проверил')

    reply = models.TextField('Ответ хозяина', blank=True)
    replied_at = models.DateTimeField('Отвечено', null=True, blank=True)

    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author} → {self.housing} ({self.rating}★)'

    @property
    def status_label(self):
        return self.get_status_display()

    @property
    def status_tone(self):
        return self.STATUS_TONE.get(self.status, 'neutral')

    @property
    def stars_on(self):
        return range(self.rating)

    @property
    def stars_off(self):
        return range(5 - self.rating)

    def clean(self):
        from housing.models import Booking
        if not self.booking_id:
            return
        booking = self.booking
        if booking.status != Booking.COMPLETED:
            raise ValidationError('Отзыв можно оставить только после завершения поездки.')
        if self.author_id and booking.guest_id != self.author_id:
            raise ValidationError('Отзыв может оставить только гость этой брони.')

    def save(self, *args, **kwargs):
        if self.booking_id and not self.housing_id:
            self.housing = self.booking.housing
        if self.booking_id and not self.author_id:
            self.author = self.booking.guest
        super().save(*args, **kwargs)


    def publish(self, by=None):
        self.status = self.PUBLISHED
        self.moderated_by = by
        self.save(update_fields=['status', 'moderated_by'])

    def reject(self, note='', by=None):
        self.status = self.REJECTED
        self.moderation_note = note
        self.moderated_by = by
        self.save(update_fields=['status', 'moderation_note', 'moderated_by'])

    def add_reply(self, text):
        self.reply = text
        self.replied_at = timezone.now()
        self.save(update_fields=['reply', 'replied_at'])


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def _recalc_housing_rating(sender, instance, **kwargs):
    if instance.housing_id:
        try:
            instance.housing.recalc_rating()
        except Exception:
            pass

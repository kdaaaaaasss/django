from django.conf import settings
from django.db import models


class Notification(models.Model):
    BOOKING, MODERATION, REVIEW, SUPPORT, SYSTEM = (
        'booking', 'moderation', 'review', 'support', 'system')
    KIND_CHOICES = [
        (BOOKING, 'Бронирование'), (MODERATION, 'Модерация'),
        (REVIEW, 'Отзыв'), (SUPPORT, 'Поддержка'), (SYSTEM, 'Система'),
    ]
    ICONS = {BOOKING: '📅', MODERATION: '🛡', REVIEW: '★', SUPPORT: '💬', SYSTEM: 'ℹ'}

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='notifications', verbose_name='Получатель')
    kind = models.CharField('Тип', max_length=16, choices=KIND_CHOICES, default=SYSTEM)
    verb = models.CharField('Текст', max_length=200)
    url = models.CharField('Ссылка', max_length=200, blank=True)
    is_read = models.BooleanField('Прочитано', default=False, db_index=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user}: {self.verb[:40]}'

    @property
    def icon(self):
        return self.ICONS.get(self.kind, 'ℹ')

    @classmethod
    def push(cls, user, verb, url='', kind=SYSTEM):
        if user is None:
            return None
        return cls.objects.create(user=user, verb=verb, url=url, kind=kind)

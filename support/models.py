from django.conf import settings
from django.db import models
from django.utils import timezone


class TicketQuerySet(models.QuerySet):
    def open_only(self):
        return self.exclude(status=Ticket.CLOSED)

    def with_user(self):
        return self.select_related('user', 'assigned_to')


class Ticket(models.Model):
    OPEN, PENDING, CLOSED = 'open', 'pending', 'closed'
    STATUS_CHOICES = [(OPEN, 'Открыт'), (PENDING, 'В работе'), (CLOSED, 'Закрыт')]
    STATUS_TONE = {OPEN: 'warning', PENDING: 'info', CLOSED: 'success'}

    LOW, NORMAL, HIGH, URGENT = 'low', 'normal', 'high', 'urgent'
    PRIORITY_CHOICES = [(LOW, 'Низкий'), (NORMAL, 'Обычный'),
                        (HIGH, 'Высокий'), (URGENT, 'Срочный')]
    PRIORITY_TONE = {LOW: 'neutral', NORMAL: 'neutral', HIGH: 'warning', URGENT: 'danger'}

    CATEGORY_CHOICES = [
        ('booking', 'Проблема с бронированием'), ('payment', 'Оплата'),
        ('listing', 'Объявление и модерация'), ('account', 'Аккаунт и доступ'),
        ('other', 'Другое'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='tickets', verbose_name='Пользователь')
    subject = models.CharField('Тема', max_length=140)
    category = models.CharField('Категория', max_length=16,
                                choices=CATEGORY_CHOICES, default='other')
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES,
                              default=OPEN, db_index=True)
    priority = models.CharField('Приоритет', max_length=10,
                                choices=PRIORITY_CHOICES, default=NORMAL)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tickets', verbose_name='Исполнитель',
        limit_choices_to={'is_staff': True})

    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)
    closed_at = models.DateTimeField('Закрыт', null=True, blank=True)

    objects = TicketQuerySet.as_manager()

    class Meta:
        verbose_name = 'Обращение'
        verbose_name_plural = 'Обращения'
        ordering = ['-updated_at']

    def __str__(self):
        return f'#{self.pk} {self.subject}'

    @property
    def status_label(self):
        return self.get_status_display()

    @property
    def status_tone(self):
        return self.STATUS_TONE.get(self.status, 'neutral')

    @property
    def priority_tone(self):
        return self.PRIORITY_TONE.get(self.priority, 'neutral')

    @property
    def category_label(self):
        return self.get_category_display()

    def close(self):
        self.status = self.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at', 'updated_at'])

    def reopen(self):
        self.status = self.OPEN
        self.closed_at = None
        self.save(update_fields=['status', 'closed_at', 'updated_at'])


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name='messages', verbose_name='Обращение')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='ticket_messages', verbose_name='Автор')
    body = models.TextField('Сообщение')
    is_staff = models.BooleanField('От поддержки', default=False)
    created_at = models.DateTimeField('Отправлено', auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} — {self.ticket}'

    def save(self, *args, **kwargs):
        if self.author_id and not self.pk:
            self.is_staff = self.author.is_staff
        super().save(*args, **kwargs)

        Ticket.objects.filter(pk=self.ticket_id).update(updated_at=timezone.now())

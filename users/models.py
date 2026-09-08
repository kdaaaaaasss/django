from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
\
\
\
\
\
\


    TENANT = 'tenant'
    LANDLORD = 'landlord'
    ROLE_CHOICES = [
        (TENANT, 'Арендатор'),
        (LANDLORD, 'Арендодатель / продавец'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь',
    )
    role = models.CharField(
        'Роль',
        max_length=16,
        choices=ROLE_CHOICES,
        default=TENANT,
    )
    phone = models.CharField('Телефон', max_length=32, blank=True)
    about = models.TextField('О себе', blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True, null=True)
    is_blocked = models.BooleanField('Заблокирован', default=False)
    email_verified = models.BooleanField('Email подтверждён', default=False)
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'{self.user.username} — {self.get_role_display()}'

    @property
    def is_landlord(self):
        return self.role == self.LANDLORD

    @property
    def initials(self):
        return (self.user.username or '?')[:1].upper()

    def make_landlord(self):
        if self.role != self.LANDLORD:
            self.role = self.LANDLORD
            self.save(update_fields=['role'])

    def block(self):
        self.is_blocked = True
        self.save(update_fields=['is_blocked'])
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])

    def unblock(self):
        self.is_blocked = False
        self.save(update_fields=['is_blocked'])
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)

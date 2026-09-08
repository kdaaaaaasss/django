\
\
\
\

from django.core.management.base import BaseCommand
from django.utils import timezone

from housing.models import Booking
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Помечает завершёнными брони, у которых прошла дата выезда'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Только показать, ничего не менять')

    def handle(self, *args, **options):
        today = timezone.localdate()
        qs = Booking.objects.filter(status=Booking.CONFIRMED, check_out__lte=today)
        total = qs.count()

        if options['dry_run']:
            for b in qs:
                self.stdout.write(f'  [dry-run] #{b.pk} {b.housing} → completed')
            self.stdout.write(self.style.WARNING(f'Будет завершено: {total}'))
            return

        for b in qs.select_related('housing', 'guest'):
            b.complete()
            Notification.push(
                b.guest,
                f'Поездка «{b.housing.title}» завершена — оставьте отзыв',
                url='/dashboard/reviews/', kind=Notification.REVIEW)

        self.stdout.write(self.style.SUCCESS(f'Завершено броней: {total}'))

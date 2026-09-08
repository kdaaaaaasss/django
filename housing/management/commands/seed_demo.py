\
\
\
\

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from housing.models import Amenity, Booking, Housing
from notifications.models import Notification
from reviews.models import Review
from support.models import Ticket, TicketMessage

AMENITIES = [
    ('wifi', 'Wi-Fi', '📶'), ('kitchen', 'Кухня', '🍳'),
    ('washer', 'Стиральная машина', '🧺'), ('parking', 'Парковка', '🅿'),
    ('tv', 'Телевизор', '📺'), ('ac', 'Кондиционер', '❄'),
    ('balcony', 'Балкон', '🌿'), ('elevator', 'Лифт', '🛗'),
    ('pets', 'Можно с животными', '🐾'), ('workspace', 'Рабочее место', '💻'),
]

HOSTS = [('maria', 'Мария'), ('petr', 'Пётр'), ('olga', 'Ольга')]
GUESTS = [('ivan', 'Иван'), ('sergey', 'Сергей'), ('anna', 'Анна')]

LISTINGS = [
    ('Студия у Кремля', 'ул. Ленина, 10', 2500, 1, 2, 'studio', 0, True, 'approved'),
    ('Квартира на Почтовой', 'ул. Почтовая, 55', 2800, 2, 4, 'apartment', 1, True, 'approved'),
    ('Апартаменты у парка', 'ул. Горького, 15', 3200, 2, 4, 'apartments', 2, True, 'approved'),
    ('Современная квартира', 'ул. Татарская, 21', 2900, 2, 3, 'apartment', 0, False, 'approved'),
    ('Квартира рядом с вокзалом', 'пл. Димитрова, 1', 2400, 1, 2, 'apartment', 1, False, 'approved'),
    ('Дом за городом', 'с. Солотча, 3', 6000, 4, 8, 'house', 2, True, 'approved'),
    ('Светлая двушка на Есенина', 'ул. Есенина, 42', 3100, 2, 4, 'apartment', 0, False, 'approved'),
    ('Лофт в центре', 'ул. Свободы, 7', 4200, 1, 3, 'studio', 1, True, 'approved'),
    ('Уютная квартира у ЦПКиО', 'ул. Крупской, 19', 2600, 2, 4, 'apartment', 2, False, 'approved'),
    ('Апартаменты бизнес-класса', 'ул. Соборная, 2', 5500, 3, 6, 'apartments', 0, False, 'approved'),
    ('Комната в тихом районе', 'ул. Черновицкая, 8', 1200, 1, 1, 'room', 1, False, 'approved'),
    ('Коттедж с баней', 'п. Дядьково, 11', 8000, 5, 10, 'house', 2, False, 'approved'),
    ('Трёшка для семьи', 'ул. Новосёлов, 33', 3800, 3, 6, 'apartment', 0, False, 'approved'),
    ('Мансарда с видом', 'ул. Павлова, 4', 3400, 2, 3, 'apartments', 1, False, 'pending'),
    ('Квартира у ТЦ «Малина»', 'Московское ш., 5', 2200, 1, 2, 'studio', 2, False, 'pending'),
    ('Гараж на окраине', 'ул. Промышленная, 40', 500, 1, 1, 'room', 0, False, 'rejected'),
    ('Черновик: дом у реки', 'с. Заокское, 2', 5000, 3, 6, 'house', 1, False, 'draft'),
]

TEXTS = [
    'Просторное и чистое жильё с хорошим ремонтом. Рядом магазины, остановки и кафе. '
    'Быстрый заезд, вся техника исправна, постельное бельё и полотенца включены.',
    'Тихая квартира в спокойном районе. До центра 10 минут на транспорте. '
    'Есть всё для длительного проживания: кухня, стиральная машина, рабочее место.',
    'Светлые комнаты, панорамные окна и новая мебель. Во дворе бесплатная парковка. '
    'Подходит для командировок и отдыха с семьёй.',
]

REVIEW_TEXTS = [
    ('Отличное место, всё чисто и рядом с центром. Хозяин на связи, заезд без проблем.', 5),
    ('Просторно и тихо. Немного не хватило посуды, в остальном — супер.', 4),
    ('Всё соответствует описанию. Рекомендую, вернёмся ещё.', 5),
    ('Нормально за свои деньги, но слышно соседей.', 3),
    ('Уютно, тепло, хороший район. Спасибо хозяйке!', 5),
]


class Command(BaseCommand):
    help = 'Наполняет базу демонстрационными данными'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Удалить демо-данные перед созданием')

    def handle(self, *args, **options):
        rnd = random.Random(42)
        today = timezone.localdate()

        if options['flush']:
            Review.objects.all().delete()
            Booking.objects.all().delete()
            Housing.objects.all().delete()
            TicketMessage.objects.all().delete()
            Ticket.objects.all().delete()
            Notification.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()
            self.stdout.write(self.style.WARNING('Демо-данные удалены'))


        for i, (code, name, icon) in enumerate(AMENITIES):
            Amenity.objects.get_or_create(
                code=code, defaults={'name': name, 'icon': icon, 'order': i})
        amenities = list(Amenity.objects.all())


        def mkuser(username, first, landlord=False, staff=False):
            u, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com', 'first_name': first})
            if created:
                u.set_password('demo12345')
                u.is_staff = staff
                u.save()
            if landlord:
                u.profile.make_landlord()
            return u

        hosts = [mkuser(u, n, landlord=True) for u, n in HOSTS]
        guests = [mkuser(u, n) for u, n in GUESTS]
        support = mkuser('support1', 'Поддержка', staff=True)


        created_listings = 0
        for i, (title, addr, price, rooms, gcap, htype, host_i, feat, status) in enumerate(LISTINGS):
            obj, created = Housing.objects.get_or_create(title=title, defaults=dict(
                owner=hosts[host_i], address=addr, city='Рязань',
                price=Decimal(price), rooms=rooms, guests=gcap,
                housing_type=htype, deal_type=Housing.RENT,
                is_featured=feat, status=status,
                short_description=f'{rooms} комн. · до {gcap} гостей · {addr}',
                description=TEXTS[i % len(TEXTS)],
                area=rnd.randint(28, 120),
                rejection_reason=('Недостаточно фотографий и неполное описание.'
                                  if status == 'rejected' else ''),
            ))
            if created:
                obj.amenities.set(rnd.sample(amenities, rnd.randint(3, 7)))
                created_listings += 1


        for t, p, r in (('Двушка на продажу, Центр', 4900000, 2),
                        ('Дом на продажу, Солотча', 7800000, 4)):
            Housing.objects.get_or_create(title=t, defaults=dict(
                owner=hosts[0], address='Рязань', city='Рязань', price=Decimal(p),
                rooms=r, guests=r * 2, deal_type=Housing.SALE, status='approved',
                housing_type='house' if r > 3 else 'apartment',
                short_description='Продажа', description=TEXTS[0]))


        approved = list(Housing.objects.public().filter(deal_type=Housing.RENT))
        specs = [
            (0, -30, -27, 'completed'), (1, -20, -17, 'completed'),
            (2, -12, -9, 'completed'), (3, -6, -3, 'completed'),
            (4, 5, 8, 'confirmed'), (5, 14, 18, 'confirmed'),
            (6, 3, 6, 'pending'), (7, 10, 12, 'pending'),
            (8, -40, -38, 'cancelled'), (9, -8, -5, 'declined'),
        ]
        created_bookings = 0
        for idx, (hi, ci, co, status) in enumerate(specs):
            housing = approved[hi % len(approved)]
            guest = guests[idx % len(guests)]
            if housing.owner_id == guest.id:
                guest = guests[(idx + 1) % len(guests)]
            check_in = today + timedelta(days=ci)
            if Booking.objects.filter(housing=housing, guest=guest,
                                      check_in=check_in).exists():
                continue
            b = Booking(housing=housing, guest=guest, check_in=check_in,
                        check_out=today + timedelta(days=co),
                        guests=min(2, housing.guests), status=status,
                        message='Приедем вдвоём, заезд после 15:00.' if idx % 3 == 0 else '')
            b.total_price = b.calc_total()
            b.save()
            created_bookings += 1


        created_reviews = 0
        for i, b in enumerate(Booking.objects.filter(status=Booking.COMPLETED)):
            if hasattr(b, 'review'):
                continue
            text, rating = REVIEW_TEXTS[i % len(REVIEW_TEXTS)]
            Review.objects.create(
                booking=b, housing=b.housing, author=b.guest,
                rating=rating, text=text,
                status=Review.PUBLISHED if i % 4 != 3 else Review.PENDING,
                reply='Спасибо за отзыв! Ждём снова.' if i % 3 == 0 else '')
            created_reviews += 1


        ticket_specs = [
            ('Не приходит подтверждение брони', 'booking', 'open', 'high'),
            ('Как изменить цену в объявлении?', 'listing', 'pending', 'normal'),
            ('Двойное списание', 'payment', 'open', 'urgent'),
            ('Забыл пароль, почта не приходит', 'account', 'closed', 'normal'),
        ]
        created_tickets = 0
        for i, (subject, cat, status, prio) in enumerate(ticket_specs):
            if Ticket.objects.filter(subject=subject).exists():
                continue
            author = (guests + hosts)[i % (len(guests) + len(hosts))]
            t = Ticket.objects.create(user=author, subject=subject, category=cat,
                                      status=status, priority=prio,
                                      assigned_to=support if status != 'open' else None)
            TicketMessage.objects.create(
                ticket=t, author=author,
                body='Здравствуйте! Столкнулся с проблемой, помогите разобраться.')
            if status != 'open':
                TicketMessage.objects.create(
                    ticket=t, author=support,
                    body='Здравствуйте! Разбираемся, ответим в течение дня.')
            created_tickets += 1


        for host in hosts:
            Notification.objects.get_or_create(
                user=host, verb='Добро пожаловать в Рязань.Аренда!',
                defaults={'kind': Notification.SYSTEM, 'url': '/dashboard/'})

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Объявлений: +{created_listings} (всего {Housing.objects.count()}), '
            f'броней: +{created_bookings}, отзывов: +{created_reviews}, '
            f'тикетов: +{created_tickets}.'))
        self.stdout.write('Демо-логины: maria / petr / olga / ivan / sergey / anna / '
                          'support1 — пароль demo12345')

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from notifications.models import Notification

from .models import Booking, Housing


def make_user(username, landlord=False):
    u = User.objects.create_user(username, f'{username}@e.ru', 'pass12345')
    if landlord:
        u.profile.make_landlord()
    return u


def make_housing(owner, **kw):
    defaults = dict(title=f'Объект {owner.username}', price=Decimal('1000'),
                    rooms=2, guests=4, status=Housing.APPROVED, owner=owner)
    defaults.update(kw)
    return Housing.objects.create(**defaults)


class HousingModerationTests(TestCase):
    def setUp(self):
        self.host = make_user('host', landlord=True)
        self.staff = User.objects.create_user('mod', 'mod@e.ru', 'pass12345', is_staff=True)

    def test_new_listing_is_draft_and_not_public(self):
        h = make_housing(self.host, status=Housing.DRAFT)
        self.assertFalse(h.is_published)
        self.assertNotIn(h, Housing.objects.public())

    def test_submit_then_approve_makes_public(self):
        h = make_housing(self.host, status=Housing.DRAFT)
        h.submit_for_moderation()
        self.assertEqual(h.status, Housing.PENDING)
        self.assertIn(h, Housing.objects.pending())

        h.approve(by=self.staff)
        self.assertTrue(h.is_published)
        self.assertEqual(h.moderated_by, self.staff)
        self.assertIn(h, Housing.objects.public())

    def test_reject_keeps_reason_and_hides_listing(self):
        h = make_housing(self.host, status=Housing.PENDING)
        h.reject('Мало фото', by=self.staff)
        self.assertEqual(h.status, Housing.REJECTED)
        self.assertEqual(h.rejection_reason, 'Мало фото')
        self.assertNotIn(h, Housing.objects.public())


class BookingValidationTests(TestCase):
    def setUp(self):
        self.host = make_user('host2', landlord=True)
        self.guest = make_user('guest2')
        self.housing = make_housing(self.host, title='Тестовый объект', guests=4)
        self.today = timezone.localdate()

    def _booking(self, offset_in=1, offset_out=3, **kw):
        return Booking(housing=self.housing, guest=self.guest,
                       check_in=self.today + timedelta(days=offset_in),
                       check_out=self.today + timedelta(days=offset_out), **kw)

    def test_total_price_is_nights_times_price(self):
        b = self._booking(1, 4)
        b.save()
        self.assertEqual(b.nights, 3)
        self.assertEqual(b.total_price, Decimal('3000'))

    def test_checkout_must_be_after_checkin(self):
        with self.assertRaises(ValidationError):
            self._booking(3, 1).full_clean()

    def test_cannot_book_in_the_past(self):
        with self.assertRaises(ValidationError):
            self._booking(-5, -2).full_clean()

    def test_cannot_exceed_guest_capacity(self):
        with self.assertRaises(ValidationError):
            self._booking(guests=99).full_clean()

    def test_owner_cannot_book_own_listing(self):
        b = Booking(housing=self.housing, guest=self.host,
                    check_in=self.today + timedelta(days=1),
                    check_out=self.today + timedelta(days=2))
        with self.assertRaises(ValidationError):
            b.full_clean()

    def test_overlapping_confirmed_booking_is_rejected(self):
        first = self._booking(5, 10)
        first.save()
        first.confirm()

        other = make_user('guest3')
        clash = Booking(housing=self.housing, guest=other,
                        check_in=self.today + timedelta(days=7),
                        check_out=self.today + timedelta(days=12))
        with self.assertRaises(ValidationError):
            clash.full_clean()

    def test_pending_booking_does_not_block_dates(self):
        self._booking(5, 10).save()
        other = make_user('guest4')
        ok = Booking(housing=self.housing, guest=other,
                     check_in=self.today + timedelta(days=7),
                     check_out=self.today + timedelta(days=12))
        ok.full_clean()


class BookingFlowTests(TestCase):
    def setUp(self):
        self.host = make_user('flowhost', landlord=True)
        self.guest = make_user('flowguest')
        self.housing = make_housing(self.host, title='Объект для потока')
        self.today = timezone.localdate()
        self.client.force_login(self.guest)

    def test_guest_creates_booking_and_host_is_notified(self):
        resp = self.client.post(f'/catalog/{self.housing.pk}/book/', {
            'check_in': (self.today + timedelta(days=2)).isoformat(),
            'check_out': (self.today + timedelta(days=5)).isoformat(),
            'guests': 2, 'message': 'Приедем вдвоём',
        })
        self.assertRedirects(resp, '/dashboard/bookings/')

        booking = Booking.objects.get(housing=self.housing, guest=self.guest)
        self.assertEqual(booking.status, Booking.PENDING)
        self.assertEqual(booking.nights, 3)
        self.assertTrue(Notification.objects.filter(user=self.host).exists())

    def test_host_confirms_and_guest_is_notified(self):
        booking = Booking.objects.create(
            housing=self.housing, guest=self.guest,
            check_in=self.today + timedelta(days=2),
            check_out=self.today + timedelta(days=4))
        self.client.force_login(self.host)
        self.client.post(f'/booking/{booking.pk}/confirm/')

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.CONFIRMED)
        self.assertEqual(booking.decided_by, self.host)
        self.assertTrue(Notification.objects.filter(
            user=self.guest, verb__icontains='подтверждена').exists())

    def test_stranger_cannot_act_on_booking(self):
        booking = Booking.objects.create(
            housing=self.housing, guest=self.guest,
            check_in=self.today + timedelta(days=2),
            check_out=self.today + timedelta(days=4))
        self.client.force_login(make_user('stranger'))
        self.assertEqual(self.client.post(f'/booking/{booking.pk}/confirm/').status_code, 404)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.PENDING)


class MarkCompletedCommandTests(TestCase):
    def test_past_confirmed_bookings_become_completed(self):
        from django.core.management import call_command
        host = make_user('cmdhost', landlord=True)
        guest = make_user('cmdguest')
        housing = make_housing(host, title='Объект команды')
        today = timezone.localdate()

        past = Booking.objects.create(
            housing=housing, guest=guest, status=Booking.CONFIRMED,
            check_in=today - timedelta(days=5), check_out=today - timedelta(days=2))
        future = Booking.objects.create(
            housing=housing, guest=guest, status=Booking.CONFIRMED,
            check_in=today + timedelta(days=5), check_out=today + timedelta(days=8))

        call_command('mark_completed_bookings', verbosity=0)

        past.refresh_from_db(); future.refresh_from_db()
        self.assertEqual(past.status, Booking.COMPLETED)
        self.assertEqual(future.status, Booking.CONFIRMED)
        self.assertTrue(Notification.objects.filter(user=guest).exists())

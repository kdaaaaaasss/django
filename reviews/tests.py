from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from housing.models import Booking, Housing

from .models import Review


class ReviewGuardTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user('rhost', 'h@e.ru', 'pass12345')
        self.guest = User.objects.create_user('rguest', 'g@e.ru', 'pass12345')
        self.housing = Housing.objects.create(
            owner=self.host, title='Объект отзывов', price=Decimal('1000'),
            rooms=1, guests=2, status=Housing.APPROVED)
        today = timezone.localdate()
        self.booking = Booking.objects.create(
            housing=self.housing, guest=self.guest,
            check_in=today - timedelta(days=5), check_out=today - timedelta(days=2),
            status=Booking.COMPLETED)

    def test_review_on_unfinished_booking_is_rejected(self):
        self.booking.status = Booking.CONFIRMED
        self.booking.save()
        review = Review(booking=self.booking, author=self.guest, rating=5, text='ок')
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_review_by_other_user_is_rejected(self):
        stranger = User.objects.create_user('stranger2', 's@e.ru', 'pass12345')
        review = Review(booking=self.booking, author=stranger, rating=5, text='ок')
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_one_review_per_booking(self):
        Review.objects.create(booking=self.booking, author=self.guest, rating=5, text='раз')
        with self.assertRaises(Exception):
            Review.objects.create(booking=self.booking, author=self.guest,
                                  rating=4, text='два')


class RatingRecalcTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user('rhost2', 'h2@e.ru', 'pass12345')
        self.housing = Housing.objects.create(
            owner=self.host, title='Объект рейтинга', price=Decimal('1000'),
            rooms=1, guests=2, status=Housing.APPROVED)
        self.today = timezone.localdate()

    def _completed_booking(self, guest_name):
        guest = User.objects.create_user(guest_name, f'{guest_name}@e.ru', 'pass12345')
        return Booking.objects.create(
            housing=self.housing, guest=guest, status=Booking.COMPLETED,
            check_in=self.today - timedelta(days=6), check_out=self.today - timedelta(days=3))

    def test_pending_review_does_not_affect_rating(self):
        Review.objects.create(booking=self._completed_booking('g1'),
                              rating=5, text='ок', status=Review.PENDING)
        self.housing.refresh_from_db()
        self.assertEqual(self.housing.reviews_count, 0)
        self.assertEqual(float(self.housing.rating), 0)

    def test_published_reviews_average(self):
        r1 = Review.objects.create(booking=self._completed_booking('g2'),
                                   rating=5, text='отлично')
        r2 = Review.objects.create(booking=self._completed_booking('g3'),
                                   rating=4, text='хорошо')
        r1.publish()
        r2.publish()

        self.housing.refresh_from_db()
        self.assertEqual(self.housing.reviews_count, 2)
        self.assertEqual(float(self.housing.rating), 4.5)

    def test_rating_drops_when_review_deleted(self):
        r1 = Review.objects.create(booking=self._completed_booking('g4'), rating=5, text='a')
        r2 = Review.objects.create(booking=self._completed_booking('g5'), rating=3, text='b')
        r1.publish(); r2.publish()
        r2.delete()

        self.housing.refresh_from_db()
        self.assertEqual(self.housing.reviews_count, 1)
        self.assertEqual(float(self.housing.rating), 5.0)

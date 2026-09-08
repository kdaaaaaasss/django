from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from housing.models import Housing
from notifications.models import Notification


class CrmAccessTests(TestCase):
    URLS = ['/crm/', '/crm/moderation/', '/crm/listings/', '/crm/bookings/',
            '/crm/tickets/', '/crm/reviews/', '/crm/users/']

    def test_anonymous_is_redirected(self):
        for url in self.URLS:
            self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_regular_user_is_redirected(self):
        self.client.force_login(User.objects.create_user('plain', 'p@e.ru', 'pass12345'))
        for url in self.URLS:
            self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_staff_gets_access(self):
        self.client.force_login(
            User.objects.create_user('crmstaff', 'c@e.ru', 'pass12345', is_staff=True))
        for url in self.URLS:
            self.assertEqual(self.client.get(url).status_code, 200, url)


class ModerationActionTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('mod2', 'm@e.ru', 'pass12345', is_staff=True)
        self.host = User.objects.create_user('modhost', 'h@e.ru', 'pass12345')
        self.housing = Housing.objects.create(
            owner=self.host, title='На модерации', price=Decimal('1500'),
            rooms=2, guests=3, status=Housing.PENDING)
        self.client.force_login(self.staff)

    def test_approve_publishes_and_notifies_owner(self):
        self.client.post(f'/crm/moderation/{self.housing.pk}/approve/')
        self.housing.refresh_from_db()
        self.assertEqual(self.housing.status, Housing.APPROVED)
        self.assertEqual(self.housing.moderated_by, self.staff)
        self.assertTrue(Notification.objects.filter(
            user=self.host, verb__icontains='одобрено').exists())

    def test_reject_stores_reason_and_notifies(self):
        self.client.post(f'/crm/moderation/{self.housing.pk}/reject/',
                         {'reason': 'Недостаточно фотографий', 'comment': 'Добавьте 5 фото'})
        self.housing.refresh_from_db()
        self.assertEqual(self.housing.status, Housing.REJECTED)
        self.assertIn('Добавьте 5 фото', self.housing.rejection_reason)
        self.assertTrue(Notification.objects.filter(
            user=self.host, verb__icontains='отклонено').exists())

    def test_get_request_does_not_change_status(self):
        self.client.get(f'/crm/moderation/{self.housing.pk}/approve/')
        self.housing.refresh_from_db()
        self.assertEqual(self.housing.status, Housing.PENDING)

    def test_staff_cannot_block_themselves(self):
        self.client.post(f'/crm/users/{self.staff.pk}/block/')
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.profile.is_blocked)
        self.assertTrue(self.staff.is_active)

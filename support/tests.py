from django.contrib.auth.models import User
from django.test import TestCase

from .models import Ticket, TicketMessage


class TicketFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tuser', 't@e.ru', 'pass12345')
        self.staff = User.objects.create_user('tstaff', 's@e.ru', 'pass12345', is_staff=True)

    def test_user_creates_ticket_with_first_message(self):
        self.client.force_login(self.user)
        resp = self.client.post('/support/new/', {
            'subject': 'Не приходит письмо', 'category': 'account',
            'body': 'Регистрируюсь, письмо не приходит.'})
        ticket = Ticket.objects.get(user=self.user)
        self.assertRedirects(resp, f'/support/{ticket.pk}/')
        self.assertEqual(ticket.status, Ticket.OPEN)
        self.assertEqual(ticket.messages.count(), 1)
        self.assertFalse(ticket.messages.first().is_staff)

    def test_staff_reply_is_marked_as_staff(self):
        ticket = Ticket.objects.create(user=self.user, subject='Вопрос')
        msg = TicketMessage.objects.create(ticket=ticket, author=self.staff, body='Отвечаем')
        self.assertTrue(msg.is_staff)

    def test_user_cannot_open_foreign_ticket(self):
        other = User.objects.create_user('other', 'o@e.ru', 'pass12345')
        ticket = Ticket.objects.create(user=other, subject='Чужое')
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/support/{ticket.pk}/').status_code, 404)

    def test_staff_can_open_any_ticket(self):
        ticket = Ticket.objects.create(user=self.user, subject='Любое')
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(f'/support/{ticket.pk}/').status_code, 200)

    def test_closing_and_reopening(self):
        ticket = Ticket.objects.create(user=self.user, subject='Закрытие')
        ticket.close()
        self.assertEqual(ticket.status, Ticket.CLOSED)
        self.assertIsNotNone(ticket.closed_at)
        ticket.reopen()
        self.assertEqual(ticket.status, Ticket.OPEN)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from housing.views_dashboard import _ctx
from notifications.models import Notification

from .forms import TicketForm, TicketMessageForm
from .models import Ticket, TicketMessage


@login_required
def ticket_list(request):
    return render(request, 'support/list.html', _ctx(
        request, 'support', tickets=Ticket.objects.filter(user=request.user)))


@login_required
def ticket_new(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            TicketMessage.objects.create(ticket=ticket, author=request.user,
                                         body=form.cleaned_data['body'])
            messages.success(request, f'Обращение #{ticket.pk} создано. Ответим в течение дня.')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, 'support/new.html', _ctx(request, 'support', form=form))


@login_required
def ticket_detail(request, pk):
    qs = Ticket.objects.select_related('user', 'assigned_to')
    ticket = get_object_or_404(qs, pk=pk) if request.user.is_staff \
        else get_object_or_404(qs, pk=pk, user=request.user)

    if request.method == 'POST':
        form = TicketMessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.ticket = ticket
            msg.author = request.user
            msg.save()
            if ticket.status == Ticket.CLOSED:
                ticket.reopen()
            messages.success(request, 'Сообщение отправлено.')
            return redirect('ticket_detail', pk=pk)
    else:
        form = TicketMessageForm()

    return render(request, 'support/thread.html', _ctx(
        request, 'support', ticket=ticket, form=form,
        thread=ticket.messages.select_related('author')))


@login_required
def ticket_close(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    if request.method == 'POST':
        ticket.close()
        messages.success(request, 'Обращение закрыто. Спасибо!')
    return redirect('ticket_list')

from django import forms

from .models import Ticket, TicketMessage


class TicketForm(forms.ModelForm):
    body = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': 'Что произошло, что вы ожидали, номер брони или объявления'}),
        label='Описание')

    class Meta:
        model = Ticket
        fields = ('subject', 'category')
        labels = {'subject': 'Тема', 'category': 'Категория'}
        widgets = {'subject': forms.TextInput(attrs={'placeholder': 'Коротко о проблеме'})}


class TicketMessageForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ('body',)
        labels = {'body': 'Сообщение'}
        widgets = {'body': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ваше сообщение'})}


class TicketStaffForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('assigned_to', 'status', 'priority')
        labels = {'assigned_to': 'Исполнитель', 'status': 'Статус', 'priority': 'Приоритет'}

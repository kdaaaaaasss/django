from django import forms
from django.utils import timezone

from .models import Amenity, Booking, Housing


class HousingForm(forms.ModelForm):
    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(), required=False,
        widget=forms.CheckboxSelectMultiple, label='Удобства')

    class Meta:
        model = Housing
        fields = ('title', 'short_description', 'description', 'city', 'address',
                  'housing_type', 'deal_type', 'price', 'rooms', 'guests', 'area',
                  'image', 'amenities')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'short_description': forms.TextInput(),
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError('Цена должна быть больше нуля.')
        return price


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ('check_in', 'check_out', 'guests', 'message')
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date'}),
            'check_out': forms.DateInput(attrs={'type': 'date'}),
            'message': forms.Textarea(attrs={'rows': 3,
                                             'placeholder': 'Расскажите о цели поездки'}),
        }
        labels = {'check_in': 'Заезд', 'check_out': 'Выезд',
                  'guests': 'Гостей', 'message': 'Сообщение хозяину'}

    def __init__(self, *args, housing=None, guest=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.housing = housing
        self.guest = guest
        if housing:
            self.fields['guests'].widget.attrs.update({'min': 1, 'max': housing.guests})
        today = timezone.localdate().isoformat()
        self.fields['check_in'].widget.attrs['min'] = today
        self.fields['check_out'].widget.attrs['min'] = today

    def _post_clean(self):
        if self.housing:
            self.instance.housing = self.housing
        if self.guest:
            self.instance.guest = self.guest
        super()._post_clean()


class RejectForm(forms.Form):
    REASONS = [
        ('Недостаточно фотографий', 'Недостаточно фотографий'),
        ('Неполное или недостоверное описание', 'Неполное или недостоверное описание'),
        ('Некорректный адрес', 'Некорректный адрес'),
        ('Подозрение на мошенничество', 'Подозрение на мошенничество'),
        ('Другое', 'Другое'),
    ]
    reason = forms.ChoiceField(choices=REASONS, label='Причина отказа')
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}),
                              label='Комментарий автору')

    def full_reason(self):
        reason = self.cleaned_data['reason']
        comment = self.cleaned_data.get('comment', '').strip()
        return f'{reason}. {comment}' if comment else reason

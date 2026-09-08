from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(i, str(i)) for i in range(5, 0, -1)],
        coerce=int, widget=forms.RadioSelect, label='Ваша оценка')

    class Meta:
        model = Review
        fields = ('rating', 'text')
        widgets = {'text': forms.Textarea(
            attrs={'rows': 4, 'placeholder': 'Что понравилось, что можно улучшить?'})}
        labels = {'text': 'Комментарий'}


class ReviewReplyForm(forms.Form):
    reply = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}),
                            label='Ответ на отзыв')

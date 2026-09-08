from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(label='Email', required=True)
    phone = forms.CharField(label='Телефон', max_length=32, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()

            profile = user.profile
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('phone',)

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction

from core.forms import BootstrapFormMixin

from .models import User


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Login form accepting either email or username."""
    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'autocomplete': 'username',
            'placeholder': 'you@example.com or username',
        }),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )


class BaseRegistrationForm(BootstrapFormMixin, forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput, strip=False)
    role = None

    class Meta:
        model = User
        fields = ['username', 'email', 'phone']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if not email:
            raise forms.ValidationError('Email is required.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        if p1:
            temp = User(username=data.get('username', ''), email=data.get('email', ''))
            try:
                password_validation.validate_password(p1, temp)
            except forms.ValidationError as exc:
                self.add_error('password1', exc)
        return data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.role
        user.set_password(self.cleaned_data['password1'])
        user.save()
        self.create_profile(user)
        return user

    def create_profile(self, user):  # pragma: no cover
        raise NotImplementedError


class WorkerRegistrationForm(BaseRegistrationForm):
    full_name = forms.CharField(max_length=120)
    role = User.Role.WORKER

    def create_profile(self, user):
        from workers.models import WorkerProfile
        WorkerProfile.objects.create(user=user, full_name=self.cleaned_data['full_name'])


class EmployerRegistrationForm(BaseRegistrationForm):
    organisation_name = forms.CharField(max_length=150)
    role = User.Role.EMPLOYER

    def create_profile(self, user):
        from employers.models import EmployerProfile
        EmployerProfile.objects.create(user=user, organisation_name=self.cleaned_data['organisation_name'])

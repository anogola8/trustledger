from django import forms

from core.forms import BootstrapFormMixin


class CodeForm(BootstrapFormMixin, forms.Form):
    code = forms.CharField(max_length=30, label='Verification code', widget=forms.TextInput(attrs={'placeholder': 'TL-XXXXX-XXXXX', 'autofocus': True}))

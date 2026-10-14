from django import forms

from core.forms import BootstrapFormMixin

from .models import Dispute


class DisputeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Dispute
        fields = ['reason', 'evidence']
        widgets = {'reason': forms.Textarea(attrs={'rows': 4})}


class ResolveForm(BootstrapFormMixin, forms.Form):
    decision = forms.ChoiceField(choices=[('uphold', 'Uphold the attestation'), ('revoke', 'Revoke the attestation')])
    note = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), max_length=1000)

from django import forms

from core.forms import BootstrapFormMixin

from .models import EmployerProfile, EmployerRating

SCORES = [(i, str(i)) for i in range(1, 6)]


class EmployerProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ['organisation_name', 'org_type', 'registration_number', 'description', 'location']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class RatingForm(BootstrapFormMixin, forms.ModelForm):
    score = forms.TypedChoiceField(choices=SCORES, coerce=int, label='Overall (1-5)')
    punctuality = forms.TypedChoiceField(choices=SCORES, coerce=int, initial=3)
    quality = forms.TypedChoiceField(choices=SCORES, coerce=int, initial=3, label='Quality of work')
    honesty = forms.TypedChoiceField(choices=SCORES, coerce=int, initial=3)

    class Meta:
        model = EmployerRating
        fields = ['score', 'punctuality', 'quality', 'honesty', 'comment']


class VerifyWorkerForm(BootstrapFormMixin, forms.Form):
    worker_code = forms.CharField(label='Worker profile code or link', max_length=200,
                                  help_text='The code at the end of the worker\'s profile link, e.g. amina-w-1a2b3c')

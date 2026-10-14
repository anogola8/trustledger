import datetime

from django import forms

from core.forms import BootstrapFormMixin, DateInput
from workers.models import WorkerProfile


class IssueAttestationForm(BootstrapFormMixin, forms.Form):
    worker_code = forms.CharField(label='Worker profile code', max_length=60,
                                  help_text='The code at the end of the worker\'s profile link (ask the worker to share it).')
    role_title = forms.CharField(max_length=120, label='Role / job title')
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False, max_length=1000,
                                  label='What did the worker do?')
    start_date = forms.DateField(widget=DateInput())
    end_date = forms.DateField(widget=DateInput(), required=False, help_text='Leave empty if ongoing')

    def clean_worker_code(self):
        code = self.cleaned_data['worker_code'].strip().rstrip('/').split('/')[-1]
        try:
            self.worker = WorkerProfile.objects.get(slug=code, user__is_active=True)
        except WorkerProfile.DoesNotExist:
            raise forms.ValidationError('No worker found with that code.')
        return code

    def clean(self):
        data = super().clean()
        s, e = data.get('start_date'), data.get('end_date')
        today = datetime.date.today()
        if s and s > today:
            self.add_error('start_date', 'Start date cannot be in the future.')
        if e and e > today:
            self.add_error('end_date', 'End date cannot be in the future.')
        if s and e and e < s:
            self.add_error('end_date', 'End date cannot be before the start date.')
        return data


class ReasonForm(BootstrapFormMixin, forms.Form):
    reason = forms.CharField(max_length=300, widget=forms.Textarea(attrs={'rows': 3}))

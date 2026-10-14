from django import forms

from core.forms import BootstrapFormMixin, DateInput

from .models import Certificate, Skill, WorkerProfile, WorkExperience


class WorkerProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = WorkerProfile
        fields = ['full_name', 'headline', 'bio', 'location', 'photo', 'show_skills', 'show_certificates']
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}


class SkillForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'level', 'years']

    def __init__(self, *args, worker=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.worker = worker

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if self.worker and self.worker.skills.filter(name__iexact=name).exists():
            raise forms.ValidationError('You already listed this skill.')
        return name


class CertificateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['title', 'issuing_body', 'year', 'file']


class ExperienceForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = WorkExperience
        fields = ['employer_name', 'role_title', 'start_date', 'end_date', 'description']
        widgets = {'start_date': DateInput(), 'end_date': DateInput(), 'description': forms.Textarea(attrs={'rows': 3})}

    def clean(self):
        data = super().clean()
        s, e = data.get('start_date'), data.get('end_date')
        if s and e and e < s:
            self.add_error('end_date', 'End date cannot be before the start date.')
        return data

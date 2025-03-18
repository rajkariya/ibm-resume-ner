from django import forms
from .models import JobApplication, JobPosting

class JobPostingForm(forms.ModelForm):
    class Meta:
        model = JobPosting
        fields = ['title', 'description', 'expires_at']
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }

class JobApplicationForm(forms.ModelForm):
    resume = forms.FileField()

    class Meta:
        model = JobApplication
        fields = ['first_name', 'last_name', 'email', 'phone']
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    # Additional fields can be added here if needed
    # For example, to allow users to update their email:
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ['bio', 'location', 'birth_date']  # Add other fields as needed

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        user = self.instance.user
        user.email = self.cleaned_data['email']
        user.save()

        profile = super(UserProfileForm, self).save(commit=False)
        if commit:
            profile.save()
        return profile

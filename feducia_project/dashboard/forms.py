from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User

        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-input'})
from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

User = get_user_model()

AVATAR_EXTENSIONS = ("jpg", "jpeg", "png", "gif", "webp")
MAX_AVATAR_SIZE = 5 * 1024 * 1024


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User

        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-input'})

    def clean_email(self):
        email = self.cleaned_data['email']
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class AvatarForm(forms.Form):
    avatar = forms.ImageField(validators=[FileExtensionValidator(AVATAR_EXTENSIONS)])

    def clean_avatar(self):
        avatar = self.cleaned_data['avatar']
        if avatar.size > MAX_AVATAR_SIZE:
            raise forms.ValidationError("The photo must be smaller than 5 MB.")
        return avatar

from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({
                "class": "form-control",
                "placeholder": field.label,  # floating label requires placeholder
            })

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email already registered")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()

        user.role = User.Role.USER
        user.must_change_password = False
        user.is_verified_publisher = False
        user.is_sponsored_oss = False

        if commit:
            user.save()
        return user


class EditProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": ""
        })
    )

    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": ""
        })
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name")


class ChangeEmailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email"]

        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"})
        }


class ChangePasswordForm(PasswordChangeForm):

    old_password = forms.CharField(
        label="Current password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter current password"
        })
    )

    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter new password"
        })
    )

    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm new password"
        })
    )


class RequestEmailChangeForm(forms.Form):
    old_email = forms.EmailField(
        label="Current email",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    new_email = forms.EmailField(
        label="New email",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "id": "id_password",
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        old_email = cleaned_data.get("old_email")
        new_email = cleaned_data.get("new_email")

        if old_email and new_email and old_email == new_email:
            raise forms.ValidationError(
                "New email must be different from current email."
            )

        return cleaned_data

    def clean_old_email(self):
        old_email = self.cleaned_data["old_email"].lower()
        if old_email != self.user.email:
            raise forms.ValidationError("Current email is incorrect.")
        return old_email

    def clean_new_email(self):
        email = self.cleaned_data["new_email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return password


class ConfirmEmailChangeForm(forms.Form):
    code = forms.CharField(
        label="Verification code",
        max_length=6,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

from django import forms
from .models import Repository, Tag
import re


class RepositoryForm(forms.ModelForm):
    initial_tag = forms.CharField(
        max_length=255,
        initial="latest",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "e.g., latest, v1.0.0"}
        ),
        help_text="Initial tag name for the repository",
    )

    class Meta:
        model = Repository
        fields = ["name", "description", "visibility", "is_official"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter repository name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "A short description of your repository",
                }
            ),
            "visibility": forms.Select(attrs={"class": "form-select"}),
            "is_official": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_is_official(self):
        is_official = self.cleaned_data.get("is_official")

        if is_official and self.request and not self.request.user.is_admin:
            raise forms.ValidationError(
                "Only admin users can create official repositories."
            )

        if self.instance.pk:
            was_official = self.instance.is_official

            # Prevent downgrade: official → personal
            if was_official and not is_official:
                raise forms.ValidationError(
                    "Cannot convert official repository back to personal. "
                    "Delete and recreate if needed."
                )

        return is_official

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        initial_tag = cleaned_data.get("initial_tag")
        is_official = cleaned_data.get("is_official", False)
        visibility = cleaned_data.get("visibility")

        if name:
            name = name.strip()
            cleaned_data["name"] = name

        if initial_tag:
            initial_tag = initial_tag.strip()
            cleaned_data["initial_tag"] = initial_tag

        if not name:
            raise forms.ValidationError({"name": "Repository name is required."})

        if not self.instance.pk and not initial_tag:
            raise forms.ValidationError({"initial_tag": "Initial tag is required."})

        if is_official and visibility == Repository.VisibilityChoices.PRIVATE:
            raise forms.ValidationError({"is_official": "Official repositories must be public."})

        if self.instance.pk:
            if is_official:
                duplicates = Repository.objects.exclude(pk=self.instance.pk).filter(
                    name=name, is_official=True
                )
                if duplicates.exists():
                    self.add_error(
                        "name", "Official repository with this name already exists."
                    )
            else:
                duplicates = Repository.objects.exclude(pk=self.instance.pk).filter(
                    name=name, is_official=False, owner=self.instance.owner
                )
                if duplicates.exists():
                    self.add_error(
                        "name", "You already have a repository with this name."
                    )

        else:
            if not self.request:
                return cleaned_data

            duplicates = Repository.objects.filter(name=name)
            if duplicates.exists():
                self.add_error(
                    "name", "You already have a repository with this name."
                )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["name"].disabled = True
            self.fields["name"].help_text = "Repository name cannot be changed"

            if self.instance.is_official:
                self.fields["is_official"].disabled = True
                self.fields["is_official"].help_text = (
                    "Official repositories cannot be converted back to personal"
                )


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "digest"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "v1.0.0, latest, dev"}
            ),
            "digest": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "sha256:7da81a8..."}
            ),
        }
        help_texts = {
            "name": "Tag name (e.g., v1.0.0, latest)",
            "digest": "SHA256 digest of the image",
            "size": "Image size in bytes",
        }

    def clean_name(self):
        """Validate tag name format"""
        name = self.cleaned_data.get("name")

        if not re.match(r"^[a-zA-Z0-9._-]+$", name):
            raise forms.ValidationError(
                "Tag name can only contain letters, "
                "numbers, dots, hyphens, and underscores."
            )

        return name

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["name"].disabled = True
            self.fields["digest"].disabled = True

from django import forms
from .models import Repository


class RepositoryForm(forms.ModelForm):
    class Meta:
        model = Repository
        fields = ["name", "description", "visibility"]
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
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if self.instance.pk:
            return name

        if (
            self.request
            and Repository.objects.filter(owner=self.request.user, name=name).exists()
        ):
            raise forms.ValidationError("Repository with this name already exists!")

        return name

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["name"].disabled = True
            self.fields["name"].help_text = "Repository name cannot be changed"

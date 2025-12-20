from django import forms
from .models import Repository, Tag
import re


class RepositoryForm(forms.ModelForm):
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
        is_official = self.cleaned_data.get('is_official')
        
        if is_official and self.request and not self.request.user.is_staff:
            raise forms.ValidationError(
                "Only staff users can create official repositories."
            )
        
        return is_official

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        is_official = cleaned_data.get('is_official', False)
        
        if not name:
            return cleaned_data
        
        if self.instance.pk:
            if is_official:
                duplicates = Repository.objects.exclude(pk=self.instance.pk).filter(
                    name=name, 
                    is_official=True
                )
                if duplicates.exists():
                    self.add_error('name', 'Official repository with this name already exists.')
            else:
                duplicates = Repository.objects.exclude(pk=self.instance.pk).filter(
                    name=name, 
                    is_official=False, 
                    owner=self.instance.owner
                )
                if duplicates.exists():
                    self.add_error('name', 'You already have a repository with this name.')
        
        else:
            if not self.request:
                return cleaned_data
            
            if is_official:
                duplicates = Repository.objects.filter(name=name, is_official=True)
                if duplicates.exists():
                    self.add_error('name', 'Official repository with this name already exists.')
            else:
                duplicates = Repository.objects.filter(
                    name=name, 
                    is_official=False, 
                    owner=self.request.user
                )
                if duplicates.exists():
                    self.add_error('name', 'You already have a repository with this name.')
        
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["name"].disabled = True
            self.fields["name"].help_text = "Repository name cannot be changed"

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'digest', 'size']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'v1.0.0, latest, dev'
            }),
            'digest': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'sha256:abc123...'
            }),
            'size': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Size in bytes'
            }),
        }
        help_texts = {
            'name': 'Tag name (e.g., v1.0.0, latest)',
            'digest': 'SHA256 digest of the image',
            'size': 'Image size in bytes',
        }

    def clean_name(self):
        """Validate tag name format"""
        name = self.cleaned_data.get('name')
        
        if not re.match(r'^[a-zA-Z0-9._-]+$', name):
            raise forms.ValidationError(
                'Tag name can only contain letters, numbers, dots, hyphens, and underscores.'
            )
        
        return name
    
    def clean_digest(self):
        """Validate digest format"""
        digest = self.cleaned_data.get('digest')
        
        if not digest.startswith('sha256:'):
            raise forms.ValidationError('Digest must start with "sha256:"')
        
        if not re.match(r'^sha256:[a-f0-9]{64}$', digest):
            raise forms.ValidationError(
                'Invalid digest format. Must be sha256: followed by 64 hexadecimal characters.'
            )
        
        return digest

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["name"].disabled = True
            self.fields["name"].help_text = "Tag name cannot be changed"

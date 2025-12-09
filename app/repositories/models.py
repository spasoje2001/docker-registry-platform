from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class Repository(models.Model):
    class VisibilityChoices(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        PRIVATE = "PRIVATE", "Private"

    name_validator = RegexValidator(
        regex=r"^[a-z0-9-]+$",
        message="Name is lowercase alphanumeric with hyphens, no spaces.",
    )
    name = models.CharField(
        max_length=150,
        validators=[name_validator],
        help_text="Lowercase alphanumeric with hyphens, no spaces",
    )
    visibility = models.CharField(
        choices=VisibilityChoices.choices,
        default=VisibilityChoices.PUBLIC,
    )
    is_official = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="repositories"
    )

    class Meta:
        verbose_name_plural = "repositories"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_owner_name")
        ]

    @property
    def full_name(self):
        if self.is_official:
            return self.name
        return f"{self.owner.username}/{self.name}"

    def __str__(self):
        return self.full_name

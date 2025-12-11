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
            models.UniqueConstraint(fields=["owner", "name"], name="unique_owner_name")
        ]

    @property
    def full_name(self):
        if self.is_official:
            return self.name
        return f"{self.owner.username}/{self.name}"

    def __str__(self):
        return self.full_name

class Tag(models.Model):
    name = models.CharField(max_length=100)
    digest = models.CharField(max_length=256)
    size = models.PositiveBigIntegerField()
    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="tags"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["repository", "name"], name="unique_repository_name")
        ]
        ordering = ["-created_at"]

    @property
    def full_tag_name(self):
        return f"{self.repository.full_name}:{self.name}"
    
    @property
    def size_display(self):
        """Human-readable size"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    @property
    def short_digest(self):
        """Returns truncated digest for display"""
        if not self.digest:
            return ""
        if self.digest.startswith('sha256:'):
            return f"sha256:{self.digest[7:19]}..."
        return f"{self.digest[:12]}..."

    def __str__(self):
        return self.full_tag_name

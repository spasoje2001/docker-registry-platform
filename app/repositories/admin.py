from django.contrib import admin
from .models import Repository


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "owner", "visibility", "is_official", "created_at")

    list_filter = ("visibility", "is_official", "created_at")

    search_fields = ("name", "owner__username", "description")

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Basic Information", {"fields": ("name", "description", "owner")}),
        ("Settings", {"fields": ("visibility", "is_official")}),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),  # Collapse sekcija
            },
        ),
    )

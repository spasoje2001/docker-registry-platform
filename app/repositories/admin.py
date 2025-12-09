from django.contrib import admin
from .models import Repository


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    # Koje kolone se prikazuju u listi
    list_display = ("full_name", "owner", "visibility", "is_official", "created_at")

    # Filteri sa desne strane
    list_filter = ("visibility", "is_official", "created_at")

    # Pretraga
    search_fields = ("name", "owner__username", "description")

    # Polja koja ne mogu da se menjaju
    readonly_fields = ("created_at", "updated_at")

    # Organizacija polja u grupe
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

"""URL configuration for repositories app."""

from django.urls import path
from . import views

app_name = "repositories"

urlpatterns = [
    path("", views.repository_list, name="list"),
    path("new/", views.repository_create, name="create"),
    path("<str:owner_username>/<str:name>/", views.repository_detail, name="detail"),
    path(
        "<str:owner_username>/<str:name>/edit/", views.repository_update, name="update"
    ),
    path(
        "<str:owner_username>/<str:name>/delete/",
        views.repository_delete,
        name="delete",
    ),
]

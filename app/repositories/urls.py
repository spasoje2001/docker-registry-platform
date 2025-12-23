"""URL configuration for repositories app."""

from django.urls import path
from . import views

app_name = "repositories"

urlpatterns = [
    path("", views.repository_list, name="list"),
    path("new/", views.repository_create, name="create"),
    path("<str:owner_username>/<str:name>/", views.repository_detail, name="detail"),
    path('<str:name>/', views.repository_detail_official, name='detail_official'),
    path(
        "<str:owner_username>/<str:name>/edit/",
        views.repository_update,
        name="update"
    ),
    path(
        "<str:name>/edit/official/",
        views.repository_update,
        name="update"
    ),
    path(
        "<str:owner_username>/<str:name>/delete/",
        views.repository_delete,
        name="delete",
    ),
    path(
        "<str:owner_username>/<str:name>/tags/new/",
        views.tag_create,
        name="tag_create"
    ),
    path(
        "<str:owner_username>/<str:name>/tags/<str:tag_name>/edit/",
        views.tag_update,
        name="tag_update"
    ),
    path(
        "<str:owner_username>/<str:name>/tags/<str:tag_name>/delete/<str:digest>", views.tag_delete, name="tag_delete"
    ),
]

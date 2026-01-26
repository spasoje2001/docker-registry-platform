"""URL configuration for repositories app."""

from django.urls import path
from . import views

app_name = "repositories"

urlpatterns = [
    # ===== GENERAL =====
    # path("", views.repository_list, name="list"),
    path("new/", views.repository_create, name="create"),
    path("<str:name>/star/", views.star_repository, name="star"),
    path('validate/', views.repository_validate, name='validate'),
    path('validate/tag/', views.tag_validate, name='tag_validate'),
    # ===== OFFICIAL REPOS =====
    path("<str:name>/", views.repository_detail_official, name="detail_official"),
    path("<str:name>/edit/", views.repository_update_official, name="update_official"),
    path(
        "<str:name>/delete/", views.repository_delete_official, name="delete_official"
    ),
    path("<str:name>/tags/new/", views.tag_create_official, name="tag_create_official"),
    path(
        "<str:name>/tags/<str:tag_name>/edit/",
        views.tag_detail_official,
        name="tag_detail_official",
    ),
    # ===== REGULAR REPOS =====
    path("<str:owner_username>/<str:name>/", views.repository_detail, name="detail"),
    path(
        "<str:owner_username>/<str:name>/edit/", views.repository_update, name="update"
    ),
    path(
        "<str:owner_username>/<str:name>/delete/",
        views.repository_delete,
        name="delete",
    ),
    path(
        "<str:owner_username>/<str:name>/tags/new/", views.tag_create, name="tag_create"
    ),
    path(
        "<str:owner_username>/<str:name>/tags/<str:tag_name>/edit/",
        views.tag_detail,
        name="tag_detail",
    ),
    path(
        "<str:owner_username>/<str:name>/tags/<str:tag_name>/delete/<str:digest>",
        views.tag_delete,
        name="tag_delete",
    ),
    path(
        "<str:name>/tags/<str:tag_name>/delete/<str:digest>",
        views.tag_delete_official,
        name="tag_delete_official",
    ),
]

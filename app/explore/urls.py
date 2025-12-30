"""URL configuration for explore app."""

from django.urls import path
from . import views

app_name = "explore"

urlpatterns = [
    path('', views.search, name='search'),
]

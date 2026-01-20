"""URL configuration for analytics app."""
from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path('', views.log_search, name='search'),
]

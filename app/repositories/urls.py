"""URL configuration for repositories app."""
from django.urls import path
from . import views

app_name = 'repositories'

urlpatterns = [
    path('', views.repository_list, name='respository_list'),
    # path('<str:owner>/<str:name>/', views.repository_detail, name='detail'),
]
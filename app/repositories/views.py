from django.shortcuts import render
from .models import Repository
from django.db import models

def repository_list(request):
    """List of all public repositories + user's private repositories"""
    user = request.user
    if user.is_authenticated:
        repositories = Repository.objects.filter(
            models.Q(visibility=Repository.VisibilityChoices.PUBLIC) |
            models.Q(owner=user)
        )
    else:
        repositories = Repository.objects.filter(
            visibility=Repository.VisibilityChoices.PUBLIC
        )
    return render(request, 'repository_list.html', {
        'repositories': repositories
        })

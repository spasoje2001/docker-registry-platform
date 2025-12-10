
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.db import models
from .models import Repository
from .forms import RepositoryForm


def repository_list(request):
    """List of all public repositories + user's private repositories"""
    user = request.user
    if user.is_authenticated:
        repositories = Repository.objects.filter(
            models.Q(visibility=Repository.VisibilityChoices.PUBLIC)
            | models.Q(owner=user)
        )
    else:
        repositories = Repository.objects.filter(
            visibility=Repository.VisibilityChoices.PUBLIC
        )
    return render(
        request, "repositories/repository_list.html", {"repositories": repositories}
    )


def repository_detail(request, owner_username, name):
    """Show repository details"""
    repo = get_object_or_404(Repository, owner__username=owner_username, name=name)

    if repo.visibility == Repository.VisibilityChoices.PRIVATE:
        if not request.user.is_authenticated or request.user != repo.owner:
            raise Http404("Repository not found")

    return render(request, "repositories/repository_detail.html", {"repository": repo})


@login_required
def repository_create(request):
    """Create new repository (only authenticated users)"""
    if request.method == "POST":
        form = RepositoryForm(request.POST)
        if form.is_valid():
            repo = form.save(commit=False)
            repo.owner = request.user
            repo.save()
            messages.success(
                request, f'Repository "{repo.full_name}" successfully created!'
            )
            return redirect("repositories:list")
    else:
        form = RepositoryForm()

    return render(
        request,
        "repositories/repository_form.html",
        {"form": form, "title": "New Repository"},
    )


@login_required
def repository_update(request, owner_username, name):
    """Edit repository (only owner)"""
    repo = get_object_or_404(Repository, owner__username=owner_username, name=name)

    if repo.owner != request.user:
        messages.error(request, "You cannot edit this repository.")
        return redirect(
            "repositories:detail", owner_username=repo.owner.username, name=repo.name
        )

    if request.method == "POST":
        form = RepositoryForm(request.POST, instance=repo)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'Repository "{repo.full_name}" updated successfully!'
            )
            return redirect(
                "repositories:detail",
                owner_username=repo.owner.username,
                name=repo.name,
            )
    else:
        form = RepositoryForm(instance=repo)

    return render(
        request,
        "repositories/repository_form.html",
        {"form": form, "repository": repo, "title": f"Edit {repo.full_name}"},
    )


@login_required
def repository_delete(request, owner_username, name):
    """Delete repository (only owner)"""
    repo = get_object_or_404(Repository, owner__username=owner_username, name=name)

    if repo.owner != request.user:
        messages.error(request, "You cannot delete this repository.")
        return redirect(
            "repositories:detail", owner_username=repo.owner.username, name=repo.name
        )

    if request.method == "POST":
        repo_name = repo.full_name
        repo.delete()
        messages.success(request, f'Repository "{repo_name}" deleted.')
        return redirect("repositories:list")

    return render(
        request, "repositories/repository_confirm_delete.html", {"repository": repo}
    )

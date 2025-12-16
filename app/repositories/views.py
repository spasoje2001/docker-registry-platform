from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.db import models
from .models import Repository, Tag
from .forms import RepositoryForm, TagForm


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
    repo = get_object_or_404(Repository, owner__username=owner_username, name=name, is_official=False)

    if repo.visibility == Repository.VisibilityChoices.PRIVATE:
        if not request.user.is_authenticated or request.user != repo.owner:
            raise Http404("Repository not found")

    tags = repo.tags.all()
    return render(request, "repositories/repository_detail.html", {"repository": repo, "tags": tags})


def repository_detail_official(request, name):
    """Show official repository details"""
    repo = get_object_or_404(Repository, name=name, is_official=True)
    tags = repo.tags.all()
    
    return render(request, "repositories/repository_detail.html", {
        "repository": repo, 
        "tags": tags
    })


@login_required
def repository_create(request):
    """Create new repository (only authenticated users)"""
    if request.method == "POST":
        form = RepositoryForm(request.POST, request=request)
        if form.is_valid():
            name = form.cleaned_data['name']
            is_official = form.cleaned_data.get('is_official', False)

            repo = form.save(commit=False)
            repo.owner = request.user
            if not request.user.is_staff and repo.is_official:
                form.add_error(
                    "is_official",
                    "Only staff users can create official repositories."
                )
                return render(request, "repositories/repository_form.html", {
                    "form": form,
                    "title": "New Repository"
                })
            repo.save()
            messages.success(
                request, f'Repository "{repo.full_name}" successfully created!'
            )
            return redirect("repositories:list")
    else:
        form = RepositoryForm(request=request)

    return render(
        request,
        "repositories/repository_form.html",
        {"form": form, "title": "New Repository"},
    )


@login_required
def repository_update(request, owner_username, name):
    """Edit repository (only owner)"""
    repo = None
    if owner_username == 'official':
        repo = get_object_or_404(Repository, name=name, is_official=True)
    else:
        repo = get_object_or_404(Repository, owner__username=owner_username, name=name, is_official=False)

    if repo.owner != request.user:
        messages.error(request, "You cannot edit this repository.")
        return redirect(
            "repositories:detail", owner_username=repo.owner.username, name=repo.name
        )

    if request.method == "POST":
        form = RepositoryForm(request.POST, instance=repo, request=request)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'Repository "{repo.full_name}" updated successfully!'
            )
            if repo.is_official:
                return redirect(
                    "repositories:detail_official",
                    name=repo.name,
                )
            else:
                return redirect(
                    "repositories:detail",
                    owner_username=repo.owner.username,
                    name=repo.name,
                )
    else:
        form = RepositoryForm(instance=repo, request=request)

    return render(
        request,
        "repositories/repository_form.html",
        {"form": form, "repository": repo, "title": f"Edit {repo.full_name}"},
    )


@login_required
def repository_delete(request, owner_username, name):
    """Delete repository (only owner)"""
    repo = None
    if owner_username == 'official':
        repo = get_object_or_404(Repository, name=name, is_official=True)
    else:
        repo = get_object_or_404(Repository, owner__username=owner_username, name=name, is_official=False)

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

@login_required
def tag_create(request, owner_username, name):
    """Create new tag for repository (only owner)"""
    repository = get_object_or_404(
        Repository,
        owner__username=owner_username,
        name=name
    )
    
    if repository.owner != request.user:
        messages.error(request, 'You cannot create tags for this repository.')
        return redirect('repositories:detail', owner_username=owner_username, name=name)
    
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            tag = form.save(commit=False)
            tag.repository = repository
            
            if Tag.objects.filter(repository=repository, name=tag.name).exists():
                form.add_error('name', f'Tag "{tag.name}" already exists for this repository.')
            else:
                tag.save()
                messages.success(
                    request,
                    f'Tag "{tag.name}" created successfully!'
                )
            if repository.is_official:
                return redirect('repositories:detail_official', name=repository.name)
            else:
                return redirect('repositories:detail', owner_username=owner_username, name=name)
    else:
        form = TagForm()
    
    return render(request, 'tags/tag_form.html', {
        'form': form,
        'repository': repository,
        'title': f'New Tag for {repository.full_name}'
    })

def tag_delete(request, owner_username, name, tag_name):
    """Delete tag from repository"""
    repo = get_object_or_404(Repository, owner__username=owner_username, name=name)

    if repo.owner != request.user:
        messages.error(request, "You cannot delete tags from this repository.")
        return redirect(
            "repositories:detail", owner_username=repo.owner.username, name=repo.name
        )

    tag = get_object_or_404(repo.tags, name=tag_name)

    if request.method == "POST":
        tag.delete()
        messages.success(request, f'Tag "{tag_name}" deleted from repository "{repo.full_name}".')
        if repo.is_official:
            return redirect(
                "repositories:detail_official", name=repo.name
            )
        else:
            return redirect(
                "repositories:detail", owner_username=repo.owner.username, name=repo.name
            )

    return render(
        request,
        "tags/tag_confirm_delete.html",
        {"repository": repo, "tag": tag},
    )

def tag_update(request, owner_username, name, tag_name):
    """Edit tag for repository (only owner)"""
    repository = get_object_or_404(
        Repository,
        owner__username=owner_username,
        name=name
    )
    
    if repository.owner != request.user:
        messages.error(request, 'You cannot edit tags for this repository.')
        return redirect('repositories:detail', owner_username=owner_username, name=name)
    
    tag = get_object_or_404(repository.tags, name=tag_name)
    
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Tag "{tag.name}" updated successfully!'
            )
        if repository.is_official:
            return redirect('repositories:detail_official', name=repository.name)
        else:
            return redirect('repositories:detail', owner_username=owner_username, name=name)
    else:
        form = TagForm(instance=tag)
    
    return render(request, 'tags/tag_form.html', {
        'form': form,
        'repository': repository,
        'tag': tag,
        'title': f'Edit Tag {tag.name} for {repository.full_name}'
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.db import models
from .models import Repository, Tag
from .forms import RepositoryForm, TagForm
from django.urls import reverse


def repository_list(request):
    """List of all public repositories + user's private repositories"""
    user = request.user
    if user.is_authenticated:
        repositories = Repository.objects.filter(
            models.Q(visibility=Repository.VisibilityChoices.PUBLIC)
            | models.Q(owner=user)
        ).order_by('-updated_at')
    else:
        repositories = Repository.objects.filter(
            visibility=Repository.VisibilityChoices.PUBLIC
        ).order_by('-updated_at')

    return render(
        request,
        "repositories/repository_list.html",
        {
            "repositories": repositories,
            "from_profile": False,
        }
    )


@login_required
def repository_create(request):
    """Create new repository (user repo or official repo if admin)"""
    from_profile = request.POST.get("from_profile")

    if request.method == "POST":
        form = RepositoryForm(request.POST, request=request)
        if form.is_valid():
            repo = form.save(commit=False)
            repo.owner = request.user

            # Safety check - should be caught by form validation, but double-check
            if repo.is_official and not request.user.is_admin():
                form.add_error(
                    'is_official',
                    'Only admins can create official repositories.'
                )
                return render(
                    request,
                    "repositories/repository_form.html",
                    {"form": form, "title": "New Repository"}
                )

            repo.save()

            messages.success(
                request,
                f'Repository "{repo.full_name}" successfully created!'
            )

            if from_profile:
                return redirect("accounts:profile")
            return redirect("repositories:list")

        # Form invalid
        if from_profile:
            request.session["repo_form_data"] = request.POST
            request.session["repo_form_errors"] = form.errors
            return redirect("accounts:profile")

        return render(
            request,
            "repositories/repository_form.html",
            {"form": form, "title": "New Repository"},
        )

    # GET request
    form = RepositoryForm(request=request)
    return render(
        request,
        "repositories/repository_form.html",
        {"form": form, "title": "New Repository"},
    )

def repository_detail(request, owner_username, name):
    """Show user repository details"""
    repo = get_object_or_404(
        Repository,
        owner__username=owner_username,
        name=name,
        is_official=False
    )

    # Privacy check
    if repo.visibility == Repository.VisibilityChoices.PRIVATE:
        if not request.user.is_authenticated or request.user != repo.owner:
            raise Http404("Repository not found")

    tags = repo.tags.all()
    return render(
        request,
        "repositories/repository_detail.html",
        {"repository": repo, "tags": tags}
    )


def repository_detail_official(request, name):
    """Show official repository details"""
    repo = get_object_or_404(Repository, name=name, is_official=True)
    tags = repo.tags.all()

    return render(
        request,
        "repositories/repository_detail.html",
        {"repository": repo, "tags": tags}
    )


@login_required
def repository_update(request, owner_username, name):
    """Edit user repository (only owner)"""
    repo = get_object_or_404(
        Repository,
        owner__username=owner_username,
        name=name,
        is_official=False
    )

    # Permission check
    if repo.owner != request.user:
        messages.error(request, "You cannot edit this repository.")
        return redirect(
            "repositories:detail",
            owner_username=repo.owner.username,
            name=repo.name,
        )

    from_profile = request.POST.get("from_profile")
    form = RepositoryForm(request.POST or None, instance=repo, request=request)

    if request.method == "POST" and form.is_valid():
        updated_repo = form.save()  # Save and get updated instance
        messages.success(
            request,
            f'Repository "{updated_repo.full_name}" updated successfully!'
        )

        # Check if repo became official after update
        if updated_repo.is_official:
            # Redirect to official detail page
            return redirect("repositories:detail_official", name=updated_repo.name)
        else:
            # Redirect to user detail page
            url = reverse(
                "repositories:detail",
                kwargs={
                    "owner_username": updated_repo.owner.username,
                    "name": updated_repo.name,
                },
            )
            if from_profile:
                url += "?from_profile=1"

            return redirect(url)

    return render(
        request,
        "repositories/repository_form.html",
        {
            "form": form,
            "repository": repo,
            "title": f"Edit {repo.full_name}",
        },
    )


@login_required
def repository_update_official(request, name):
    """Edit official repository (only admins)"""
    repo = get_object_or_404(Repository, name=name, is_official=True)

    # Permission check - only admins can edit official repos
    if not request.user.is_admin():
        messages.error(request, "Only admins can edit official repositories.")
        return redirect("repositories:detail_official", name=repo.name)

    from_profile = request.POST.get("from_profile")
    form = RepositoryForm(request.POST or None, instance=repo, request=request)

    if request.method == "POST" and form.is_valid():
        updated_repo = form.save()
        messages.success(
            request,
            f'Repository "{updated_repo.full_name}" updated successfully!'
        )

        # Check if repo is no longer official after update
        if not updated_repo.is_official:
            # Redirect to user detail page
            url = reverse(
                "repositories:detail",
                kwargs={
                    "owner_username": updated_repo.owner.username,
                    "name": updated_repo.name,
                },
            )
            if from_profile:
                url += "?from_profile=1"
            return redirect(url)
        else:
            # Still official, redirect to official detail
            return redirect("repositories:detail_official", name=updated_repo.name)

    return render(
        request,
        "repositories/repository_form.html",
        {
            "form": form,
            "repository": repo,
            "title": f"Edit {repo.full_name}",
        },
    )


@login_required
def repository_delete(request, owner_username, name):
    """Delete user repository (only owner)"""
    repo = get_object_or_404(
        Repository,
        owner__username=owner_username,
        name=name,
        is_official=False
    )

    # Permission check
    if repo.owner != request.user:
        messages.error(request, "You cannot delete this repository.")
        return redirect(
            "repositories:detail",
            owner_username=repo.owner.username,
            name=repo.name
        )

    from_profile = request.GET.get("from_profile")

    if request.method == "POST":
        repo_name = repo.full_name
        repo.delete()
        messages.success(request, f'Repository "{repo_name}" deleted.')

        if from_profile:
            return redirect("accounts:profile")
        return redirect("repositories:list")

    return render(
        request,
        "repositories/repository_confirm_delete.html",
        {"repository": repo}
    )


@login_required
def repository_delete_official(request, name):
    """Delete official repository (only admins)"""
    repo = get_object_or_404(Repository, name=name, is_official=True)

    # Permission check - only admins can delete official repos
    if not request.user.is_admin():
        messages.error(request, "Only admins can delete official repositories.")
        return redirect("repositories:detail_official", name=repo.name)

    from_profile = request.GET.get("from_profile")

    if request.method == "POST":
        repo_name = repo.full_name
        repo.delete()
        messages.success(request, f'Repository "{repo_name}" deleted.')

        if from_profile:
            return redirect("accounts:profile")
        return redirect("repositories:list")

    return render(
        request,
        "repositories/repository_confirm_delete.html",
        {"repository": repo}
    )


@login_required
def tag_create(request, owner_username, name):
    """Create new tag for user repository (only owner)"""
    repository = get_object_or_404(
        Repository,
        owner__username=owner_username,
        name=name,
        is_official=False
    )

    # Permission check
    if repository.owner != request.user:
        messages.error(request, 'You cannot create tags for this repository.')
        return redirect(
            'repositories:detail',
            owner_username=owner_username,
            name=name
        )

    from_profile = request.GET.get('from_profile') or request.POST.get('from_profile')

    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            tag = form.save(commit=False)
            tag.repository = repository

            # Check for duplicate tag name
            if Tag.objects.filter(repository=repository, name=tag.name).exists():
                form.add_error(
                    'name',
                    f'Tag "{tag.name}" already exists for this repository.'
                )
            else:
                tag.save()
                messages.success(
                    request,
                    f'Tag "{tag.name}" created successfully!'
                )

                url = reverse(
                    'repositories:detail',
                    kwargs={
                        'owner_username': owner_username,
                        'name': name
                    }
                )
                if from_profile:
                    url += '?from_profile=1'
                return redirect(url)
    else:
        form = TagForm()

    return render(
        request,
        'tags/tag_form.html',
        {
            'form': form,
            'repository': repository,
            'title': f'New Tag for {repository.full_name}',
            'from_profile': from_profile,
        }
    )


@login_required
def tag_create_official(request, name):
    """Create new tag for official repository (only admins)"""
    repository = get_object_or_404(Repository, name=name, is_official=True)

    # Permission check - only admins can create tags for official repos
    if not request.user.is_admin():
        messages.error(request, 'Only admins can create tags for official repositories.')
        return redirect('repositories:detail_official', name=name)

    from_profile = request.GET.get('from_profile') or request.POST.get('from_profile')

    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            tag = form.save(commit=False)
            tag.repository = repository

            # Check for duplicate tag name
            if Tag.objects.filter(repository=repository, name=tag.name).exists():
                form.add_error(
                    'name',
                    f'Tag "{tag.name}" already exists for this repository.'
                )
            else:
                tag.save()
                messages.success(
                    request,
                    f'Tag "{tag.name}" created successfully!'
                )
                return redirect('repositories:detail_official', name=repository.name)
    else:
        form = TagForm()

    return render(
        request,
        'tags/tag_form.html',
        {
            'form': form,
            'repository': repository,
            'title': f'New Tag for {repository.full_name}',
            'from_profile': from_profile,
        }
    )


@login_required
def tag_update(request, owner_username, name, tag_name):
    """Edit tag for user repository (only owner)"""
    repository = get_object_or_404(
        Repository,
        owner__username=owner_username,
        name=name,
        is_official=False
    )

    # Permission check
    if repository.owner != request.user:
        messages.error(request, 'You cannot edit tags for this repository.')
        return redirect(
            'repositories:detail',
            owner_username=owner_username,
            name=name
        )

    tag = get_object_or_404(repository.tags, name=tag_name)
    from_profile = request.GET.get('from_profile') or request.POST.get('from_profile')

    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Tag "{tag.name}" updated successfully!'
            )

            url = reverse(
                'repositories:detail',
                kwargs={
                    'owner_username': owner_username,
                    'name': name
                }
            )
            if from_profile:
                url += '?from_profile=1'
            return redirect(url)
    else:
        form = TagForm(instance=tag)

    return render(
        request,
        'tags/tag_form.html',
        {
            'form': form,
            'repository': repository,
            'tag': tag,
            'title': f'Edit Tag {tag.name} for {repository.full_name}',
            'from_profile': from_profile,
        }
    )


@login_required
def tag_update_official(request, name, tag_name):
    """Edit tag for official repository (only admins)"""
    repository = get_object_or_404(Repository, name=name, is_official=True)

    # Permission check - only admins can edit tags for official repos
    if not request.user.is_admin():
        messages.error(request, 'Only admins can edit tags for official repositories.')
        return redirect('repositories:detail_official', name=name)

    tag = get_object_or_404(repository.tags, name=tag_name)
    from_profile = request.GET.get('from_profile') or request.POST.get('from_profile')

    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Tag "{tag.name}" updated successfully!'
            )
            return redirect('repositories:detail_official', name=repository.name)
    else:
        form = TagForm(instance=tag)

    return render(
        request,
        'tags/tag_form.html',
        {
            'form': form,
            'repository': repository,
            'tag': tag,
            'title': f'Edit Tag {tag.name} for {repository.full_name}',
            'from_profile': from_profile,
        }
    )


@login_required
def tag_delete(request, owner_username, name, tag_name):
    """Delete tag from user repository (only owner)"""
    repo = get_object_or_404(
        Repository,
        owner__username=owner_username,
        name=name,
        is_official=False
    )

    # Permission check
    if repo.owner != request.user:
        messages.error(request, "You cannot delete tags from this repository.")
        return redirect(
            "repositories:detail",
            owner_username=repo.owner.username,
            name=repo.name,
        )

    tag = get_object_or_404(repo.tags, name=tag_name)
    from_profile = request.GET.get("from_profile") or request.POST.get("from_profile")

    if request.method == "POST":
        tag.delete()
        messages.success(
            request,
            f'Tag "{tag_name}" deleted from repository "{repo.full_name}".'
        )

        url = reverse(
            "repositories:detail",
            kwargs={
                "owner_username": repo.owner.username,
                "name": repo.name,
            },
        )
        if from_profile:
            url += "?from_profile=1"

        return redirect(url)

    return render(
        request,
        "tags/tag_confirm_delete.html",
        {
            "repository": repo,
            "tag": tag,
            "from_profile": from_profile,
        },
    )


@login_required
def tag_delete_official(request, name, tag_name):
    """Delete tag from official repository (only admins)"""
    repo = get_object_or_404(Repository, name=name, is_official=True)

    # Permission check - only admins can delete tags from official repos
    if not request.user.is_admin():
        messages.error(request, "Only admins can delete tags from official repositories.")
        return redirect("repositories:detail_official", name=repo.name)

    tag = get_object_or_404(repo.tags, name=tag_name)
    from_profile = request.GET.get("from_profile") or request.POST.get("from_profile")

    if request.method == "POST":
        tag.delete()
        messages.success(
            request,
            f'Tag "{tag_name}" deleted from repository "{repo.full_name}".'
        )
        return redirect("repositories:detail_official", name=repo.name)

    return render(
        request,
        "tags/tag_confirm_delete.html",
        {
            "repository": repo,
            "tag": tag,
            "from_profile": from_profile,
        },
    )

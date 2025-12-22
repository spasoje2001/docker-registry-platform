from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.db import models
from .models import Repository, Tag
from .forms import RepositoryForm, TagForm
from .services.repositories_service import RepositoryService


def repository_list(request):
    user = request.user
    service = RepositoryService()
    repositories = []

    if not service.health_check():
        messages.warning(request, "Registry is unavailable at this moment. Please try again later.")
    else:
        try:
            repositories = service.list_repositories(request.user)
        except Exception as e:
            messages.warning(request, "Error fetching repositories from registry.")
            
    return render(
        request, "repositories/repository_list.html", {"repositories": repositories}
    )


def repository_detail(request, owner_username, name):
    repo = get_object_or_404(Repository, owner__username=owner_username, name=name, is_official=False)

    if repo.visibility == Repository.VisibilityChoices.PRIVATE:
        if not request.user.is_authenticated or request.user != repo.owner:
            raise Http404("Repository not found")

    tags = repo.tags.all()
    return render(request, "repositories/repository_detail.html", {"repository": repo, "tags": tags})


def repository_detail_official(request, name):
    repo = get_object_or_404(Repository, name=name, is_official=True)
    tags = repo.tags.all()
    
    return render(request, "repositories/repository_detail.html", {
        "repository": repo, 
        "tags": tags
    })


@login_required
def repository_create(request):
    if request.method == "POST":
        form = RepositoryForm(request.POST, request=request)
        if form.is_valid():
            name = form.cleaned_data['name']
            is_official = form.cleaned_data.get('is_official', False)
            tag_name = form.cleaned_data.get('initial_tag', 'latest')

            print(f"JEBENI TAG NAME ----> {tag_name}")

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

            try:
                Tag.objects.create(name=tag_name, repository=repo)
            except Exception as e:
                form.add_error(None, f"Error creating initial tag: {e}")
                return render(request, "repositories/repository_form.html", {
                    "form": form,
                    "title": "New Repository"
                })

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
        {"form": form, "repository": repo, "title": f"Edit repository"},
    )


@login_required
def repository_delete(request, owner_username, name):
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
    repository = get_object_or_404(
        Repository,
        owner__username=owner_username,
        name=name
    )
    
    if repository.owner != request.user:
        messages.error(request, 'You cannot create tags for this repository.')
        return redirect('repositories:detail', owner_username=owner_username, name=name)
    
    print(f"DEBUG: Request method: {request.method}")
    
    if request.method == 'POST':
        print("DEBUG: POST request received")
        form = TagForm(request.POST)
        print(f"DEBUG: Form data: {request.POST}")
        print(f"DEBUG: Form is valid: {form.is_valid()}")
        
        if form.is_valid():
            print("DEBUG: Form is valid, processing...")
            tag = form.save(commit=False)
            tag.repository = repository
            
            tag_exists = Tag.objects.filter(repository=repository, name=tag.name).exists()
            print(f"DEBUG: Tag exists: {tag_exists}")
            
            if tag_exists:
                print("DEBUG: Tag already exists, adding error")
                form.add_error('name', f'Tag "{tag.name}" already exists for this repository.')
            else:
                print("DEBUG: Saving tag...")
                tag.save()
                print("DEBUG: Tag saved successfully!")
                messages.success(
                    request,
                    f'Tag "{tag.name}" created successfully!'
                )
                
                print("DEBUG: Redirecting...")
                if repository.is_official:
                    return redirect('repositories:detail_official', name=repository.name)
                else:
                    return redirect('repositories:detail', owner_username=owner_username, name=name)
        else:
            print(f"DEBUG: Form errors: {form.errors}")
    else:
        print("DEBUG: GET request, creating empty form")
        form = TagForm()
    
    print("DEBUG: Rendering template")
    return render(request, 'tags/tag_form.html', {
        'form': form,
        'repository': repository,
        'title': f'New Tag for {repository.full_name}'
    })

def tag_delete(request, owner_username, name, tag_name):
    service = RepositoryService()
    repo = get_object_or_404(Repository, owner__username=owner_username, name=name)

    if repo.owner != request.user:
        messages.error(request, "You cannot delete tags from this repository.")
        return redirect(
            "repositories:detail", owner_username=repo.owner.username, name=repo.name
        )

    tag = get_object_or_404(repo.tags, name=tag_name)
    
    registry_url = service.registry_client.registry_url
    commands = {
        'delete': f"curl -X DELETE {registry_url}/v2/{repo}/manifests/{tag.digest}",
        'gc': "docker exec registry bin/registry garbage-collect /etc/docker/registry/config.yml",
        'restart': "docker restart registry"
    }

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
        {"repository": repo, "tag": tag, "commands": commands},
    )

def tag_update(request, owner_username, name, tag_name):
    service = RepositoryService()
    repository = get_object_or_404(Repository, owner__username=owner_username, name=name)
    
    if repository.owner != request.user:
        messages.error(request, 'You cannot edit tags for this repository.')
        return redirect('repositories:detail', owner_username=owner_username, name=name)
    
    tag = get_object_or_404(repository.tags, name=tag_name)
    manifest = {}

    try:
        manifest = service.get_manifest(repository.name, tag.name)
    except Exception as e:
        messages.error(request, f'Error fetching manifest for tag "{tag.name}": {e}')
        manifest = {}
    
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tag "{tag.name}" updated successfully!')
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
        'manifest': manifest,
        'title': f'Details for {tag.name}'
    })

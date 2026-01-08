from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from .models import Repository, Tag
from .forms import RepositoryForm, TagForm
from .services.repositories_service import RepositoryService
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


def repository_list(request):
    service = RepositoryService()
    repositories = []

    if not service.health_check():
        messages.error(
            request, "Registry is unavailable at this moment. Please try again later."
        )
    else:
        try:
            repositories = service.list_repositories(request.user)
        except Exception:
            messages.error(request, "Error fetching repositories from registry.")

    return render(
        request,
        "repositories/repository_list.html",
        {
            "repositories": repositories,
            "from_profile": False,
        },
    )


@login_required
def repository_create(request):
    """Create new repository (user repo or official repo if admin)"""
    from_profile = request.POST.get("from_profile")

    if request.method == "POST":
        form = RepositoryForm(request.POST, request=request)
        if form.is_valid():
            form.cleaned_data["name"]
            form.cleaned_data.get("is_official", False)
            tag_name = form.cleaned_data.get("initial_tag", "latest")

            repo = form.save(commit=False)
            repo.owner = request.user

            # Safety check - should be caught by form validation, but double-check
            if repo.is_official and not request.user.is_admin:
                form.add_error(
                    "is_official", "Only admins can create official repositories."
                )
                if from_profile:
                    return redirect("accounts:profile")
                return render(
                    request,
                    "repositories/repository_form.html",
                    {"form": form, "title": "New Repository"},
                )

            repo.save()

            try:
                Tag.objects.create(name=tag_name, repository=repo)
            except Exception as e:
                form.add_error(None, f"Error creating initial tag: {e}")
                return render(
                    request,
                    "repositories/repository_form.html",
                    {"form": form, "title": "New Repository"},
                )

            messages.success(
                request, f'Repository "{repo.full_name}" successfully created!'
            )

            if from_profile:
                return redirect("accounts:profile")
            return redirect("repositories:list")

        # Form invalid
        if from_profile:
            request.session["form_data"] = request.POST
            request.session["form_errors"] = form.errors
            return redirect("accounts:profile")

        return render(
            request,
            "repositories/repository_form.html",
            {
                "form": form,
                "title": "New Repository",
                "from_profile": from_profile,
            },
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
        Repository, owner__username=owner_username, name=name, is_official=False
    )

    # Privacy check
    if repo.visibility == Repository.VisibilityChoices.PRIVATE:
        if not request.user.is_authenticated or request.user != repo.owner:
            raise Http404("Repository not found")

    from_profile = request.GET.get("from_profile")
    from_explore = request.GET.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")
    tag_q = request.GET.get('tag_q', '')
    tag_sort = request.GET.get('tag_sort', 'newest')

    tags = repo.tags.all()

    if tag_q:
        tags = tags.filter(name__icontains=tag_q)

    if tag_sort == "oldest":
        tags = tags.order_by('created_at')
    elif tag_sort == "name_asc":
        tags = tags.order_by('name')
    elif tag_sort == "name_desc":
        tags = tags.order_by('-name')
    elif tag_sort == "size":
        tags = tags.order_by('-size')
    else:
        tags = tags.order_by('-created_at')

    return render(
        request,
        "repositories/repository_detail.html",
        {
            "repository": repo,
            "tags": tags,
            "from_profile": from_profile,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
            "tag_q": tag_q,
            "tag_sort": tag_sort,
        }
    )


def repository_detail_official(request, name):
    """Show official repository details"""
    repo = get_object_or_404(Repository, name=name, is_official=True)
    tags = repo.tags.all()

    from_profile = request.GET.get("from_profile")
    from_explore = request.GET.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")
    tag_q = request.GET.get('tag_q', '')
    tag_sort = request.GET.get('tag_sort', 'newest')

    if tag_q:
        tags = tags.filter(name__icontains=tag_q)

    if tag_sort == "oldest":
        tags = tags.order_by('created_at')
    elif tag_sort == "name_asc":
        tags = tags.order_by('name')
    elif tag_sort == "name_desc":
        tags = tags.order_by('-name')
    elif tag_sort == "size":
        tags = tags.order_by('-size')
    else:
        tags = tags.order_by('-created_at')

    return render(
        request,
        "repositories/repository_detail.html",
        {
            "repository": repo,
            "tags": tags,
            "from_profile": from_profile,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
            "tag_q": tag_q,
            "tag_sort": tag_sort,
        }
    )


@login_required
def repository_update(request, owner_username, name):
    repo = None
    if owner_username == "official":
        repo = get_object_or_404(Repository, name=name, is_official=True)
    else:
        repo = get_object_or_404(
            Repository, owner__username=owner_username, name=name, is_official=False
        )

    # Permission check
    if repo.owner != request.user:
        messages.error(request, "You cannot edit this repository.")
        return redirect(
            "repositories:detail",
            owner_username=repo.owner.username,
            name=repo.name,
        )

    from_profile = request.GET.get("from_profile") or request.POST.get("from_profile")
    from_explore = request.GET.get("from_explore") or request.POST.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")
    form = RepositoryForm(request.POST or None, instance=repo, request=request)

    if request.method == "POST" and form.is_valid():
        updated_repo = form.save()
        messages.success(
            request, f'Repository "{updated_repo.full_name}" updated successfully!'
        )

        if updated_repo.is_official:
            url = reverse(
                "repositories:detail_official",
                kwargs={
                    "name": updated_repo.name,
                },
            )
            if from_explore:
                url += "?from_explore=1"
                if explore_queries:
                    url += "&" + explore_queries

            return redirect(url)
        else:
            url = reverse(
                "repositories:detail",
                kwargs={
                    "owner_username": updated_repo.owner.username,
                    "name": updated_repo.name,
                },
            )
            if from_profile:
                url += "?from_profile=1"
            elif from_explore:
                url += "?from_explore=1"
            if explore_queries:
                url += "&" + explore_queries

            return redirect(url)

    return render(
        request,
        "repositories/repository_form.html",
        {
            "form": form,
            "repository": repo,
            "title": f"Edit {repo.full_name}",
            "from_profile": from_profile,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
        },
    )


@login_required
def repository_update_official(request, name):
    """Edit official repository (only admins)"""
    repo = get_object_or_404(Repository, name=name, is_official=True)

    if not request.user.is_admin:
        messages.error(request, "Only admins can edit official repositories.")
        return redirect("repositories:detail_official", name=repo.name)

    from_profile = request.GET.get("from_profile") or request.POST.get("from_profile")
<<<<<<< HEAD
    from_explore = request.GET.get("from_explore") or request.POST.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&")
=======
    from_explore = request.GET.get('from_explore') or request.POST.get('from_explore')
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")
>>>>>>> 18d63a7 (feat: return path are good)
    form = RepositoryForm(request.POST or None, instance=repo, request=request)

    if request.method == "POST" and form.is_valid():
        updated_repo = form.save()
        messages.success(
            request, f'Repository "{updated_repo.full_name}" updated successfully!'
        )

        if not updated_repo.is_official:
            url = reverse(
                "repositories:detail",
                kwargs={
                    "owner_username": updated_repo.owner.username,
                    "name": updated_repo.name,
                },
            )

            if from_profile:
                url += "?from_profile=1"
            elif from_explore:
                url += "?from_explore=1"
            if explore_queries:
                url += "&" + explore_queries
            return redirect(url)
        else:
            url = reverse(
                "repositories:detail_official",
                kwargs={
                    "name": updated_repo.name,
                },
            )
            if from_explore:
                url += "?from_explore=1"
                if explore_queries:
                    url += "&" + explore_queries

            return redirect(url)

    return render(
        request,
        "repositories/repository_form.html",
        {
            "form": form,
            "repository": repo,
            "title": "Edit repository",
            "from_profile": from_profile,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
        },
    )


@login_required
def repository_delete(request, owner_username, name):
    repo = None
    if owner_username == "official":
        repo = get_object_or_404(Repository, name=name, is_official=True)
    else:
        repo = get_object_or_404(
            Repository, owner__username=owner_username, name=name, is_official=False
        )

    if repo.owner != request.user:
        messages.error(request, "You cannot delete this repository.")
        return redirect(
            "repositories:detail", owner_username=repo.owner.username, name=repo.name
        )

    commands = {
        "delete_repo": f"docker exec docker-registry-platform-registry-1 rm -rf /var/lib/registry/docker/registry/v2/repositories/{repo.name}",
        "gc": "docker exec docker-registry-platform-registry-1 bin/registry garbage-collect /etc/docker/registry/config.yml",
        "restart": "docker restart docker-registry-platform-registry-1",
    }

    from_profile = request.GET.get("from_profile")
    from_explore = request.GET.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")

    if request.method == "POST":
        repo_name = repo.full_name
        repo.delete()
        messages.success(request, f'Repository "{repo_name}" deleted.')

        if from_profile:
            return redirect("accounts:profile")
        elif from_explore:
            if explore_queries:
                url = reverse(
                    "explore:search",
                )
                url += "explore/?" + explore_queries
                return redirect(url)
            return redirect("explore:search")
        return redirect("repositories:list")

    return render(
        request,
        "repositories/repository_confirm_delete.html",
        {
            "repository": repo,
            "commands": commands,
            "from_profile": from_profile,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
        },
    )


@login_required
def repository_delete_official(request, name):
    """Delete official repository (only admins)"""
    repo = get_object_or_404(Repository, name=name, is_official=True)

    # Permission check - only admins can delete official repos
    if not request.user.is_admin:
        messages.error(request, "Only admins can delete official repositories.")
        return redirect("repositories:detail_official", name=repo.name)

    from_explore = request.GET.get("from_explore") or request.POST.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")

    commands = {
        "delete_repo": f"docker exec docker-registry-platform-registry-1 rm -rf /var/lib/registry/docker/registry/v2/repositories/{repo.name}",
        "gc": "docker exec docker-registry-platform-registry-1 bin/registry garbage-collect /etc/docker/registry/config.yml",
        "restart": "docker restart docker-registry-platform-registry-1",
    }

    if request.method == "POST":
        repo_name = repo.full_name
        repo.delete()
        messages.success(request, f'Repository "{repo_name}" deleted.')

        if from_explore:
            if explore_queries:
                url = reverse(
                    "explore:search",
                )
                url += "explore/?" + explore_queries
                return redirect(url)
            return redirect("explore:search")
        return redirect("repositories:list")

    return render(
        request,
        "repositories/repository_confirm_delete.html",
        {
            "repository": repo,
            "commands": commands,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
        },
    )


@login_required
def tag_create(request, owner_username, name):
    """Create new tag for user repository (only owner)"""
    repo = get_object_or_404(
        Repository, owner__username=owner_username, name=name, is_official=False
    )

    # Permission check
    if repo.owner != request.user:
        messages.error(request, "You cannot create tags for this repository.")
        return redirect("repositories:detail", owner_username=owner_username, name=name)

<<<<<<< HEAD
    from_profile = request.GET.get("from_profile") or request.POST.get("from_profile")
    from_explore = request.GET.get("from_explore") or request.POST.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&")
=======
    from_profile = request.GET.get('from_profile') or request.POST.get('from_profile')
    from_explore = request.GET.get('from_explore') or request.POST.get('from_explore')
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")
>>>>>>> 18d63a7 (feat: return path are good)

    if request.method == "POST":
        form = TagForm(request.POST)

        if form.is_valid():
            tag = form.save(commit=False)
            tag.repository = repo

            # Check for duplicate tag name
            if Tag.objects.filter(repository=repo, name=tag.name).exists():
                form.add_error(
                    "name", f'Tag "{tag.name}" already exists for this repository.'
                )
            else:
                tag.save()
                messages.success(request, f'Tag "{tag.name}" created successfully!')

                url = reverse(
                    "repositories:detail",
                    kwargs={"owner_username": owner_username, "name": name},
                )
                if from_profile:
                    url += "?from_profile=1"
                elif from_explore:
                    url += "?from_explore=1"
                if explore_queries:
                    url += "&" + explore_queries
                return redirect(url)
    else:
        form = TagForm()

    return render(
        request,
        "tags/tag_form.html",
        {
            "form": form,
            "repository": repo,
            "title": f"New Tag for {repo.full_name}",
            "from_profile": from_profile,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
        },
    )


@login_required
def tag_create_official(request, name):
    """Create new tag for official repository (only admins)"""
    repo = get_object_or_404(Repository, name=name, is_official=True)

    # Permission check - only admins can create tags for official repos
    if not request.user.is_admin:
        messages.error(
            request, "Only admins can create tags for official repositories."
        )
        return redirect("repositories:detail_official", name=name)

<<<<<<< HEAD
    from_explore = request.GET.get("from_explore") or request.POST.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&")
=======
    from_explore = request.GET.get('from_explore') or request.POST.get('from_explore')
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")
>>>>>>> 18d63a7 (feat: return path are good)

    if request.method == "POST":
        form = TagForm(request.POST)
        if form.is_valid():
            tag = form.save(commit=False)
            tag.repository = repo

            # Check for duplicate tag name
            if Tag.objects.filter(repository=repo, name=tag.name).exists():
                form.add_error(
                    "name", f'Tag "{tag.name}" already exists for this repository.'
                )
            else:
                tag.save()
                messages.success(
                    request,
                    f'Tag "{tag.name}" created successfully!'
                )
                url = reverse(
                    "repositories:detail_official",
                    kwargs={"name": name})
                if from_explore:
                    url += "?from_explore=1"
                    if explore_queries:
                        url += "&" + explore_queries
                return redirect(url)
    else:
        form = TagForm()

    return render(
        request,
        "tags/tag_form.html",
        {
            "form": form,
            "repository": repo,
            "title": f"New Tag for {repo.full_name}",
            "from_explore": from_explore,
            "explore_queries": explore_queries,
        },
    )


def tag_detail(request, owner_username, name, tag_name):
    repository = get_object_or_404(
        Repository, owner__username=owner_username, name=name
    )

    tag = get_object_or_404(repository.tags, name=tag_name)
<<<<<<< HEAD
    from_profile = request.GET.get("from_profile") or request.POST.get("from_profile")
    from_explore = request.GET.get("from_explore") or request.POST.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&")
=======
    from_profile = request.GET.get('from_profile') or request.POST.get('from_profile')
    from_explore = request.GET.get('from_explore') or request.POST.get('from_explore')
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")
>>>>>>> 18d63a7 (feat: return path are good)

    if request.method == "POST":
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tag "{tag.name}" updated successfully!')

            url = reverse(
                "repositories:detail", kwargs={"owner_username": owner_username, "name": name},
            )
            if from_profile:
                url += "?from_profile=1"
            elif from_explore:
                url += "?from_explore=1"
            if explore_queries:
                url += "&" + explore_queries
            return redirect(url)
    else:
        form = TagForm(instance=tag)

    return render(
        request,
        "tags/tag_form.html",
        {
            "form": form,
            "repository": repository,
            "tag": tag,
            "title": f"Details for {tag.name} from {repository.full_name}",
            "from_profile": from_profile,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
        },
    )


def tag_detail_official(request, name, tag_name):
    repository = get_object_or_404(Repository, name=name, is_official=True)

    tag = get_object_or_404(repository.tags, name=tag_name)
    from_profile = request.GET.get("from_profile") or request.POST.get("from_profile")
    from_explore = request.GET.get("from_explore") or request.POST.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&")

    if request.method == "POST":
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tag "{tag.name}" updated successfully!')

            url = reverse(
                "repositories:detail",
                kwargs={"owner_username": repository.owner.username, "name": name},
            )
            if from_profile:
                url += "?from_profile=1"
            elif from_explore:
                url += "?from_explore=1"
                if explore_queries:
                    url += "&" + explore_queries
            return redirect(url)
    else:
        form = TagForm(instance=tag)

    return render(
        request,
        "tags/tag_form.html",
        {
            "form": form,
            "repository": repository,
            "tag": tag,
            "title": f"Details for {tag.name} from {repository.full_name}",
            "from_profile": from_profile,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
        },
    )


@login_required
def tag_delete(request, owner_username, name, tag_name, digest):
    """Delete tag from user repository (only owner)"""
    service = RepositoryService()
    repo = get_object_or_404(Repository, owner__username=owner_username, name=name)

    if repo.owner != request.user:
        messages.error(request, "You cannot delete tags from this repository.")
        return redirect(
            "repositories:detail",
            owner_username=repo.owner.username,
            name=repo.name,
        )

    tag = get_object_or_404(repo.tags, name=tag_name)
    from_profile = request.GET.get("from_profile") or request.POST.get("from_profile")
    from_explore = request.GET.get("from_explore") or request.POST.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")

    commands = {
        "gc": "docker exec docker-registry-platform-registry-1 bin/registry garbage-collect /etc/docker/registry/config.yml",
        "restart": "docker restart docker-registry-platform-registry-1",
    }

    step = None
    deletion_success = False
    error_message = None

    if request.method == "POST":
        step = request.POST.get("step")

        if step == "1":
            try:
                if service.delete_manifest(repo.name, tag.digest):
                    tag.delete()
                    deletion_success = True
                else:
                    error_message = "Failed to delete manifest from registry."
            except Exception as e:
                logger.error(f"Error deleting tag: {e}")
                error_message = str(e)

            return render(
                request,
                "tags/tag_confirm_delete.html",
                {
                    "repository": repo,
                    "tag": tag,
                    "commands": commands,
                    "from_profile": from_profile,
                    "from_explore": from_explore,
                    "step": step,
                    "deletion_success": deletion_success,
                    "error_message": error_message,
                },
            )
<<<<<<< HEAD
=======
            if from_profile:
                url += "?from_profile=1"
            elif from_explore:
                url += "?from_explore=1"
            if explore_queries:
                url += "&" + explore_queries
            return redirect(url)
        else:
            url = reverse(
                "repositories:detail",
                kwargs={
                    "owner_username": repo.owner.username,
                    "name": repo.name,
                },
            )
            if from_profile:
                url += "?from_profile=1"
            elif from_explore:
                url += "?from_explore=1"
            if explore_queries:
                url += "&" + explore_queries
            return redirect(url)
>>>>>>> 18d63a7 (feat: return path are good)

    return render(
        request,
        "tags/tag_confirm_delete.html",
        {
            "repository": repo,
            "tag": tag,
            "commands": commands,
            "from_profile": from_profile,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
            "step": step,
            "deletion_success": deletion_success,
            "error_message": error_message,
        },
    )


@login_required
def tag_delete_official(request, name, tag_name, digest):
    """Delete tag from official repository (only admins)"""
    service = RepositoryService()
    repo = get_object_or_404(Repository, name=name, is_official=True)

    if not request.user.is_admin:
        messages.error(
            request, "Only admins can delete tags from official repositories."
        )
        return redirect("repositories:detail_official", name=repo.name)

    tag = get_object_or_404(repo.tags, name=tag_name)
<<<<<<< HEAD
    from_explore = request.GET.get("from_explore") or request.POST.get("from_explore")
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&")
=======
    from_explore = request.GET.get('from_explore') or request.POST.get('from_explore')
    explore_queries = request.GET.urlencode().replace("from_explore=1", "").lstrip("&").replace("from_profile=1", "").lstrip("&")
>>>>>>> 18d63a7 (feat: return path are good)

    commands = {
        "gc": "docker exec docker-registry-platform-registry-1 bin/registry garbage-collect /etc/docker/registry/config.yml",
        "restart": "docker restart docker-registry-platform-registry-1",
    }

    step = None
    deletion_success = False
    error_message = None

    if request.method == "POST":
<<<<<<< HEAD
        step = request.POST.get("step")

        if step == "1":
            try:
                if service.delete_manifest(repo.name, tag.digest):
                    tag.delete()
                    deletion_success = True
                else:
                    error_message = "Failed to delete manifest from registry."
            except Exception as e:
                logger.error(f"Error deleting tag: {e}")
                error_message = str(e)

            return render(
                request,
                "tags/tag_confirm_delete.html",
                {
                    "repository": repo,
                    "tag": tag,
                    "commands": commands,
                    "from_explore": from_explore,
                    "step": step,
                    "deletion_success": deletion_success,
                    "error_message": error_message,
                },
            )
=======
        tag.delete()
        messages.success(
            request,
            f'Tag "{tag_name}" deleted from repository "{repo.full_name}".'
        )
        url = reverse(
                'repositories:detail_official',
                kwargs={'name': name}
        )
        if from_explore:
            url += "?from_explore=1"
        if explore_queries:
            url += "&" + explore_queries
        return redirect(url)
>>>>>>> 18d63a7 (feat: return path are good)

    return render(
        request,
        "tags/tag_confirm_delete.html",
        {
            "repository": repo,
            "tag": tag,
            "commands": commands,
            "from_explore": from_explore,
            "explore_queries": explore_queries,
            "step": step,
            "deletion_success": deletion_success,
            "error_message": error_message,
        },
    )

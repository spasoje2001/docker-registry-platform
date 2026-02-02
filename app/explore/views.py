from django.shortcuts import render
from django.db.models import Q, Case, When, IntegerField
from django.core.paginator import Paginator
from django.contrib import messages

from repositories.services.repositories_service import RepositoryService


def search(request):
    service = RepositoryService()
    repositories = service.get_initial_repositories(False, None)

    if not service.health_check():
        messages.error(
            request, "Registry is unavailable at this moment. Please try again later."
        )
    else:
        try:
            repositories = service.list_repositories(request.user, False)
        except Exception:
            messages.error(request, "Error fetching repositories from registry.")
            repositories = service.get_initial_repositories(False, None)

    repositories = repositories.select_related("owner").order_by("-created_at")

    return render(
        request,
        "explore/explore.html",
        {
            "repositories": repositories,
            "from_explore": True,
        },
    )


def explore_repositories(request):
    query = request.GET.get("q", "").strip()
    active_filter = request.GET.get("filter", "")
    sort = request.GET.get("sort", "updated")
    explore_queries = request.GET.urlencode()

    service = RepositoryService()
    repositories = service.get_initial_repositories(False, None)

    if not service.health_check():
        messages.error(
            request, "Registry is unavailable at this moment. Please try again later."
        )
    else:
        try:
            repositories = service.list_repositories(request.user, False)
        except Exception:
            messages.error(request, "Error fetching repositories from registry.")
            repositories = service.get_initial_repositories(False, None)

    repositories = repositories.select_related("owner").order_by("-created_at")

    if active_filter == "official":
        repositories = repositories.filter(is_official=True)

    elif active_filter == "verified":
        repositories = repositories.filter(owner__is_verified_publisher=True)

    elif active_filter == "sponsored":
        repositories = repositories.filter(owner__is_sponsored_oss=True)

    if query:
        repositories = (
            repositories.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
            .order_by("-updated_at").order_by("-updated_at")
        )

    if sort == "name_asc":
        repositories = repositories.order_by("name")

    elif sort == "name_desc":
        repositories = repositories.order_by("-name")

    elif sort == "relevance":
        repositories = repositories.annotate(
                relevance=Case(
                    When(name__icontains=query, then=0),
                    When(description__icontains=query, then=1),
                    default=2,
                    output_field=IntegerField(),
                )
            ).order_by("relevance", "name")

    all_filters = 0

    if query:
        all_filters += 1

    if active_filter:
        all_filters += 1

    paginator = Paginator(repositories, 2)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if sort != "updated":
        all_filters += 1

    return render(
        request,
        "explore/explore.html",
        {
            "repositories": page_obj,
            "page_obj": page_obj,
            "query": query,
            "active_filter": active_filter,
            "sort": sort,
            "all_filters": all_filters,
            "from_explore": True,
            "explore_queries": explore_queries,
        },
    )

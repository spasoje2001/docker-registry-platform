from django.shortcuts import render
from django.db.models import Q, Case, When, IntegerField
from django.core.paginator import Paginator

from repositories.models import Repository


def search(request):
    repositories = (
        Repository.objects
        .filter(visibility="PUBLIC")
        .select_related("owner")
        .order_by("-created_at")
    )

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

    repositories = (
        Repository.objects
        .filter(visibility="PUBLIC")
        .order_by("-created_at")
    )

    if query:
        repositories = repositories.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).annotate(
            relevance=Case(
                When(name__icontains=query, then=0),
                When(description__icontains=query, then=1),
                default=2,
                output_field=IntegerField(),
            )
        ).order_by("relevance", "name")

    paginator = Paginator(repositories, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "explore/explore.html",
        {
            "repositories": page_obj,
            "page_obj": page_obj,
            "query": query,
            "from_explore": True,
        },
    )

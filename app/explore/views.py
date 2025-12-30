from django.shortcuts import render

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
        {"repositories": repositories},
    )
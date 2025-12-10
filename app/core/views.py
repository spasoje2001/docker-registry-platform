"""Core site-wide views."""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def home(request):
    """
    Landing page for Docker Registry Platform.
    """
    # Show landing page for everyone for now
    # Will add redirect logic when repositories app URLs are implemented
    return render(request, 'core/home.html')

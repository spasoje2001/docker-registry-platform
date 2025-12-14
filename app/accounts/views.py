from idlelib.debugobj_r import remote_object_tree_item

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm

User = get_user_model()


def admin_panel(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    if request.user.role not in ["admin", "super_admin"]:
        messages.warning(
            request,
            "You do not have permission to access this page."
        )
        return redirect("core:home")

    q = request.GET.get("q", "").strip()
    users = User.objects.filter(role=User.Role.USER).order_by("username")
    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(email__icontains=q)
        )
    return render(request, "accounts/admin_panel.html", {"users": users, "q": q})

def update_badges(request, user_id):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    if request.user.role not in ["admin", "super_admin"]:
        messages.error(request, "You do not have permission to do that.")
        return redirect("core:home")

    if request.method != "POST":
        return redirect("accounts:admin_panel")

    target = get_object_or_404(User, id=user_id)

    target.is_verified_publisher = "is_verified_publisher" in request.POST
    target.is_sponsored_oss = "is_sponsored_oss" in request.POST
    target.save(update_fields=["is_verified_publisher", "is_sponsored_oss"])

    messages.success(request, f"Badges updated for {target.username}.")

    return redirect(request.META.get("HTTP_REFERER", "accounts:admin_panel"))

def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:home")

    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            messages.success(
                request,
                "You have successfully logged in!"
            )

            if next_url:
                return redirect(next_url)
            return redirect("core:home")
        else:
            messages.error(
                request,
                "Invalid username or password. Please try again."
            )
    else:
        form = CustomAuthenticationForm(request)

    return render(
            request,
            "accounts/login.html",
            {"form": form, "next": next_url},
        )

def logout_view(request):
    logout(request)

    messages.success(
        request,
        "You have successfully logged out!"
    )
    return redirect("core:home")

def register(request):
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome, {user.username}! Your account has been created successfully."
            )

            return redirect("core:home")

    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


class CustomPasswordChangeView(auth_views.PasswordChangeView):
    """
    Custom password change view that clears must_change_password flag.

    Extends Django's built-in PasswordChangeView to add custom logic
    for clearing the must_change_password flag after successful password change.
    """

    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')

    def form_valid(self, form):
        """
        Clear must_change_password flag after successful password change.

        This is called when the form is valid and before the user is redirected.
        We override this method to set must_change_password=False.
        """
        response = super().form_valid(form)

        user = self.request.user
        if user.must_change_password:
            user.must_change_password = False
            user.save(update_fields=['must_change_password'])

            messages.success(
                self.request,
                'Password changed successfully! '
                'You now have full access to the application.'
            )

        return response

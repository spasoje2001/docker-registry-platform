from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

from .forms import CustomUserCreationForm
from .forms import EditProfileForm
from .forms import ChangeEmailForm
from .forms import ChangePasswordForm


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


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html", {"user": request.user})


@login_required
def edit_profile(request):
    user = request.user

    if request.method == "POST":
        form = EditProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        form = EditProfileForm(instance=user)

    return render(
        request,
        "accounts/edit_profile.html",
        {"form": form, "user": user}
    )


@login_required
def change_email(request):
    user = request.user

    if request.method == "POST":
        form = ChangeEmailForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Email changed successfully.")
            return redirect("accounts:profile")
    else:
        form = ChangeEmailForm(instance=user)

    return render(
        request,
        "accounts/email_change.html",
        {"form": form}
    )


@login_required
def change_password(request):
    if request.method == "POST":
        form = ChangePasswordForm(user=request.user, data=request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password successfully changed.")
            return redirect("accounts:profile")
        else:
            messages.success(request, "Current password wasn't correct.")
    else:
        form = ChangePasswordForm(user=request.user)

    return render(
        request,
        "accounts/change_password.html",
        {"form": form, "user": request.user}
    )

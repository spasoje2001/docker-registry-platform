from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.conf import settings

from .forms import ChangePasswordForm, RequestEmailChangeForm
from .forms import ConfirmEmailChangeForm, EditProfileForm
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .utils import generate_verification_code, store_email_change_request, delete_email_change_request, \
    get_email_change_request

from repositories.forms import RepositoryForm
from repositories.models import Repository


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

@login_required
@require_POST
def update_badges(request, user_id):
    if request.user.role not in ["admin", "super_admin"]:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    target = get_object_or_404(User, id=user_id)

    badge = request.POST.get("badge")
    value = request.POST.get("value")

    if badge not in ["is_verified_publisher", "is_sponsored_oss"]:
        return JsonResponse({"ok": False, "error": "bad badge"}, status=400)

    bool_value = str(value).lower() in ["1", "true", "on", "yes"]

    setattr(target, badge, bool_value)
    target.save(update_fields=[badge])

    return JsonResponse({"ok": True, "user_id": target.id, "badge": badge, "value": bool_value})


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


@login_required
def profile_view(request):
    active_tab = "repos"
    form_data = request.session.pop("repo_form_data", None)
    form_errors = request.session.pop("repo_form_errors", None)
    repositories = Repository.objects.filter(
        owner=request.user,
        is_official=False
    ).order_by('-updated_at')

    if form_data:
        repo_form = RepositoryForm(form_data, request=request)
        repo_form._errors = form_errors
        active_tab = "new_repo"
    else:
        repo_form = RepositoryForm(request=request)
        active_tab = "repos"

    return render(
        request,
        "accounts/profile.html",
        {
            "user": request.user,
            "repo_form": repo_form,
            "active_tab": active_tab,
            "repositories": repositories,
            "from_profile": True, 
        }
    )


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


@login_required
def email_change(request):
    """
    Request email change - sends verification code to new email.
    """
    if request.method == 'POST':
        form = RequestEmailChangeForm(request.user, request.POST)
        if form.is_valid():
            new_email = form.cleaned_data['new_email']

            code = generate_verification_code()

            # Store in Redis (expires in 10 minutes)
            store_email_change_request(
                user_id=request.user.id,
                new_email=new_email,
                code=code
            )

            try:
                send_mail(
                    subject='Email Change Verification Code',
                    message=f'Your verification code is: {code}\n\n'
                            f'This code will expire in 10 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[new_email],
                    fail_silently=False,
                )
                messages.success(
                    request,
                    f'Verification code sent to {new_email}. '
                    f'Please check your inbox.'
                )
                return redirect('accounts:email_change_confirm')
            except Exception as e:
                messages.error(
                    request,
                    'Failed to send verification email. Please try again.'
                )
                # Clean up Redis if email fails
                delete_email_change_request(request.user.id)
    else:
        form = RequestEmailChangeForm(request.user)

    return render(request, 'accounts/email_change.html', {'form': form})


@login_required
def email_change_confirm(request):
    """
    Confirm email change with verification code.
    """
    # Check if there's a pending request
    email_data = get_email_change_request(request.user.id)

    if not email_data:
        messages.error(
            request,
            'No pending email change request or code has expired.'
        )
        return redirect('accounts:profile')

    if request.method == 'POST':
        form = ConfirmEmailChangeForm(request.POST)
        if form.is_valid():
            entered_code = form.cleaned_data['code']

            if entered_code == email_data['code']:
                request.user.email = email_data['new_email']
                request.user.save(update_fields=['email'])

                delete_email_change_request(request.user.id)

                messages.success(
                    request,
                    'Email address changed successfully!'
                )
                return redirect('accounts:profile')
            else:
                form.add_error('code', 'Invalid verification code.')
    else:
        form = ConfirmEmailChangeForm()

    context = {
        'form': form,
        'new_email': email_data['new_email'],
    }
    return render(request, 'accounts/email_change_confirm.html', context)


@login_required
def cancel_email_change(request):
    """
    Cancel pending email change request.
    """
    if request.method == 'POST':
        delete_email_change_request(request.user.id)
        messages.info(request, 'Email change request cancelled.')

    return redirect('accounts:edit_profile')

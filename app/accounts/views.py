from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from app.accounts.forms import CustomUserCreationForm


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
                "Your account has been created! You are now able to log in"
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

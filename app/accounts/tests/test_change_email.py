from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core import mail

User = get_user_model()


class EmailChangeTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="old@example.com",
            password="StrongPass123!"
        )
        self.client.login(username="testuser", password="StrongPass123!")

        self.request_url = reverse("accounts:email_change")
        self.confirm_url = reverse("accounts:email_change_confirm")

    def test_request_email_change_sends_code(self):
        data = {
            "old_email": "old@example.com",
            "new_email": "new@example.com",
            "password": "StrongPass123!",
        }

        response = self.client.post(self.request_url, data, follow=True)

        user = User.objects.get(pk=self.user.pk)

        self.assertIsNotNone(user.email_change_code)
        self.assertEqual(user.email_change_new_email, "new@example.com")
        self.assertIsNotNone(user.email_change_requested_at)

        self.assertContains(
            response,
            "Verification code sent to new email address."
        )

    def test_confirm_email_change_success(self):
        self.user.email_change_code = "123456"
        self.user.email_change_new_email = "new@example.com"
        self.user.email_change_requested_at = timezone.now()
        self.user.save()

        response = self.client.post(
            self.confirm_url,
            {"code": "123456"},
            follow=True
        )

        self.user.refresh_from_db()

        self.assertEqual(self.user.email, "new@example.com")
        self.assertIsNone(self.user.email_change_code)

        self.assertContains(
            response,
            "Email address changed successfully."
        )

    def test_confirm_email_change_with_invalid_code_fails(self):
        self.user.email_change_code = "123456"
        self.user.email_change_new_email = "new@example.com"
        self.user.email_change_requested_at = timezone.now()
        self.user.save()

        response = self.client.post(
            self.confirm_url,
            {"code": "000000"}
        )

        self.assertFormError(
            response.context["form"],
            "code",
            "Invalid verification code."
        )

    def test_confirm_email_change_with_expired_code_fails(self):
        self.user.email_change_code = "123456"
        self.user.email_change_new_email = "new@example.com"
        self.user.email_change_requested_at = (
            timezone.now() - timedelta(minutes=15)
        )
        self.user.save()

        response = self.client.post(
            self.confirm_url,
            {"code": "123456"}
        )

        self.assertFormError(
            response.context["form"],
            "code",
            "Verification code has expired. Please request a new one."
        )

    def test_cancel_email_change_clears_code(self):
        self.client.login(username="testuser", password="StrongPass123!")

        self.user.email_change_code = "123456"
        self.user.email_change_new_email = "new@example.com"
        self.user.email_change_requested_at = timezone.now()
        self.user.save()

        response = self.client.post(
            reverse("accounts:email_change_cancel"),
            follow=True
        )

        self.user.refresh_from_db()

        self.assertIsNone(self.user.email_change_code)
        self.assertIsNone(self.user.email_change_new_email)
        self.assertIsNone(self.user.email_change_requested_at)

        self.assertRedirects(response, reverse("accounts:edit_profile"))

    def test_email_change_sends_verification_email(self):
        self.client.login(username="testuser", password="StrongPass123!")

        self.client.post(
            reverse("accounts:email_change"),
            {
                "old_email": "old@example.com",
                "new_email": "new@example.com",
                "password": "StrongPass123!",
            }
        )

        # how many emails is sent, 1? subject od mail?
        # who gets email? is there code?
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Confirm your email change")
        self.assertEqual(email.to, ["new@example.com"])
        self.assertIn("verification code", email.body.lower())

    def test_email_not_sent_if_form_invalid(self):
        self.client.login(username="testuser", password="StrongPass123!")

        self.client.post(
            reverse("accounts:email_change"),
            {
                "old_email": "WRONG@example.com",
                "new_email": "new@example.com",
                "password": "StrongPass123!",
            }
        )

        self.assertEqual(len(mail.outbox), 0)

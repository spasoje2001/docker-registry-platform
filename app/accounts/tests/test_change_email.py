from django.test import TestCase
from django.urls import reverse
from django.core import mail

from ..models import User
from ..utils import (
    store_email_change_request,
    get_email_change_request,
    delete_email_change_request,
)


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
        self.cancel_url = reverse("accounts:email_change_cancel")

    def tearDown(self):
        """Clean up Redis after each test."""
        delete_email_change_request(self.user.id)

    def test_request_email_change_sends_code(self):
        """Test that requesting email change stores data in Redis and sends email."""
        data = {
            "old_email": "old@example.com",
            "new_email": "new@example.com",
            "password": "StrongPass123!",
        }

        response = self.client.post(self.request_url, data, follow=True)

        redis_data = get_email_change_request(self.user.id)
        self.assertIsNotNone(redis_data)
        self.assertEqual(redis_data['new_email'], "new@example.com")
        self.assertIsNotNone(redis_data['code'])
        self.assertEqual(len(redis_data['code']), 6)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('Verification code sent', str(messages[0]))

        self.assertRedirects(response, self.confirm_url)

    def test_request_email_change_with_wrong_old_email_fails(self):
        """Test that wrong current email fails validation."""
        data = {
            "old_email": "wrong@example.com",
            "new_email": "new@example.com",
            "password": "StrongPass123!",
        }

        response = self.client.post(self.request_url, data)

        self.assertFormError(
            response.context["form"],
            "old_email",
            "Current email is incorrect."
        )

        redis_data = get_email_change_request(self.user.id)
        self.assertIsNone(redis_data)

    def test_request_email_change_with_wrong_password_fails(self):
        data = {
            "old_email": "old@example.com",
            "new_email": "new@example.com",
            "password": "WrongPassword123!",
        }

        response = self.client.post(self.request_url, data)

        self.assertFormError(
            response.context["form"],
            "password",
            "Incorrect password."
        )

        redis_data = get_email_change_request(self.user.id)
        self.assertIsNone(redis_data)

    def test_request_email_change_with_duplicate_email_fails(self):
        """Test that email already in use fails validation."""
        User.objects.create_user(
            username="otheruser",
            email="new@example.com",
            password="pass123"
        )

        data = {
            "old_email": "old@example.com",
            "new_email": "new@example.com",
            "password": "StrongPass123!",
        }

        response = self.client.post(self.request_url, data)

        self.assertFormError(
            response.context["form"],
            "new_email",
            "This email is already in use."
        )

    def test_confirm_email_change_success(self):
        """Test successful email confirmation with correct code."""
        code = "123456"
        store_email_change_request(
            self.user.id,
            "new@example.com",
            code
        )

        response = self.client.post(
            self.confirm_url,
            {"code": code},
            follow=True
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")

        redis_data = get_email_change_request(self.user.id)
        self.assertIsNone(redis_data)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('Email address changed successfully', str(messages[0]))

        self.assertRedirects(response, reverse("accounts:profile"))

    def test_confirm_email_change_with_invalid_code_fails(self):
        """Test that invalid code fails confirmation."""
        store_email_change_request(
            self.user.id,
            "new@example.com",
            "123456"
        )

        response = self.client.post(
            self.confirm_url,
            {"code": "000000"}  # Wrong code
        )

        self.assertFormError(
            response.context["form"],
            "code",
            "Invalid verification code."
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")

        redis_data = get_email_change_request(self.user.id)
        self.assertIsNotNone(redis_data)

    def test_confirm_email_change_without_pending_request_fails(self):
        """Test that confirmation fails if no pending request exists."""
        response = self.client.post(
            self.confirm_url,
            {"code": "123456"},
            follow=True
        )

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('No pending email change', str(messages[0]))

        self.assertRedirects(response, reverse("accounts:profile"))

    def test_confirm_email_change_get_request_without_pending_fails(self):
        """Test that GET to confirm page fails if no pending request."""
        response = self.client.get(self.confirm_url, follow=True)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('No pending email change', str(messages[0]))

        self.assertRedirects(response, reverse("accounts:profile"))

    def test_cancel_email_change_clears_redis(self):
        """Test that canceling email change clears Redis data."""
        store_email_change_request(
            self.user.id,
            "new@example.com",
            "123456"
        )

        response = self.client.post(self.cancel_url, follow=True)

        redis_data = get_email_change_request(self.user.id)
        self.assertIsNone(redis_data)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('Email change request cancelled', str(messages[0]))

        self.assertRedirects(response, reverse("accounts:edit_profile"))

    def test_email_change_sends_verification_email(self):
        """Test that verification email is sent with correct content."""
        data = {
            "old_email": "old@example.com",
            "new_email": "new@example.com",
            "password": "StrongPass123!",
        }

        self.client.post(self.request_url, data)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertEqual(email.subject, "Email Change Verification Code")
        self.assertEqual(email.to, ["new@example.com"])
        self.assertIn("verification code", email.body.lower())
        self.assertIn("10 minutes", email.body.lower())

        redis_data = get_email_change_request(self.user.id)
        self.assertIn(redis_data['code'], email.body)

    def test_email_not_sent_if_form_invalid(self):
        """Test that no email is sent if form validation fails."""
        data = {
            "old_email": "WRONG@example.com",
            "new_email": "new@example.com",
            "password": "StrongPass123!",
        }

        self.client.post(self.request_url, data)

        self.assertEqual(len(mail.outbox), 0)

        redis_data = get_email_change_request(self.user.id)
        self.assertIsNone(redis_data)

    def test_multiple_requests_override_previous(self):
        """Test that new email change request overrides previous one."""
        self.client.post(self.request_url, {
            "old_email": "old@example.com",
            "new_email": "first@example.com",
            "password": "StrongPass123!",
        })

        redis_data_1 = get_email_change_request(self.user.id)
        first_code = redis_data_1['code']

        self.client.post(self.request_url, {
            "old_email": "old@example.com",
            "new_email": "second@example.com",
            "password": "StrongPass123!",
        })

        redis_data_2 = get_email_change_request(self.user.id)

        self.assertEqual(redis_data_2['new_email'], "second@example.com")
        self.assertNotEqual(redis_data_2['code'], first_code)

        self.assertEqual(len(mail.outbox), 2)

    def test_unauthorized_user_cannot_access_email_change(self):
        """Test that unauthenticated users are redirected to login."""
        self.client.logout()

        response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
        self.assertIn(f'next={self.request_url}', response.url)

    def test_unauthorized_user_cannot_access_confirm(self):
        """Test that unauthenticated users cannot confirm email change."""
        self.client.logout()

        response = self.client.get(self.confirm_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
        self.assertIn(f'next={self.confirm_url}', response.url)

    def test_redis_data_has_correct_ttl(self):
        """Test that Redis data expires after 10 minutes."""
        from django.core.cache import cache

        store_email_change_request(
            self.user.id,
            "new@example.com",
            "123456"
        )

        cache_key = f'email_change:{self.user.id}'
        ttl = cache.ttl(cache_key)

        self.assertGreater(ttl, 590)
        self.assertLessEqual(ttl, 600)

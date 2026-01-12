from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class SuperAdminFlowTestCase(TestCase):
    def setUp(self):
        self.login_url = reverse("accounts:login")
        self.superadmin = User.objects.create_user(
            username="superadmin",
            email="super@admin.com",
            password="SuperPassword123!",
            role=User.Role.SUPER_ADMIN,
        )
        self.superadmin.must_change_password = False
        self.superadmin.is_superuser = True
        self.superadmin.save()

    def test_superadmin_creates_admin_and_admin_logs_in(self):
        login_data = {"username": "superadmin", "password": "SuperPassword123!"}
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, 302)

        create_admin_data = {
            "username": "newadmin",
            "email": "admin@test.com",
            "generate_password": True,
        }
        response = self.client.post(reverse("accounts:create_admin"), create_admin_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:create_admin_success"))

        new_admin = User.objects.get(username="newadmin")
        self.assertFalse(new_admin.is_superuser)

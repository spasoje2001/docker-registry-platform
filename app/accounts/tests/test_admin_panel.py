from tkinter.constants import YES

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class AdminPanelTest(TestCase):
    def setUp(self):
        self.home_url = reverse('core:home')
        self.admin_panel_url = reverse('accounts:admin_panel')

        self.admin_password = "AdminPass123!"
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@gmail.com",
            password=self.admin_password,
            role = User.Role.ADMIN,
        )
        self.user1 = User.objects.create_user(
            username="marko",
            email="marko@example.com",
            password="UserPass123!",
            role=User.Role.USER,
        )
        self.user2 = User.objects.create_user(
            username="jelena",
            email="jelena@example.com",
            password="UserPass123!",
            role=User.Role.USER,
        )


        # Unit test: admin can search users
        #
        # Unit test: admin can assign Verified Publisher
        #
        # Unit test: admin can assign Sponsored OSS
        #
        # Unit test: regular user cannot access

    def login_admin(self):
        self.client.login(username="admin", password=self.admin_password)

    def test_admin_user_search(self):
        self.login_admin()

        response = self.client.get(self.admin_panel_url, {"q": "marko"})
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        self.assertIn("marko", content)
        self.assertNotIn("jelena", content)

    def test_admin_can_assign_verified_publisher(self):
        self.login_admin()

        url = reverse("accounts:update_badges", kwargs={"user_id":self.user1.id})

        response = self.client.post(
            url,
            data= {"badge": "is_verified_publisher", "value": "true"},
        )
        print("STATUS:", response.status_code)
        print("BODY:", response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)

        self.user1.refresh_from_db()
        self.assertTrue(self.user1.is_verified_publisher)
        self.assertFalse(self.user1.is_sponsored_oss)

    def test_admin_can_assign_sponsored_oss(self):
        self.login_admin()
        url = reverse("accounts:update_badges", kwargs={"user_id":self.user2.id})

        response = self.client.post(
            url,
            data= {"badge": "is_sponsored_oss", "value": "true"},
        )
        self.assertEqual(response.status_code, 200)

        self.user2.refresh_from_db()
        self.assertTrue(self.user2.is_sponsored_oss)
        self.assertFalse(self.user2.is_verified_publisher)

    def test_regular_user_cannot_access(self):
        self.client.login(username="marko", password="UserPass123")

        response = self.client.get(self.admin_panel_url)
        self.assertEqual(response.status_code, 302)


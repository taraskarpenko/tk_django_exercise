from django.test import tag
from django.urls import reverse

from recipe.tests.utils import (
    create_user,
    UnauthorizedTestCase,
    AuthorizedTestCase,
)


@tag('api', 'user')
class TestUnauthorizedUserAccess(UnauthorizedTestCase):
    """Test that run without authorization"""

    def test_access_user(self):
        """verify user details endpoint requires authorization"""
        url = reverse("user")
        user_result = self.client.get(url)

        self.assertEqual(user_result.status_code, 401)

    def test_generate_token(self):
        """verify token is generated for the valid username and password"""
        user = create_user(username="test_user", password="test_pass")
        url = reverse("token")
        payload = {
            "username": user.username,
            "password": "test_pass",
        }
        token_result = self.client.post(url, payload, format="json")

        self.assertEqual(token_result.status_code, 200)
        self.assertIn("token", token_result.data)

    def test_generate_token_fails(self):
        """
        verify token is NOT generated for the INvalid username and password
        """
        user = create_user(username="test_user", password="test_pass")
        url = reverse("token")
        payload = {
            "username": user.username,
            "password": "test_pazz",
        }
        token_result = self.client.post(url, payload, format="json")

        self.assertIn('Unable to authenticate', str(token_result.data))
        self.assertEqual(token_result.status_code, 400)
        self.assertNotIn("token", token_result.data)


@tag('api', 'user')
class TestAuthorizedAccess(AuthorizedTestCase):
    def test_access_user(self):
        """
        Verify user details accessible with authorization
        """
        url = reverse("user")
        user_result = self.client.get(url)

        self.assertEqual(user_result.status_code, 200)
        self.assertEqual(user_result.data["username"], self.user.username)

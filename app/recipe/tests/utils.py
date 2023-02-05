from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from recipe.models import Recipe, Ingredient

DEFAULT_RECIPE_NAME = "Recipe name"
DEFAULT_RECIPE_DESCRIPTION = "Recipe description"
DEFAULT_INGREDIENT_NAME = "Ingredient"


def create_user(username="test_user", password="userpass123456789"):
    user = get_user_model().objects.create(username=username)
    user.set_password(password)
    user.save()
    return user


def create_recipe(
        user, name=DEFAULT_RECIPE_NAME, description=DEFAULT_RECIPE_DESCRIPTION
):
    return Recipe.objects.create(user=user, name=name, description=description)


def create_ingredient(user, recipe, name=DEFAULT_INGREDIENT_NAME):
    return Ingredient.objects.create(user=user, recipe=recipe, name=name)


class UnauthorizedTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()


class AuthorizedTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

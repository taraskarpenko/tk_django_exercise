from django.db.utils import IntegrityError, DataError
from django.test import TestCase, tag

from recipe.models import Recipe
from recipe.tests.utils import (
    create_user,
    create_recipe,
    create_ingredient,
    DEFAULT_RECIPE_NAME,
    DEFAULT_INGREDIENT_NAME,
)


@tag('models')
class ModelTest(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_create_simple_recipe(self):
        """verify recipe model created and assigned to the proper user"""
        recipe = create_recipe(user=self.user)

        result_recipe = Recipe.objects.get(id=recipe.id)

        self.assertEqual(str(result_recipe), DEFAULT_RECIPE_NAME)
        self.assertEqual(self.user, result_recipe.user)

    def test_create_recipes_with_same_name_different_users(self):
        """
        verify two recipes can be created with the same name
        for different users
        """
        other_user = create_user(username='other_user')
        create_recipe(user=self.user, name='Recipe')
        create_recipe(user=other_user, name='Recipe')

        self.assertEqual(Recipe.objects.count(), 2)

    def test_create_recipe_with_same_name_raises(self):
        """
        verify two recipes can NOT be created with the same name
        for the same user
        """
        create_recipe(user=self.user, name='Recipe1')
        with self.assertRaises(IntegrityError):
            create_recipe(user=self.user, name='Recipe1')

    def test_create_recipe_with_None_name_raises(self):
        """verify Recipe model can not be created without name"""
        with self.assertRaises(IntegrityError):
            create_recipe(user=self.user, name=None)

    def test_create_recipe_with_None_user_raises(self):
        """verify Recipe model can not be created without user"""
        with self.assertRaises(IntegrityError):
            create_recipe(user=None)

    def test_create_recipe_with_long_name_raises(self):
        """verify Recipe model can not be created name longer then 255"""
        with self.assertRaises(DataError):
            create_recipe(user=self.user, name="c" * 256)

    def test_create_simple_ingredient(self):
        """verify ingredient created"""
        recipe = Recipe.objects.create(user=self.user)
        create_ingredient(user=self.user, recipe=recipe)

        result_ingredients = recipe.ingredients.all()
        self.assertEqual(len(result_ingredients), 1)
        self.assertEqual(result_ingredients[0].name, DEFAULT_INGREDIENT_NAME)
        self.assertEqual(result_ingredients[0].user, self.user)

    def test_create_ingredient_without_recipe_raises(self):
        """Verify that ingredient can not be created without recipe"""
        with self.assertRaises(IntegrityError):
            create_ingredient(user=self.user, recipe=None)

    def test_create_recipe_with_multiple_ingredients(self):
        """
        Verify that multiple ingredients can be related to the same recipe
        """
        recipe = Recipe.objects.create(user=self.user)
        ingredient_1 = create_ingredient(
            user=self.user, recipe=recipe, name="ingredient1"
        )
        ingredient_2 = create_ingredient(
            user=self.user, recipe=recipe, name="ingredient2"
        )
        ingredient_3 = create_ingredient(
            user=self.user, recipe=recipe, name="ingredient3"
        )

        result_ingredients = recipe.ingredients.all()
        self.assertEqual(
            {ingredient_1, ingredient_2, ingredient_3}, set(result_ingredients)
        )

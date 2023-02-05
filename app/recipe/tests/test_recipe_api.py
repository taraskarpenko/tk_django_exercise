from django.db import transaction
from django.test import tag
from django.urls import reverse
from parameterized import parameterized

from recipe.models import Recipe, Ingredient
from recipe.serializers import RecipeSerializer
from recipe.tests.utils import (
    UnauthorizedTestCase,
    AuthorizedTestCase,
    create_recipe,
    create_user,
)

RECIPES_URL = reverse("recipe:recipe-list")


def recipe_detail_url(recipe_id):
    return reverse("recipe:recipe-detail", args=[recipe_id])


@tag('api', 'recipe')
class TestUnauthorizedRecipeAccess(UnauthorizedTestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user()
        self.recipe = create_recipe(user=self.user)

    @parameterized.expand(
        [("list recipes", "GET", None), ("create recipe", "POST", {})]
    )
    def test_recipes_endpoint_requires_auth(self, name, method, data):
        """
        verify that call to recipes list/create endpoint returns 401
        in case of unauthorized request
        """
        recipes_result = self.client.generic(method, RECIPES_URL, data)
        self.assertEqual(recipes_result.status_code, 401)

    @parameterized.expand(
        [
            ("get recipe details", "GET", None),
            ("delete recipe", "DELETE", None),
            ("partial recipe update", "PATCH", {"name": "updated name"}),
            (
                    "full recipe update",
                    "PUT",
                    {
                        "name": "updated name",
                        "description": "updated description",
                        "ingredients": [],
                    },
            ),
        ]
    )
    def test_recipe_by_id_endpoint_requires_auth(self, name, method, data):
        """
        verify that call to recipes by ID endpoint returns 401
        in case of unauthorized request
        """
        recipe_result = self.client.generic(
            method, recipe_detail_url(self.recipe.id), data
        )
        self.assertEqual(recipe_result.status_code, 401)


@tag('api', 'recipe')
class TestCreateRecipe(AuthorizedTestCase):
    def test_recipe_created_without_ingredients(self):
        """verify recipe without ingredients created correctly"""
        payload = {
            "name": "Recipe name",
            "description": "Recipe description",
        }
        post_result = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(post_result.status_code, 201)

        # verify only one recipe created
        self.assertEqual(Recipe.objects.count(), 1)

        # verify recipe created correctly
        recipe_from_db = Recipe.objects.get(id=post_result.data["id"])
        self.assertEqual(recipe_from_db.name, payload["name"])
        self.assertEqual(recipe_from_db.description, payload["description"])
        self.assertEqual(recipe_from_db.user, self.user)

    def test_recipe_created_with_ingredients(self):
        """verify recipe with multiple ingredients created correctly"""
        payload = {
            "name": "Recipe name",
            "description": "Recipe description",
            "ingredients": [{"name": "salt"}, {"name": "pepper"}],
        }

        post_result = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(post_result.status_code, 201)
        # verify ingredients in recipe are correct
        recipe_from_db = Recipe.objects.get(id=post_result.data["id"])
        recipe_ingredient_names = {
            ingredient.name for ingredient in recipe_from_db.ingredients.all()
        }

        self.assertEqual(recipe_from_db.ingredients.count(), 2)
        self.assertEqual(recipe_ingredient_names, {"salt", "pepper"})

        # verify ingredients in DB correct
        ingredients_in_db = Ingredient.objects
        self.assertEqual(ingredients_in_db.count(), 2)
        db_ingredient_names = {
            ingredient.name for ingredient in ingredients_in_db.all()
        }
        self.assertEqual(db_ingredient_names, {"salt", "pepper"})

    def test_recipe_created_with_ingredient_duplicate(self):
        """
        verify that duplicated ingredients are not created in DB
        """
        payload = {
            "name": "Recipe name",
            "description": "Recipe description",
            "ingredients": [
                {"name": "salt"}, {"name": "salt"}, {"name": "salt"}
            ],
        }
        post_result = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(post_result.status_code, 201)

        # verify ingredients duplicates removed
        recipe_from_db = Recipe.objects.get(id=post_result.data["id"])
        self.assertEqual(recipe_from_db.ingredients.count(), 1)
        self.assertEqual(recipe_from_db.ingredients.first().name, "salt")

        # verify no ingredients duplicates in DB
        ingredients_in_db = Ingredient.objects
        self.assertEqual(ingredients_in_db.count(), 1)
        self.assertEqual(ingredients_in_db.first().name, "salt")

    def test_create_recipe_with_same_name(self):
        """
        verify that creation of recipe with already
        existing name fails and do not override existing recipe

        """
        payload1 = {
            'name': 'Recipe name',
            'description': 'Recipe description1',
        }
        payload2 = {
            'name': 'Recipe name',
            'description': 'Recipe description2',
        }
        post_result1 = self.client.post(RECIPES_URL, payload1, format="json")
        with transaction.atomic():
            # django test case runs in a single transaction,
            # thus call that causes exception must be executed in atomic
            post_result2 = self.client.post(
                RECIPES_URL, payload2, format="json"
            )

        self.assertEqual(post_result1.status_code, 201)
        self.assertEqual(post_result2.status_code, 400)

        self.assertEqual(Recipe.objects.count(), 1)
        self.assertEqual(
            Recipe.objects.first().description,
            'Recipe description1'
        )


@tag('api', 'recipe')
class TestListRecipes(AuthorizedTestCase):

    def test_empty_recipes_list(self):
        """verify /recipe/ endpoint return empty list"""
        list_result = self.client.get(RECIPES_URL)
        self.assertEqual(list_result.status_code, 200)
        self.assertEqual(len(list_result.data), 0)

    def test_list_recipes_details(self):
        """
        verify /recipe/ endpoint return correct list
        excluding recipes of other user
        """
        recipe1 = create_recipe(
            user=self.user, name='Rcp 1', description='Descr 1'
        )
        recipe2 = create_recipe(
            user=self.user, name='Rcp 2', description='Descr 2'
        )
        recipe1_serialized = RecipeSerializer(recipe1).data
        recipe2_serialized = RecipeSerializer(recipe2).data

        other_user = create_user(username='other_user', password='other_pass')
        create_recipe(user=other_user, name='Rcp 3', description='Descr 3')

        self.assertEqual(Recipe.objects.all().count(), 3)

        list_result = self.client.get(RECIPES_URL)
        self.assertEqual(list_result.status_code, 200)
        self.assertEqual(len(list_result.data), 2)
        self.assertEqual(list_result.data[0], recipe1_serialized)
        self.assertEqual(list_result.data[1], recipe2_serialized)

    def test_list_recipes_return_big_list(self):
        """
        verify /recipe/ endpoint return correct list
        even with big number of recipes
        """
        recipes_count = 101
        recipe_ids = [
            create_recipe(user=self.user, name=f'Recipe {n}').id
            for n in range(recipes_count)
        ]

        list_result = self.client.get(RECIPES_URL)
        self.assertEqual(list_result.status_code, 200)

        self.assertEqual(len(list_result.data), recipes_count)
        result_recipes_ids = [rec['id'] for rec in list_result.data]
        self.assertEqual(recipe_ids, result_recipes_ids)


@tag('api', 'recipe')
class TestSearchRecipesByName(AuthorizedTestCase):

    def test_search_return_empty_list(self):
        """
        Verify search returns empty list if no match found
        """
        create_recipe(user=self.user, name="Recipe")
        search_result = self.client.get(RECIPES_URL, {'name': 'Rezipe'})
        self.assertEqual(search_result.status_code, 200)
        self.assertEqual(search_result.data, [])

    def test_search_returns_empty_list_excluding_other_users(self):
        """
        Verify search does not return a recipe of other user
        even if name matches
        """
        other_user = create_user(username='other_user', password='other_pass')
        create_recipe(user=other_user, name="Recipe")
        search_result = self.client.get(RECIPES_URL, {'name': 'Recipe'})
        self.assertEqual(search_result.status_code, 200)
        self.assertEqual(search_result.data, [])

    def test_full_name_search(self):
        """
        Verify search returns the recipe that completely matches
        """
        recipe1 = create_recipe(user=self.user, name="Recipe")
        create_recipe(user=self.user, name="Recip")
        search_result = self.client.get(RECIPES_URL, {'name': recipe1.name})
        self.assertEqual(search_result.status_code, 200)
        self.assertEqual(search_result.data, [RecipeSerializer(recipe1).data])

    def test_partial_name_search(self):
        """
        Verify search finds recipe by partial match
        """
        recipe1 = create_recipe(user=self.user, name="Recipe1")
        recipe2 = create_recipe(user=self.user, name="Recipe2")
        create_recipe(user=self.user, name="Rezipe3")
        search_result = self.client.get(RECIPES_URL, {'name': 'ecipe'})
        self.assertEqual(search_result.status_code, 200)
        self.assertEqual(
            search_result.data,
            [RecipeSerializer(recipe1).data, RecipeSerializer(recipe2).data]
        )

    @parameterized.expand([
        ('ECIPE',),
        ('recipe',)
    ])
    def test_case_insensitive_partial_search(self, search_string):
        """
        Verify search finds recipe by partial match case-insensitive
        """
        recipe1 = create_recipe(user=self.user, name="ReCiPe1")
        recipe2 = create_recipe(user=self.user, name="rEcIpE2")
        create_recipe(user=self.user, name="Rezipe3")
        search_result = self.client.get(RECIPES_URL, {'name': search_string})
        self.assertEqual(search_result.status_code, 200)
        self.assertEqual(
            search_result.data,
            [RecipeSerializer(recipe1).data, RecipeSerializer(recipe2).data]
        )


@tag('api', 'recipe')
class TestRecipeDetails(AuthorizedTestCase):
    def test_full_recipe_details(self):
        """
        Verify recipe details endpoint return all expected properties
        """
        recipe = create_recipe(
            user=self.user,
            name='Recipe',
            description='Recipe description'
        )
        Ingredient.objects.create(
            user=self.user, name='Ingredient1', recipe=recipe
        )
        Ingredient.objects.create(
            user=self.user, name='Ingredient2', recipe=recipe
        )

        recipe_details_resp = self.client.get(recipe_detail_url(recipe.id))

        self.assertEqual(recipe_details_resp.status_code, 200)
        self.assertEqual(
            RecipeSerializer(recipe).data,
            recipe_details_resp.data
        )

    def test_recipe_detail_for_other_user(self):
        """
        Verify recipe details endpoint return 404 for the recipe of other user
        """
        other_user = create_user(username='other_user')
        recipe = create_recipe(
            user=other_user,
            name='Recipe',
            description='Recipe description'
        )

        recipe_details_resp = self.client.get(recipe_detail_url(recipe.id))
        self.assertEqual(recipe_details_resp.status_code, 404)

    def test_recipe_detail_not_existing(self):
        """
        Verify recipe details endpoint return 404 if recipe does not exist
        """
        last_recipe = Recipe.objects.order_by('-id').last()
        last_recipe_id = 0 if last_recipe is None else int(last_recipe.id) + 1
        recipe_details_resp = self.client.get(
            recipe_detail_url(last_recipe_id)
        )
        self.assertEqual(recipe_details_resp.status_code, 404)


@tag('api', 'recipe')
class TestRecipeUpdate(AuthorizedTestCase):
    def test_update_recipe_name(self):
        """
        Verify recipe patch endpoint updates name only
        """
        recipe = create_recipe(user=self.user)
        update_response = self.client.patch(
            recipe_detail_url(recipe.id),
            {'name': 'updated name'}
        )
        self.assertEqual(update_response.status_code, 200)
        recipe.refresh_from_db()
        self.assertEqual(recipe.name, 'updated name')

    def test_update_recipe_description(self):
        """
        Verify recipe patch endpoint updates description only
        """
        recipe = create_recipe(user=self.user)
        update_response = self.client.patch(
            recipe_detail_url(recipe.id),
            {'description': 'updated description'}
        )
        self.assertEqual(update_response.status_code, 200)
        recipe.refresh_from_db()
        self.assertEqual(recipe.description, 'updated description')

    def test_full_update_add_ingredients(self):
        """
        Verify patch endpoint performs full update
        including adding ingredients
        """
        recipe = create_recipe(user=self.user)
        update_response = self.client.patch(
            recipe_detail_url(recipe.id),
            {
                'name': 'updated name',
                'description': 'updated description',
                'ingredients': [{'name': 'ing1'}, {'name': 'ing2'}]
            },
            format='json'
        )
        self.assertEqual(update_response.status_code, 200)
        recipe.refresh_from_db()
        self.assertEqual(recipe.name, 'updated name')
        self.assertEqual(recipe.description, 'updated description')
        self.assertEqual(
            {ing.name for ing in recipe.ingredients.all()},
            {'ing1', 'ing2'}
        )

    def test_update_ingredients(self):
        """
        Verify patch endpoint updates ingredients,
        and removes orphan ingredients from DB
        """
        recipe = create_recipe(user=self.user)
        Ingredient.objects.create(user=self.user, recipe=recipe, name='ing1')
        Ingredient.objects.create(user=self.user, recipe=recipe, name='ing2')

        update_response = self.client.patch(
            recipe_detail_url(recipe.id),
            {
                'ingredients': [{'name': 'ing2'}, {'name': 'ing3'}],
            },
            format='json'
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            {ing.name for ing in recipe.ingredients.all()},
            {'ing2', 'ing3'}
        )
        self.assertEqual(
            {ing.name for ing in Ingredient.objects.all()},
            {'ing2', 'ing3'}
        )

    def test_remove_ingredients(self):
        """
        Verify patch endpoint removes ingredients,
        and removes orphan ingredients from DB
        """
        recipe = create_recipe(user=self.user)
        Ingredient.objects.create(user=self.user, recipe=recipe, name='ing1')
        Ingredient.objects.create(user=self.user, recipe=recipe, name='ing2')
        update_response = self.client.patch(
            recipe_detail_url(recipe.id),
            {
                'name': 'updated name',
                'description': 'updated description',
                'ingredients': []
            },
            format='json'
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(recipe.ingredients.count(), 0)
        self.assertEqual(Ingredient.objects.count(), 0)

    def test_update_other_user_recipe(self):
        """verify patch endpoint returns 404 for the recipe of other user"""
        other_user = create_user(username='other_user')
        recipe = create_recipe(user=other_user, name='name')
        update_response = self.client.patch(
            recipe_detail_url(recipe.id),
            {'name': 'updated name'}
        )
        self.assertEqual(update_response.status_code, 404)
        recipe.refresh_from_db()
        self.assertEqual(recipe.name, 'name')

    def test_update_name_to_already_existing(self):
        """
        verify patch endpoint returns 404 for the recipe of the other user
        """
        recipe1 = create_recipe(user=self.user, name='recipe1')
        create_recipe(user=self.user, name='recipe2')
        with transaction.atomic():
            # django test case runs in a single transaction,
            # thus call that causes exception must be executed in atomic
            update_response = self.client.patch(
                recipe_detail_url(recipe1.id),
                {'name': 'recipe2'}
            )
        self.assertEqual(update_response.status_code, 400)
        recipe1.refresh_from_db()
        self.assertEqual(recipe1.name, 'recipe1')

    def test_update_not_existing_recipe(self):
        """verify patch endpoint returns 404 if recipe does not exists"""
        last_recipe = Recipe.objects.order_by('-id').last()
        last_recipe_id = 0 if last_recipe is None else int(last_recipe.id) + 1
        update_response = self.client.patch(
            recipe_detail_url(last_recipe_id),
            {'name': 'recipe2'}
        )
        self.assertEqual(update_response.status_code, 404)


@tag('api', 'recipe')
class TestRecipeDelete(AuthorizedTestCase):
    def test_delete_recipe(self):
        """verify delete endpoints deletes the recipe"""
        recipe = create_recipe(user=self.user)
        delete_response = self.client.delete(recipe_detail_url(recipe.id))
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(Recipe.objects.count(), 0)

    def test_delete_other_user_recipe(self):
        """
        Verify delete endpoint returns 404 for the recipe of the other user
        """
        other_user = create_user(username='other_user')
        recipe = create_recipe(user=other_user)
        delete_response = self.client.delete(recipe_detail_url(recipe.id))
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(Recipe.objects.get(id=recipe.id).user, other_user)

    def test_delete_already_deleted_recipe(self):
        """
        Verify delete endpoint returns 404
        if the recipe was already deleted
        """
        recipe = create_recipe(user=self.user)
        delete_response = self.client.delete(recipe_detail_url(recipe.id))
        self.assertEqual(delete_response.status_code, 204)
        delete_response2 = self.client.delete(recipe_detail_url(recipe.id))
        self.assertEqual(delete_response2.status_code, 404)

    def test_delete_not_existing_recipe(self):
        last_recipe = Recipe.objects.order_by('-id').last()
        last_recipe_id = 0 if last_recipe is None else int(last_recipe.id) + 1

        delete_response = self.client.delete(last_recipe_id)
        self.assertEqual(delete_response.status_code, 404)

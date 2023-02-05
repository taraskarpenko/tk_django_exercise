from rest_framework import serializers

from recipe.models import Ingredient, Recipe


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["name"]
        read_only_fields = []


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = ["id", "name", "description", "ingredients"]
        read_only_fields = ["id"]

    def _add_ingredients(self, ingredients, recipe):
        ingredients_to_create = {
            ing['name'] for ing in ingredients
        }
        ingredients_in_recipe = {
            ing.name for ing in recipe.ingredients.all()
        }

        if recipe.ingredients.count() > 0:
            # identify ingredients that are in recipe but not in new list
            ingredients_to_delete = filter(
                lambda ing: ing.name not in ingredients_to_create,
                recipe.ingredients.all()
            )
            # delete those ingredients
            for ing in ingredients_to_delete:
                ing.delete()

            # identify ingredients that are in new list but not in recipe
            ingredients_to_create = filter(
                lambda ing: ing not in ingredients_in_recipe,
                ingredients_to_create
            )

        user = self.context["request"].user
        for ingredient_name in ingredients_to_create:
            Ingredient.objects.create(
                user=user, recipe=recipe, name=ingredient_name
            )

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients", [])
        recipe = super().create(validated_data)

        if ingredients:
            self._add_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        if ingredients is not None:
            self._add_ingredients(ingredients, instance)

        super().update(instance, validated_data)
        return instance

from django.contrib import admin

from recipe.models import Recipe, Ingredient

admin.site.register(Recipe)
admin.site.register(Ingredient)

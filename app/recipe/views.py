from rest_framework import viewsets
from recipe.serializers import RecipeSerializer
from recipe.models import Recipe
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="name",
                type=OpenApiTypes.STR,
                description="Search string by recipe name"
            ),
        ]
    )
)
class RecipeViewSet(viewsets.ModelViewSet):
    """
    Recipe model CRUD view set
    requires authentication
    """

    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        queryset = self.queryset
        name_search_string = self.request.query_params.get("name")
        if name_search_string:
            queryset = queryset.filter(name__icontains=name_search_string)

        return queryset.filter(user=self.request.user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

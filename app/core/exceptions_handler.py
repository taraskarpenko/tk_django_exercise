from django.db.utils import IntegrityError
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback


def app_exception_handler(exc, context):
    # TODO maybe better error handling. Return proper error message
    response = exception_handler(exc, context)
    if response is None:
        if isinstance(exc, IntegrityError):
            set_rollback()
            message = 'Bad request'
            if (
                    'unique_recipe_name_for_user' in str(exc)
                    and context['request'].path == '/recipe/recipes/'
                    and context['request'].method == 'POST'
            ):
                message = 'Recipe with such name already exists'
            return Response(status=400, data=message)

    return response

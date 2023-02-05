from rest_framework import generics, authentication, permissions
from rest_framework.authtoken.views import ObtainAuthToken

from core.serializers import UserSerializer, AuthTokenSerializer


class RetrieveUserView(generics.RetrieveAPIView):
    """retrieve current user details"""

    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CreateTokenView(ObtainAuthToken):
    """Generate and return user auth token"""

    serializer_class = AuthTokenSerializer

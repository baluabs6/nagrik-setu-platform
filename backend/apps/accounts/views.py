from rest_framework import generics, permissions
from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """Public sign-up endpoint. Login itself is handled by SimpleJWT's
    built-in TokenObtainPairView, wired directly in config/urls.py."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

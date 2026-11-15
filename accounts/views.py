from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts import services
from accounts.filters import UserFilter
from accounts.models import User
from accounts.permissions import IsAdmin
from accounts.serializers import LoginSerializer, MeSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Account created. You can log in after an admin approves it."},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class MeView(generics.RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class UserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Admin management of regular users. Superusers are not listed."""

    queryset = User.objects.filter(is_superuser=False).order_by("date_joined")
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    filterset_class = UserFilter

    def _change_status(self, change):
        user = self.get_object()
        try:
            change(user)
        except services.UserStateError as e:
            raise ValidationError({"detail": str(e)}) from e
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._change_status(services.approve)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        self._change_status(services.reject)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def ban(self, request, pk=None):
        return self._change_status(services.ban)

    @action(detail=True, methods=["post"])
    def unban(self, request, pk=None):
        return self._change_status(services.unban)

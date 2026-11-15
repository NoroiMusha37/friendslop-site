from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password2")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords don't match."})
        try:
            validate_password(attrs["password"], user=User(username=attrs["username"], email=attrs["email"]))
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)}) from e
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        # New accounts stay inactive until an admin approves them
        return User.objects.create_user(**validated_data, is_active=False)


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        user = User.objects.filter(username=attrs.get(self.username_field)).first()
        if user and not user.is_active and user.check_password(attrs.get("password", "")):
            if user.approved_at is None:
                raise exceptions.AuthenticationFailed("Your account is waiting for admin approval.", "pending_approval")
            raise exceptions.AuthenticationFailed("Your account has been banned.", "banned")
        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "status", "date_joined")


class MeSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source="is_superuser", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "is_admin")

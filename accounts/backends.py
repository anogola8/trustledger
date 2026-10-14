"""Authentication backend that accepts email OR username."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Authenticate with either email or username + password.
    Lookup order: email (case-insensitive) → username (case-insensitive).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        try:
            user = User.objects.get(
                Q(email__iexact=username) | Q(username__iexact=username)
            )
        except User.DoesNotExist:
            # Run the default hasher to mitigate timing attacks
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email__iexact=username).first()
            if user is None:
                user = User.objects.filter(username__iexact=username).first()
            if user is None:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
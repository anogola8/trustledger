from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


def role_required(*roles):
    """Role-based access control for function views."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            user = request.user
            if user.role in roles or (user.is_superuser and 'admin' in roles):
                return view(request, *args, **kwargs)
            raise PermissionDenied
        return wrapper
    return decorator


class _Role(BasePermission):
    role = None

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.role == self.role or (self.role == 'admin' and u.is_superuser)))


class IsWorker(_Role):
    role = 'worker'


class IsEmployer(_Role):
    role = 'employer'


class IsAdminRole(_Role):
    role = 'admin'

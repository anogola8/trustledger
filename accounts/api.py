from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit.services import log

from .models import User


class RegisterSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['worker', 'employer'])
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=120, required=False)
    organisation_name = serializers.CharField(max_length=150, required=False)

    def validate_username(self, v):
        if User.objects.filter(username__iexact=v).exists():
            raise serializers.ValidationError('Username already taken.')
        return v

    def validate_email(self, v):
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError('Email already registered.')
        return v.lower()

    def validate(self, data):
        from django.contrib.auth import password_validation
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            password_validation.validate_password(data['password'], User(username=data['username'], email=data['email']))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        if data['role'] == 'worker' and not data.get('full_name'):
            raise serializers.ValidationError({'full_name': 'Required for workers.'})
        if data['role'] == 'employer' and not data.get('organisation_name'):
            raise serializers.ValidationError({'organisation_name': 'Required for employers.'})
        return data

    @transaction.atomic
    def create(self, v):
        user = User(username=v['username'], email=v['email'], role=v['role'])
        user.set_password(v['password'])
        user.save()
        if v['role'] == 'worker':
            from workers.models import WorkerProfile
            WorkerProfile.objects.create(user=user, full_name=v['full_name'])
        else:
            from employers.models import EmployerProfile
            EmployerProfile.objects.create(user=user, organisation_name=v['organisation_name'])
        return user


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        log(user, 'user.register', 'user', user.pk, {'role': user.role, 'via': 'api'})
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'role': user.role}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        user = authenticate(request, username=request.data.get('username', ''), password=request.data.get('password', ''))
        if not user or not user.is_active:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        log(user, 'user.login', 'user', user.pk, {'via': 'api'})
        return Response({'token': token.key, 'role': user.role})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        u = request.user
        return Response({'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role})

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsEmployer
from workers.models import WorkerProfile

from . import services
from .models import Attestation
from .services import ServiceError
from .views import _can_view


class AttestationSerializer(serializers.ModelSerializer):
    worker = serializers.SlugRelatedField(slug_field='slug', queryset=WorkerProfile.objects.filter(user__is_active=True))
    employer_name = serializers.CharField(source='employer.organisation_name', read_only=True)
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)

    class Meta:
        model = Attestation
        fields = ['id', 'worker', 'worker_name', 'employer_name', 'role_title', 'description', 'start_date', 'end_date',
                  'status', 'verification_code', 'created_at', 'confirmed_at']
        read_only_fields = ['id', 'status', 'verification_code', 'created_at', 'confirmed_at']

    def validate(self, d):
        s, e = d.get('start_date'), d.get('end_date')
        if s and e and e < s:
            raise serializers.ValidationError({'end_date': 'End date cannot be before start date.'})
        return d


class AttestationListCreate(ListCreateAPIView):
    serializer_class = AttestationSerializer

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsEmployer()] if self.request.method == 'POST' else [IsAuthenticated()]

    def get_queryset(self):
        u = self.request.user
        qs = Attestation.objects.select_related('worker', 'employer')
        if u.is_worker:
            return qs.filter(worker=u.worker_profile)
        if u.is_employer:
            return qs.filter(employer=u.employer_profile)
        return qs if u.is_admin_role else qs.none()

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            att = services.create_attestation(request.user.employer_profile, d['worker'], d['role_title'], d.get('description', ''),
                                              d['start_date'], d.get('end_date'))
        except ServiceError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(self.get_serializer(att).data, status=status.HTTP_201_CREATED)


class AttestationDetail(RetrieveAPIView):
    serializer_class = AttestationSerializer

    def get_object(self):
        att = get_object_or_404(Attestation.objects.select_related('worker', 'employer'), pk=self.kwargs['pk'])
        if not _can_view(self.request.user, att):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied
        return att


class AttestationAction(APIView):
    action = None

    def post(self, request, pk):
        att = get_object_or_404(Attestation.objects.select_related('worker', 'employer'), pk=pk)
        try:
            if self.action == 'confirm':
                services.confirm(att, request.user)
            elif self.action == 'reject':
                services.reject(att, request.user)
            else:
                services.revoke(att, request.user, request.data.get('reason', ''))
        except ServiceError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        att.refresh_from_db()
        return Response(AttestationSerializer(att).data)

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from attestations.models import Attestation
from attestations.services import ServiceError
from core.permissions import IsAdminRole

from . import services
from .models import Dispute


class DisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = ['id', 'attestation', 'reason', 'status', 'decision_note', 'created_at', 'resolved_at']
        read_only_fields = ['id', 'status', 'decision_note', 'created_at', 'resolved_at']


class DisputeListCreate(ListAPIView):
    serializer_class = DisputeSerializer

    def get_queryset(self):
        u = self.request.user
        qs = Dispute.objects.all()
        if u.is_worker:
            return qs.filter(attestation__worker=u.worker_profile)
        if u.is_employer:
            return qs.filter(attestation__employer=u.employer_profile)
        return qs if u.is_admin_role else qs.none()

    def post(self, request):
        att = get_object_or_404(Attestation.objects.select_related('worker', 'employer'), pk=request.data.get('attestation'))
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response({'reason': 'Required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            d = services.open_dispute(att, request.user, reason)
        except ServiceError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(DisputeSerializer(d).data, status=status.HTTP_201_CREATED)


class DisputeResolveView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        d = get_object_or_404(Dispute, pk=pk)
        try:
            services.resolve(d, request.user, request.data.get('decision', ''), request.data.get('note', ''))
        except ServiceError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        d.refresh_from_db()
        return Response(DisputeSerializer(d).data)

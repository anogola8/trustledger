from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log
from core.permissions import IsAdminRole, IsEmployer

from .models import EmployerProfile


class EmployerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerProfile
        fields = ['id', 'organisation_name', 'org_type', 'registration_number', 'description', 'location', 'status', 'key_id', 'public_key']
        read_only_fields = ['id', 'status', 'key_id', 'public_key']


class EmployerMeView(RetrieveUpdateAPIView):
    serializer_class = EmployerSerializer
    permission_classes = [IsEmployer]

    def get_object(self):
        return self.request.user.employer_profile


class EmployerListView(ListAPIView):
    serializer_class = EmployerSerializer
    permission_classes = [IsAdminRole]
    queryset = EmployerProfile.objects.all()


class EmployerApproveView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        emp = get_object_or_404(EmployerProfile, pk=pk)
        emp.approve()
        log(request.user, 'admin.employer_approve', 'employer', emp.pk, {'via': 'api'})
        return Response(EmployerSerializer(emp).data)

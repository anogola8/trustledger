from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsWorker

from .models import Skill, WorkerProfile
from .timeline import build_timeline


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'level', 'years']


class WorkerSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = WorkerProfile
        fields = ['slug', 'full_name', 'headline', 'bio', 'location', 'show_skills', 'show_certificates', 'skills']
        read_only_fields = ['slug']


class WorkerMeView(RetrieveUpdateAPIView):
    serializer_class = WorkerSerializer
    permission_classes = [IsWorker]

    def get_object(self):
        return self.request.user.worker_profile


class SkillListCreate(ListCreateAPIView):
    serializer_class = SkillSerializer
    permission_classes = [IsWorker]
    pagination_class = None

    def get_queryset(self):
        return self.request.user.worker_profile.skills.all()

    def perform_create(self, serializer):
        w = self.request.user.worker_profile
        if w.skills.filter(name__iexact=serializer.validated_data['name']).exists():
            raise serializers.ValidationError({'name': 'Skill already listed.'})
        serializer.save(worker=w)


class WorkerPublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        w = get_object_or_404(WorkerProfile, slug=slug, user__is_active=True)
        data = {'slug': w.slug, 'full_name': w.full_name, 'headline': w.headline, 'location': w.location,
                'skills': [s.name for s in w.skills.all()] if w.show_skills else [],
                'verified_experience': [{'role': i['title'], 'employer': i['org'], 'start': i['start'], 'end': i['end'], 'code': i['code']}
                                        for i in build_timeline(w) if i['kind'] == 'verified']}
        return Response(data)

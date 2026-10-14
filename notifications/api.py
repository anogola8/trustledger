from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'url', 'is_read', 'created_at']


class NotificationList(ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return self.request.user.notifications.all()


class NotificationRead(APIView):
    def post(self, request, pk):
        n = get_object_or_404(Notification, pk=pk, user=request.user)
        n.is_read = True
        n.save(update_fields=['is_read'])
        return Response(NotificationSerializer(n).data)

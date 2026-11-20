from rest_framework import serializers

from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ("id", "code", "name", "status")
        read_only_fields = fields


class ClientCreateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=255)


class ClientUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    status = serializers.ChoiceField(choices=Client.Status.choices, required=False)

from rest_framework import serializers


class DecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=False,
    )
    version = serializers.IntegerField(min_value=1, required=False)

from rest_framework import serializers
from .models import Device, ChatMessage

# --- Analysis Schemas ---
# This is a plain Serializer, not a ModelSerializer, because it doesn't
# map directly to a model. It's for validating the LLM output.
class AnalysisResultSerializer(serializers.Serializer):
    complexity = serializers.CharField(max_length=50)
    components = serializers.ListField(child=serializers.CharField(max_length=100))
    operating_voltage = serializers.CharField(max_length=50)
    description = serializers.CharField()

# --- Chat Message Schemas ---
class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at', 'device_id']

# --- Device Schemas ---
# Corresponds to FastAPI's DeviceResponse
class DeviceResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'image', 'created_at', 'complexity',
            'components', 'operating_voltage', 'description'
        ]

# Corresponds to FastAPI's DeviceWithMessages
class DeviceWithMessagesSerializer(serializers.ModelSerializer):
    # This nests the ChatMessageSerializer, automatically fetching
    # related messages via the 'chat_messages' related_name.
    chat_messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Device
        fields = [
            'id', 'name', 'image', 'created_at', 'complexity',
            'components', 'operating_voltage', 'description', 'chat_messages'
        ]
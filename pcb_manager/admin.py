from django.contrib import admin
from .models import Device, ChatMessage

admin.site.register(Device)
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'device', 'role', 'created_at')  # Add 'id' here
    list_filter = ('role', 'created_at')  # Optional: add filters
    search_fields = ('content', 'device__name', 'device__user__username')  # Optional: search bar

from django.db import models
from django.contrib.auth.models import User
from pydantic import BaseModel
from typing import List

class PCBAnalysisResult(BaseModel):
    complexity: str
    components: List[str]
    operating_voltage: str
    description: str

class Device(models.Model):
    # Add user field to associate devices with users
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    name = models.CharField(max_length=255, db_index=True)
    # ImageField handles file uploads and stores the path
    image = models.ImageField(upload_to='images/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # AI Analysis fields
    complexity = models.CharField(max_length=50)
    components = models.JSONField()
    operating_voltage = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        # Add ordering and unique constraint if needed
        ordering = ['-created_at']
        # Optional: Ensure unique device names per user
        # unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    # This method is useful for cleaning up the image file when a device is deleted
    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)  # delete file from storage
        super().delete(*args, **kwargs)

class ChatMessage(models.Model):
    # The 'related_name' allows us to do device.chat_messages.all()
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="chat_messages")
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('ai', 'AI')])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']  # Ensures history is always in order

    def __str__(self):
        return f"{self.role} message for {self.device.name} by {self.device.user.username}"
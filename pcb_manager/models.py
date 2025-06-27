from django.db import models
from pydantic import BaseModel
from typing import List

class PCBAnalysisResult(BaseModel):
    complexity: str
    components: List[str]
    operating_voltage: str
    description: str

class Device(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    # ImageField handles file uploads and stores the path
    image = models.ImageField(upload_to='images/')
    created_at = models.DateTimeField(auto_now_add=True)

    # AI Analysis fields
    complexity = models.CharField(max_length=50)
    components = models.JSONField()
    operating_voltage = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

    # This method is useful for cleaning up the image file when a device is deleted
    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)  # delete file from storage
        super().delete(*args, **kwargs)



class ChatMessage(models.Model):
    # The 'related_name' allows us to do device.chat_messages.all()
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="chat_messages")
    role = models.CharField(max_length=10)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # Ensures history is always in order

    def __str__(self):
        return f"{self.role} message for {self.device.name}"
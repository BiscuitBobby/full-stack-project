from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

# --- Analysis Schemas ---
class AnalysisResult(BaseModel):
    complexity: str
    components: List[str]
    operating_voltage: str
    description: str

# --- Chat Message Schemas ---
class ChatMessageBase(BaseModel):
    role: str
    content: str

class ChatMessageCreate(ChatMessageBase):
    device_id: int

class ChatMessage(ChatMessageBase):
    id: int
    device_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Device Schemas ---
class DeviceBase(BaseModel):
    name: str
    image_filename: str
    complexity: str
    components: List[str]
    operating_voltage: str
    description: str

class DeviceCreate(DeviceBase):
    pass

# Device response without chat messages (for list endpoints and creation)
class DeviceResponse(DeviceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Device response with chat messages (for specific device endpoint)
class DeviceWithMessages(DeviceBase):
    id: int
    created_at: datetime
    chat_messages: List[ChatMessage] = []

    class Config:
        from_attributes = True

# Keep the original Device schema for backward compatibility
class Device(DeviceWithMessages):
    pass
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base # Assuming you have this import

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    image_filename = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # AI Analysis fields
    complexity = Column(String)
    components = Column(JSON) 
    operating_voltage = Column(String)
    description = Column(String)
    
    # Relationship to ChatMessage
    chat_messages = relationship("ChatMessage", back_populates="device", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "ai"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="chat_messages")
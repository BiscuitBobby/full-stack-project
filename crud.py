from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import models, schemas
import os
from pathlib import Path

async def get_devices(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Retrieve all devices with pagination (without chat messages for performance)."""
    query = (
        select(models.Device)
        .order_by(models.Device.id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_device_basic(db: AsyncSession, device_id: int):
    """Retrieve a single device by its ID (without chat messages)."""
    query = select(models.Device).where(models.Device.id == device_id)
    result = await db.execute(query)
    return result.scalars().first()

async def get_device(db: AsyncSession, device_id: int):
    """Retrieve a single device by its ID with chat messages."""
    query = (
        select(models.Device)
        .options(selectinload(models.Device.chat_messages))
        .where(models.Device.id == device_id)
    )
    result = await db.execute(query)
    return result.scalars().first()

async def create_device(db: AsyncSession, device: schemas.DeviceCreate):
    """Create a new device entry in the database."""
    db_device = models.Device(
        name=device.name,
        image_filename=device.image_filename,
        complexity=device.complexity,
        components=device.components,
        operating_voltage=device.operating_voltage,
        description=device.description,
    )
    db.add(db_device)
    await db.commit()
    await db.refresh(db_device)
    return db_device

async def delete_device(db: AsyncSession, device_id: int):
    """
    Delete a device and its associated image file.
    Returns True if deletion was successful, False if device not found.
    """
    # First, get the device to access the image filename
    device = await get_device_basic(db, device_id)
    if device is None:
        return False
    
    # Store image filename for file deletion
    image_filename = device.image_filename
    
    # Delete the device (this will cascade delete chat messages due to the relationship)
    await db.delete(device)
    await db.commit()
    
    # Delete the associated image file if it exists
    if image_filename:
        try:
            # Construct the full path to the image file
            base_dir = Path(__file__).resolve().parent
            image_path = base_dir / "static" / "images" / image_filename
            
            if image_path.exists():
                os.remove(image_path)
                print(f"[INFO] Deleted image file: {image_path}")
            else:
                print(f"[WARNING] Image file not found: {image_path}")
        except Exception as e:
            print(f"[ERROR] Failed to delete image file {image_filename}: {str(e)}")
            # Don't raise the exception - device deletion should succeed even if file deletion fails
    
    return True

# --- Chat History CRUD Functions ---

async def get_chat_history(db: AsyncSession, device_id: int):
    """Retrieve the chat history for a specific device, ordered by creation time."""
    result = await db.execute(
        select(models.ChatMessage)
        .where(models.ChatMessage.device_id == device_id)
        .order_by(models.ChatMessage.created_at)
    )
    return result.scalars().all()

async def create_chat_message(db: AsyncSession, message: schemas.ChatMessageCreate):
    """Saves a new chat message to the database."""
    db_message = models.ChatMessage(
        device_id=message.device_id,
        role=message.role,
        content=message.content
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message
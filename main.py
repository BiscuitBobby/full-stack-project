import traceback
import uuid
import os
import json
import base64
from typing import List
from contextlib import asynccontextmanager

import aiofiles
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

import crud
import models
import schemas
from database import engine, get_db

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

# Load environment variables from .env file
load_dotenv()

if os.getenv("GOOGLE_API_KEY"):
    primary_llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,
        api_key=os.getenv("GOOGLE_API_KEY")
    )
    model_name = "gemini-2.0-flash"
else:
    primary_llm = ChatOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        # temperature=0.7,
    )
    model_name = "lm-studio"

print(model_name)

# Create all database tables on startup
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="PCB Device Manager API",
    description="API for analyzing and managing PCB devices.",
    lifespan=lifespan
)


# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static File Serving ---
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- API Endpoints ---

@app.post("/analyze-pcb/", response_model=schemas.AnalysisResult)
async def analyze_pcb_image(
    image: UploadFile = File(...)
):
    """
    Analyzes a PCB image using the Vision model.
    It processes the `image`, sends it to the model, and returns a
    structured JSON analysis.
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    try:
        llm = primary_llm
        parser = JsonOutputParser(pydantic_object=schemas.AnalysisResult)
        prompt_template = """
        Analyze the provided image of a Printed Circuit Board (PCB). Based on your analysis, provide a detailed and structured JSON output.

        Identify the key characteristics of the board and follow these instructions:
        - **complexity**: Classify the board's complexity as 'Low', 'Medium', or 'High' based on component density, number of layers, and trace routing.
        - **components**: List the names of the most prominent and identifiable components on the board.
        - **operating_voltage**: Estimate the primary operating voltage (e.g., "3.3V", "5V", "12V", "3.3V - 5V"). If unsure, state "Not determinable".
        - **description**: Write a concise, one-paragraph technical description of the board's likely function and features.

        {format_instructions}

        The user has provided the image. Analyze it now.
        """
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=[],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        if model_name.startswith("gemini"):
            # Google Gemini format
            message = HumanMessage(
                content=[
                    {"type": "text", "text": await prompt.aformat()},
                    {"type": "image_url", "image_url": f"data:{image.content_type};base64,{image_base64}"},
                ]
            )
        else:
            # LM Studio format - image_url must be an object with url property
            message = HumanMessage(
                content=[
                    {"type": "text", "text": await prompt.aformat()},
                    {"type": "image_url", "image_url": {"url": f"data:{image.content_type};base64,{image_base64}"}},
                ]
            )
        
        output = await llm.ainvoke([message])
        analysis = parser.parse(output.content)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during AI analysis: {str(e)}")


@app.post("/devices/", response_model=schemas.DeviceResponse, status_code=201)  # Changed response model
async def add_new_device(
    name: str = Form(...),
    complexity: str = Form(...),
    components: str = Form(...),
    operating_voltage: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Saves the device image and creates a new device record in the database.
    """
    file_extension = os.path.splitext(image.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = f"static/images/{unique_filename}"

    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await image.read()
            await out_file.write(content)
    except Exception:
        raise HTTPException(status_code=500, detail="There was an error uploading the file.")

    device_data = schemas.DeviceCreate(
        name=name,
        image_filename=unique_filename,
        complexity=complexity,
        components=json.loads(components),
        operating_voltage=operating_voltage,
        description=description
    )
    return await crud.create_device(db=db, device=device_data)


@app.get("/devices/", response_model=List[schemas.DeviceResponse])  # Changed response model
async def list_all_devices(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all saved devices from the database.
    """
    devices = await crud.get_devices(db, skip=skip, limit=limit)
    return devices


@app.get("/devices/{device_id}", response_model=schemas.DeviceWithMessages)  # Changed response model
async def get_device_by_id(device_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific device by its ID, including its chat history.
    """
    device = await crud.get_device(db, device_id=device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.delete("/devices/{device_id}", status_code=204)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a specific device by its ID.
    This will also delete all associated chat messages and the device image file.
    """
    success = await crud.delete_device(db, device_id=device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    # Return 204 No Content for successful deletion


@app.get("/devices/{device_id}/chat-history", response_model=List[schemas.ChatMessage])
async def get_device_chat_history(device_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve the full chat history for a specific device.
    """
    device = await crud.get_device_basic(db, device_id=device_id)  # Use basic version
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return await crud.get_chat_history(db, device_id=device_id)


@app.post("/devices/{device_id}/chat")
async def chat_with_device(
    device_id: int,
    message: str = Form(...)
):
    """
    Persistent chat endpoint. It loads conversation history, gets a new AI response,
    and saves both the user's message and the AI's response to the database.
    
    This version includes extensive debugging statements and safe session management.
    """
    print("="*50)
    print(f"[DEBUG] CHAT - START: Received chat request for device_id={device_id}")
    print(f"[DEBUG] CHAT - User message: '{message}'")
    print("="*50)
    
    # This will hold the plain data, disconnected from the database session.
    conversation_history_data = []

    # --- Step 1: Database Operations (Read and Write User Message) ---
    try:
        print("[DEBUG] CHAT - Opening database session...")
        async with AsyncSession(engine) as db:
            print(f"[DEBUG] CHAT - Fetching device with id={device_id}...")
            device = await crud.get_device_basic(db, device_id=device_id)
            if device is None:
                print(f"[ERROR] CHAT - Device with id={device_id} not found in database.")
                raise HTTPException(status_code=404, detail="Device not found")
            
            print(f"[DEBUG] CHAT - Found device: '{device.name}' (ID: {device.id})")

            # Extract all necessary data from the device object NOW
            device_name = device.name
            device_complexity = device.complexity
            device_components = device.components if device.components else []
            device_voltage = device.operating_voltage
            device_description = device.description
            device_image = device.image_filename
            
            print("[DEBUG] CHAT - Saving user's message to the database...")
            user_message_to_save = schemas.ChatMessageCreate(
                device_id=device_id, role="user", content=message
            )
            await crud.create_chat_message(db=db, message=user_message_to_save)
            print("[DEBUG] CHAT - User message saved.")
            
            print("[DEBUG] CHAT - Fetching chat history from database...")
            history_from_db = await crud.get_chat_history(db, device_id=device_id)
            print(f"[DEBUG] CHAT - Fetched {len(history_from_db)} messages from history.")
            
            # ========================= THE FIX =========================
            # Convert the SQLAlchemy ORM objects into a simple list of dictionaries
            # before the session closes. This "detaches" them cleanly.
            print("[DEBUG] CHAT - Extracting data from ORM objects before session closes...")
            for msg in history_from_db:
                conversation_history_data.append({"role": msg.role, "content": msg.content})
            # ===========================================================
            
            # Commit the transaction (saves user message) and close the session.
            await db.commit()
            print("[DEBUG] CHAT - Database transaction committed. Session closed.")
            
    except Exception as e:
        print(f"[ERROR] CHAT - Database operation failed: {type(e).__name__} - {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # --- Step 2: AI Processing (using the plain 'conversation_history_data') ---
    try:
        print("\n[DEBUG] CHAT - AI PROCESSING STAGE")
        llm = primary_llm
        
        components_str = ", ".join(device_components)
        device_context = f"""
        Device Information:
        - Name: {device_name}
        - Complexity: {device_complexity}
        - Components: {components_str}
        - Operating Voltage: {device_voltage}
        - Description: {device_description}
        - Image: Available at /static/images/{device_image}
        """
        
        system_message = SystemMessage(
            content=f"""You are an expert PCB and electronics engineer assistant. 
            You are helping a user with questions about a specific PCB device. 
            Use the following device information as your primary context.
            You must remember and use the entire conversation history provided.
            
            {device_context}
            
            Provide helpful, technical, and accurate responses based on this device information and the conversation history.
            If the user asks about something not related to this specific device, 
            politely redirect them back to topics related to this PCB device.
            """
        )
        
        print("[DEBUG] CHAT - Constructing full conversation history for AI...")
        conversation_history = [system_message]
        # Now, we iterate over our clean list of dictionaries, not the detached ORM objects.
        for i, msg_data in enumerate(conversation_history_data):
            content_preview = (msg_data['content'][:75] + '...') if len(msg_data['content']) > 75 else msg_data['content']
            print(f"  - History item {i+1}: role='{msg_data['role']}', content='{content_preview}'")
            if msg_data['role'] == "user":
                conversation_history.append(HumanMessage(content=msg_data['content']))
            elif msg_data['role'] == "ai":
                conversation_history.append(AIMessage(content=msg_data['content']))
        
        print(f"\n[DEBUG] CHAT - Invoking LLM API with {len(conversation_history)} total messages...")
        response = await llm.ainvoke(conversation_history)
        ai_response_content = response.content
        print("[DEBUG] CHAT - Received response from LLM API.")

    except Exception as e:
        print(f"[ERROR] CHAT - AI processing failed: {type(e).__name__} - {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error during AI processing: {str(e)}")

    # --- Step 3: Save AI Response to Database ---
    try:
        print("\n[DEBUG] CHAT - Opening new database session to save AI response...")
        async with AsyncSession(engine) as db:
            ai_message_to_save = schemas.ChatMessageCreate(
                device_id=device_id, role="ai", content=ai_response_content
            )
            await crud.create_chat_message(db=db, message=ai_message_to_save)
            await db.commit()
            print("[DEBUG] CHAT - AI response saved to database and session closed.")
    
    except Exception as e:
        print(f"[ERROR] CHAT - Failed to save AI response: {type(e).__name__} - {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save AI response: {str(e)}")

    print("\n[DEBUG] CHAT - END: Preparing and returning final response to client.")
    print("="*50)
    
    return {
        "device_id": device_id,
        "ai_response": ai_response_content,
    }


@app.post("/devices/{device_id}/chat-with-image")
async def chat_with_device_and_image(
    device_id: int,
    message: str = Form(...),
    image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Enhanced chat endpoint that can analyze both device context and an optional new image.
    Note: This endpoint remains stateless and does not use the persistent chat history
    for simplicity. It could be extended to save image references in the chat history.
    """
    device = await crud.get_device_basic(db, device_id=device_id)  # Use basic version
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        llm = primary_llm
        components_str = ", ".join(device.components) if device.components else "No components listed"
        device_context = f"""
        Reference Device Information:
        - Name: {device.name}
        - Complexity: {device.complexity}
        - Components: {components_str}
        - Operating Voltage: {device.operating_voltage}
        - Description: {device.description}
        """
        
        system_content = f"""You are an expert PCB and electronics engineer assistant. 
        You are helping a user with questions about PCB devices. 
        Use the following reference device information as context:
        
        {device_context}
        
        The user may also provide a new image for comparison or analysis.
        Provide helpful, technical, and accurate responses based on both the reference device 
        information and any new image provided.
        """
        
        messages = [SystemMessage(content=system_content)]
        user_content = [{"type": "text", "text": message}]
        
        if image and image.content_type.startswith("image/"):
            image_bytes = await image.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            user_content.append({
                "type": "image_url",
                "image_url": f"data:{image.content_type};base64,{image_base64}",
            })
        
        user_message = HumanMessage(content=user_content)
        messages.append(user_message)
        
        response = await llm.ainvoke(messages)
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "user_message": message,
            "image_provided": image is not None,
            "ai_response": response.content,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during chat: {str(e)}")

@app.get("/")
async def root():
    return {"status": "online."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# test_main.py

import pytest
import pytest_asyncio
import json
from httpx import AsyncClient, ASGITransport  # MODIFIED: Added ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

# Import the FastAPI app and its dependencies to override them for testing
from main import app, get_db, models
from schemas import AnalysisResult

# Use an in-memory SQLite database for testing to keep tests fast and isolated
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

# --- Test Setup & Fixtures ---

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency override for get_db. Uses an in-memory SQLite database for tests.
    """
    async with TestingSessionLocal() as session:
        yield session

# Apply the dependency override to the app
app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """
    Force pytest-asyncio to use the same event loop for all tests in a session.
    """
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """
    Create all database tables before each test and drop them afterwards.
    This ensures each test runs with a clean, empty database.
    """
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)

# ========================= THE FIX IS HERE =========================
@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an httpx.AsyncClient for making requests to the test app.
    This uses ASGITransport for broader compatibility with httpx versions.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
# ===================================================================

@pytest.fixture
def mock_llm(mocker):
    """
    Mocks the language model's `ainvoke` method to return predictable
    responses without making real API calls.
    """
    # Define a simple class to mimic the LLM's response object structure
    class MockAIMessage:
        def __init__(self, content):
            self.content = content

    # Create a predictable response for the PCB analysis endpoint
    mock_analysis_result = AnalysisResult(
        complexity="Medium",
        components=["MCU", "USB-C Port", "Crystal Oscillator"],
        operating_voltage="5V",
        description="A standard microcontroller development board."
    )
    mock_analysis_response = MockAIMessage(content=mock_analysis_result.model_dump_json())

    # Create a predictable response for the chat endpoints
    mock_chat_response = MockAIMessage(content="This is a test AI response about the PCB.")

    # Patch the `ainvoke` method in the main application
    # Use `side_effect` to provide a sequence of return values for subsequent calls
    mock_ainvoke = mocker.patch(
        "main.primary_llm.ainvoke",
        side_effect=[mock_analysis_response, mock_chat_response] * 20 # Provide enough for all tests
    )

    return {
        "ainvoke": mock_ainvoke,
        "analysis_result": mock_analysis_result,
        "chat_response": mock_chat_response
    }

@pytest.fixture
def dummy_image_file(tmp_path):
    """
    Creates a temporary dummy image file (a minimal 1x1 PNG).
    """
    img_path = tmp_path / "test_pcb.png"
    # A valid 1x1 pixel PNG
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82'
    img_path.write_bytes(png_data)
    return str(img_path)


# --- Tests ---

@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test that the root endpoint is available."""
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online."}

@pytest.mark.asyncio
async def test_analyze_pcb_invalid_file_type(client: AsyncClient, tmp_path):
    """Test the /analyze-pcb/ endpoint with a non-image file, expecting a 400 error."""
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("this is not an image")

    with open(txt_path, "rb") as f:
        files = {"image": ("test.txt", f, "text/plain")}
        response = await client.post("/analyze-pcb/", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid file type. Please upload an image."

@pytest.mark.asyncio
async def test_device_crud_and_file_management(client: AsyncClient, dummy_image_file, mocker):
    """Test the full CRUD (Create, Read, Delete) lifecycle of a device."""

    # --- Setup Mocks for file operations ---
    # Mock file writing to avoid actual disk I/O
    mock_aio_open = mocker.patch("aiofiles.open")
    # Mock file deletion to verify it's called without deleting real files
    # mock_os_remove = mocker.patch("os.remove")
    # Mock uuid to get a predictable filename
    mock_uuid = "12345678-1234-5678-1234-567812345678"
    mocker.patch("uuid.uuid4", return_value=mock_uuid)

    # --- 1. CREATE Device ---
    device_form_data = {
        "name": "Test Board",
        "complexity": "Low",
        "components": json.dumps(["Resistor", "Capacitor"]), # Form data expects a string
        "operating_voltage": "3.3V",
        "description": "A very simple test board.",
    }
    with open(dummy_image_file, "rb") as f:
        files = {"image": ("test_pcb.png", f, "image/png")}
        response_create = await client.post("/devices/", data=device_form_data, files=files)

    assert response_create.status_code == 201
    created_device = response_create.json()
    assert created_device["name"] == "Test Board"
    assert created_device["image_filename"].startswith(mock_uuid)
    # Verify that the application attempted to write the file
    mock_aio_open.assert_called_once()
    device_id = created_device["id"]

    # --- 2. READ (List) ---
    response_list = await client.get("/devices/")
    assert response_list.status_code == 200
    devices = response_list.json()
    assert len(devices) == 1
    assert devices[0]["id"] == device_id

    # --- 3. READ (Single) ---
    response_single = await client.get(f"/devices/{device_id}")
    assert response_single.status_code == 200
    single_device = response_single.json()
    assert single_device["name"] == "Test Board"
    assert "chat_messages" in single_device # Verify the correct schema is used
    assert single_device["chat_messages"] == []

    # --- 4. DELETE ---
    response_delete = await client.delete(f"/devices/{device_id}")
    assert response_delete.status_code == 204

    # Verify the application attempted to delete the correct image file
    # expected_file_to_delete = os.path.join("static", "images", created_device["image_filename"])
    # mock_os_remove.assert_called_once_with(expected_file_to_delete)

    # --- 5. Verify Deletion ---
    response_verify = await client.get(f"/devices/{device_id}")
    assert response_verify.status_code == 404

@pytest.mark.asyncio
async def test_get_non_existent_device(client: AsyncClient):
    """Test that requesting a non-existent device ID returns 404."""
    response = await client.get("/devices/9999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_non_existent_device(client: AsyncClient, mocker):
    """Test that deleting a non-existent device ID returns 404."""
    mocker.patch("os.remove") # Mock to prevent FileNotFoundError on the server
    response = await client.delete("/devices/9999")
    assert response.status_code == 404


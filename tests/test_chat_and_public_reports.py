# import pytest
# from fastapi.testclient import TestClient
# from sqlalchemy.orm import Session
# from unittest.mock import MagicMock, patch
# from datetime import date, datetime

# from app.main import app  # Import your FastAPI app
# from app.routers.public_reports import get_vector_store  # Import to override
# from src.database.vector_operations import VectorStore  # For mocking VectorStore
# from src.models.data_model import ScamReports, PersonDetails, ReportPersonsLink, Conversations, ReportStatus, PersonRole  # SQLAlchemy models
# from app.model import PublicReportSubmission, PublicReportResponse  # From model.py

# # Fixtures from conftest.py: client and mock_db are available

# # Fixture to mock CRUDOperations for public_reports tests
# @pytest.fixture
# def mock_crud_operations():
#     with patch("app.routers.public_reports.CRUDOperations") as mock_crud:
#         yield mock_crud

# # Fixture to mock ConversationManager to prevent real execution
# @pytest.fixture
# def mock_conversation_manager():
#     with patch("app.routers.chat.ConversationManager") as mock_manager:  # Patch at the import location in chat.py
#         instance = mock_manager.return_value
#         instance.process_user_query = MagicMock(return_value={
#             "response": "Mock AI response",
#             "conversation_id": 1,
#             "structured_data": {"scam_type": "phishing"}
#         })
#         yield instance

# # --- Simple Tests for public_reports.py endpoints ---

# def test_submit_public_report_success(client: TestClient, mock_db: Session, mock_crud_operations):
#     # Mock query for conversation (assume found)
#     mock_conv = MagicMock(conversation_id=2)
#     mock_db.query.return_value.filter.return_value.first.return_value = mock_conv

#     # Pre-create specific CRUD mocks for each model
#     person_crud_mock = MagicMock()
#     person_crud_mock.create.return_value = MagicMock(person_id=1)
    
#     report_crud_mock = MagicMock()
#     report_crud_mock.create.return_value = MagicMock(report_id=1)
    
#     link_crud_mock = MagicMock()
#     link_crud_mock.create.return_value = MagicMock()
    
#     conv_crud_mock = MagicMock()
#     conv_crud_mock.update.return_value = mock_conv

#     # Set side_effect to return the appropriate mock based on model
#     def crud_side_effect(model):
#         if model == PersonDetails:
#             return person_crud_mock
#         elif model == ScamReports:
#             return report_crud_mock
#         elif model == ReportPersonsLink:
#             return link_crud_mock
#         elif model == Conversations:
#             return conv_crud_mock
#         return MagicMock()  # Fallback

#     mock_crud_operations.side_effect = crud_side_effect

#     # Mock VectorStore override
#     mocked_vs = MagicMock(spec=VectorStore)
#     mocked_vs.get_embedding.return_value = [0.1] * 384  # Fake embedding
#     app.dependency_overrides[get_vector_store] = lambda: mocked_vs

#     request_data = {
#         "first_name": "John",
#         "last_name": "Doe",
#         "contact_no": "+123456789",
#         "email": "john@example.com",
#         "scam_incident_date": "2023-01-01",
#         "scam_incident_description": "I was scammed via email.",
#         "role": "victim",
#         "conversation_id": 2
#     }

#     response = client.post("/public/reports/submit", json=request_data)

#     assert response.status_code == 200
#     assert response.json()["report_id"] == 1
#     assert response.json()["conversation_id"] == 2
#     # Ensure embedding was called
#     mocked_vs.get_embedding.assert_called_once_with("I was scammed via email.")

#     # Clean up vector store override
#     del app.dependency_overrides[get_vector_store]

# def test_submit_public_report_missing_fields(client: TestClient):
#     request_data = {
#         "first_name": "John",
#     }

#     response = client.post("/public/reports/submit", json=request_data)

#     assert response.status_code == 422  # Pydantic validation error
#     detail = response.json()["detail"]
#     assert any("field required" in err["msg"] for err in detail)  # Check Pydantic error format

# def test_submit_public_report_invalid_role(client: TestClient):
#     request_data = {
#         "first_name": "John",
#         "last_name": "Doe",
#         "contact_no": "+123456789",
#         "email": "john@example.com",
#         "scam_incident_date": "2023-01-01",
#         "scam_incident_description": "I was scammed.",
#         "role": "invalid_role"
#     }

#     response = client.post("/public/reports/submit", json=request_data)

#     assert response.status_code == 400
#     assert "Invalid role" in response.json()["detail"]

# def test_submit_public_report_invalid_date(client: TestClient):
#     request_data = {
#         "first_name": "John",
#         "last_name": "Doe",
#         "contact_no": "+123456789",
#         "email": "john@example.com",
#         "scam_incident_date": "3000-01-01",
#         "scam_incident_description": "I was scammed.",
#         "role": "victim"  # Add to avoid default issues
#     }

#     response = client.post("/public/reports/submit", json=request_data)

#     assert response.status_code == 400
#     assert "Invalid dates" in response.json()["detail"]

# # --- Simple Tests for chat.py endpoints ---

# def test_send_message_new_conversation_success(client: TestClient, mock_conversation_manager):
#     request_data = {
#         "query": "Hello, I need help reporting a scam."
#     }

#     response = client.post("/chat/message", json=request_data)

#     assert response.status_code == 200
#     response_json = response.json()
#     assert "response" in response_json
#     assert response_json["response"] == "Mock AI response"
#     assert "conversation_id" in response_json
#     mock_conversation_manager.process_user_query.assert_called_once_with(
#         "Hello, I need help reporting a scam.", None  # Positional args
#     )

# def test_send_message_existing_conversation_success(client: TestClient, mock_conversation_manager):
#     request_data = {
#         "query": "More details about the scam.",
#         "conversation_id": 1
#     }

#     response = client.post("/chat/message", json=request_data)

#     assert response.status_code == 200
#     response_json = response.json()
#     assert "response" in response_json
#     assert response_json["response"] == "Mock AI response"
#     mock_conversation_manager.process_user_query.assert_called_once_with(
#         "More details about the scam.", 1  # Positional args
#     )

# def test_send_message_error(client: TestClient, mock_conversation_manager):
#     mock_conversation_manager.process_user_query.side_effect = Exception("Mock error")

#     request_data = {
#         "query": "Error query"
#     }

#     response = client.post("/chat/message", json=request_data)

#     assert response.status_code == 500
#     assert "detail" in response.json()
#     assert "Mock error" in response.json()["detail"]


import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch
from datetime import date, datetime

from app.main import app  # Import your FastAPI app
from app.routers.public_reports import get_vector_store  # Import to override
from src.database.vector_operations import VectorStore  # For mocking VectorStore
from src.models.data_model import ScamReports, PersonDetails, ReportPersonsLink, Conversations, ReportStatus, PersonRole  # SQLAlchemy models
from app.model import PublicReportSubmission, PublicReportResponse  # From model.py

# Import global managers dict to reset it across tests (fixes state persistence issue)
from app.routers.chat import managers

# Fixtures from conftest.py: client and mock_db are available (assuming you have them; if not, add @pytest.fixture for client = TestClient(app))

# Auto-use fixture to reset global 'managers' dict in chat.py (prevents cross-test pollution)
@pytest.fixture(autouse=True)
def reset_managers():
    managers.clear()  # Clear before test
    yield
    managers.clear()  # Clear after (redundant but safe)

# Fixture to mock CRUDOperations for public_reports tests
@pytest.fixture
def mock_crud_operations():
    with patch("app.routers.public_reports.CRUDOperations") as mock_crud:
        yield mock_crud

# Fixture to mock ConversationManager to prevent real execution
@pytest.fixture
def mock_conversation_manager():
    with patch("app.routers.chat.ConversationManager") as mock_manager:  # Patch at the import location in chat.py
        instance = mock_manager.return_value
        instance.process_user_query = MagicMock(return_value={
            "response": "Mock AI response",
            "conversation_id": 1,
            "structured_data": {
                "scam_incident_date": "",
                "scam_type": "phishing",
                "scam_approach_platform": "",
                "scam_communication_platform": "",
                "scam_transaction_type": "",
                "scam_beneficiary_platform": "",
                "scam_beneficiary_identifier": "",
                "scam_contact_no": "",
                "scam_email": "",
                "scam_moniker": "",
                "scam_url_link": "",
                "scam_amount_lost": 0,
                "scam_incident_description": ""
            }  # Align with actual return in conversation_manager_new.py
        })
        yield instance

# --- Simple Tests for public_reports.py endpoints ---

def test_submit_public_report_success(client: TestClient, mock_db: Session, mock_crud_operations):
    # Mock query for conversation (assume found)
    mock_conv = MagicMock(conversation_id=2)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_conv

    # Pre-create specific CRUD mocks for each model
    person_crud_mock = MagicMock()
    person_crud_mock.create.return_value = MagicMock(person_id=1)
    
    report_crud_mock = MagicMock()
    report_crud_mock.create.return_value = MagicMock(report_id=1)
    
    link_crud_mock = MagicMock()
    link_crud_mock.create.return_value = MagicMock()
    
    conv_crud_mock = MagicMock()
    conv_crud_mock.update.return_value = mock_conv

    # Set side_effect to return the appropriate mock based on model
    def crud_side_effect(model):
        if model == PersonDetails:
            return person_crud_mock
        elif model == ScamReports:
            return report_crud_mock
        elif model == ReportPersonsLink:
            return link_crud_mock
        elif model == Conversations:
            return conv_crud_mock
        return MagicMock()  # Fallback

    mock_crud_operations.side_effect = crud_side_effect

    # Mock VectorStore override
    mocked_vs = MagicMock(spec=VectorStore)
    mocked_vs.get_embedding.return_value = [0.1] * 384  # Fake embedding
    app.dependency_overrides[get_vector_store] = lambda: mocked_vs

    request_data = {
        "first_name": "John",
        "last_name": "Doe",
        "contact_no": "+123456789",
        "email": "john@example.com",
        "scam_incident_date": "2023-01-01",
        "scam_incident_description": "I was scammed via email.",
        "role": "victim",
        "conversation_id": 2
    }

    response = client.post("/public/reports/submit", json=request_data)

    assert response.status_code == 200
    assert response.json()["report_id"] == 1
    assert response.json()["conversation_id"] == 2
    # Ensure embedding was called
    mocked_vs.get_embedding.assert_called_once_with("I was scammed via email.")

    # Clean up vector store override
    del app.dependency_overrides[get_vector_store]

def test_submit_public_report_missing_fields(client: TestClient):
    request_data = {
        "first_name": "John",
    }

    response = client.post("/public/reports/submit", json=request_data)

    assert response.status_code == 422  # Pydantic validation error (happens before custom check)
    detail = response.json()["detail"]
    assert any("Field required" in err["msg"] for err in detail)  # Fixed: Match Pydantic v2 exact msg ("Field required")

def test_submit_public_report_invalid_role(client: TestClient):
    request_data = {
        "first_name": "John",
        "last_name": "Doe",
        "contact_no": "+123456789",
        "email": "john@example.com",
        "scam_incident_date": "2023-01-01",
        "scam_incident_description": "I was scammed.",
        "role": "invalid_role"
    }

    response = client.post("/public/reports/submit", json=request_data)

    assert response.status_code == 400
    assert "Invalid role" in response.json()["detail"]

def test_submit_public_report_invalid_date(client: TestClient):
    request_data = {
        "first_name": "John",
        "last_name": "Doe",
        "contact_no": "+123456789",
        "email": "john@example.com",
        "scam_incident_date": "3000-01-01",
        "scam_incident_description": "I was scammed.",
        "role": "victim"  # Add to avoid default issues
    }

    response = client.post("/public/reports/submit", json=request_data)

    assert response.status_code == 400
    assert "Invalid dates" in response.json()["detail"]

# --- Simple Tests for chat.py endpoints ---

def test_send_message_new_conversation_success(client: TestClient, mock_conversation_manager):
    request_data = {
        "query": "Hello, I need help reporting a scam."
    }

    response = client.post("/chat/message", json=request_data)

    assert response.status_code == 200
    response_json = response.json()
    assert "response" in response_json
    assert response_json["response"] == "Mock AI response"
    assert "conversation_id" in response_json
    mock_conversation_manager.process_user_query.assert_called_once_with(
        "Hello, I need help reporting a scam.", None  # Positional args
    )

def test_send_message_existing_conversation_success(client: TestClient, mock_conversation_manager):
    request_data = {
        "query": "More details about the scam.",
        "conversation_id": 1
    }

    response = client.post("/chat/message", json=request_data)

    assert response.status_code == 200
    response_json = response.json()
    assert "response" in response_json
    assert response_json["response"] == "Mock AI response"
    mock_conversation_manager.process_user_query.assert_called_once_with(
        "More details about the scam.", 1  # Positional args
    )

def test_send_message_error(client: TestClient, mock_conversation_manager):
    mock_conversation_manager.process_user_query.side_effect = Exception("Mock error")

    request_data = {
        "query": "Error query"
    }

    response = client.post("/chat/message", json=request_data)

    assert response.status_code == 500
    assert "detail" in response.json()
    assert "Mock error" in response.json()["detail"]
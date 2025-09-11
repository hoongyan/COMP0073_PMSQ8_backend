# tests/test_persons.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import date

from app.main import app  
from app.dependencies.db import get_db  
from app.dependencies.auth import get_current_active_user  
from src.models.data_model import PersonDetails, UserRole, UserStatus, ReportPersonsLink, ScamReports, ReportStatus, PersonRole
from app.model import PersonResponse, LinkedReport
from app.routers.persons import CRUDOperations  


@pytest.fixture(scope="function")
def mock_person():
    """Fixture for a mock PersonDetails object."""
    person = MagicMock(spec=PersonDetails)
    person.person_id = 1
    person.first_name = "JOHN"
    person.last_name = "DOE"
    person.sex = None
    person.dob = None
    person.nationality = None
    person.race = None
    person.occupation = None
    person.contact_no = "12345678"
    person.email = "john.doe@example.com"
    person.blk = None
    person.street = None
    person.unit_no = None
    person.postcode = None
    return person

def test_get_persons(client: TestClient, mock_db: MagicMock, mocker, mock_person):
    """Test GET /persons/ - retrieve list of persons with pagination."""
    mock_crud_class = mocker.patch('app.routers.persons.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.read_all.return_value = [mock_person]

    response = client.get("/persons/?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "persons" in data
    assert len(data["persons"]) == 1
    assert data["persons"][0]["first_name"] == "JOHN"

    # Verify CRUD call
    mock_crud_instance.read_all.assert_called_once_with(mock_db, limit=10, offset=0)

@pytest.mark.parametrize("invalid_params, expected_status", [
    ({"limit": "invalid"}, 422),  # Invalid type for limit
    ({"offset": "invalid"}, 422),  # Invalid type for offset
])
def test_get_persons_invalid_params(client: TestClient, invalid_params, expected_status):
    """Test GET /persons/ with invalid params (error cases)."""
    response = client.get("/persons/", params=invalid_params)
    assert response.status_code == expected_status

def test_create_person(client: TestClient, mock_db: MagicMock, mocker, mock_person):
    """Test POST /persons/ - create a new person."""
    payload = {
        "first_name": "Jane",
        "last_name": "Doe",
        "contact_no": "87654321",
        "email": "jane.doe@example.com",
        "dob": "1990-01-01"
    }

    mock_crud_class = mocker.patch('app.routers.persons.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_person.dob = date(1990, 1, 1)
    mock_person.person_id = 2
    mock_person.first_name = "JANE"
    mock_person.last_name = "DOE"
    mock_crud_instance.create.return_value = mock_person

    response = client.post("/persons/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "JANE"  # Uppercased
    assert data["person_id"] == 2

    # Verify CRUD call with processed data
    expected_data = {
        "first_name": "JANE",
        "last_name": "DOE",
        "contact_no": "87654321",
        "email": "jane.doe@example.com",
        "dob": date(1990, 1, 1)
    }
    mock_crud_instance.create.assert_called_once_with(mock_db, expected_data)

@pytest.mark.parametrize("invalid_payload, expected_status, expected_detail", [
    ({"first_name": "Jane"}, 400, "Missing required fields"),  
    ({"first_name": "Jane", "last_name": "Doe", "contact_no": "12345678", "email": "jane@example.com", "dob": "invalid"}, 400, "Invalid format for dob"),
])
def test_create_person_invalid(client: TestClient, invalid_payload, expected_status, expected_detail):
    """Test POST /persons/ with invalid data (error cases)."""
    response = client.post("/persons/", json=invalid_payload)
    assert response.status_code == expected_status
    if expected_detail:
        assert expected_detail in response.json().get("detail", "")

def test_update_person(client: TestClient, mock_db: MagicMock, mocker, mock_person):
    """Test PUT /persons/{person_id} - update a person."""
    person_id = 1
    payload = {"first_name": "Updated John", "dob": "1980-05-05"}

    mock_crud_class = mocker.patch('app.routers.persons.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_person.first_name = "UPDATED JOHN"
    mock_person.dob = date(1980, 5, 5)
    mock_crud_instance.update.return_value = mock_person

    response = client.put(f"/persons/{person_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "UPDATED JOHN"
    assert data["dob"] == "1980-05-05"

    # Verify CRUD call
    expected_update = {
        "first_name": "UPDATED JOHN",
        "dob": date(1980, 5, 5)
    }
    mock_crud_instance.update.assert_called_once_with(mock_db, person_id, expected_update)

def test_update_person_not_found(client: TestClient, mock_db: MagicMock, mocker):
    """Test PUT /persons/{person_id} - not found error."""
    mock_crud_class = mocker.patch('app.routers.persons.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.update.return_value = None

    response = client.put("/persons/9999", json={"first_name": "Nonexistent"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_delete_person(client: TestClient, mock_db: MagicMock, mocker):
    """Test DELETE /persons/{person_id} - delete a person."""
    person_id = 1

    mock_crud_class = mocker.patch('app.routers.persons.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.delete.return_value = True

    response = client.delete(f"/persons/{person_id}")
    assert response.status_code == 204

    # Verify CRUD call
    mock_crud_instance.delete.assert_called_once_with(mock_db, person_id)

def test_delete_person_not_found(client: TestClient, mock_db: MagicMock, mocker):
    """Test DELETE /persons/{person_id} - not found error."""
    mock_crud_class = mocker.patch('app.routers.persons.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.delete.return_value = False

    response = client.delete("/persons/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_get_linked_reports(client: TestClient, mock_db: MagicMock):
    """Test GET /persons/{person_id}/linked_reports - retrieve linked reports."""
    person_id = 1

    # Mock link
    mock_link = MagicMock(spec=ReportPersonsLink)
    mock_link.report_id = 100
    mock_link.role = PersonRole.victim 

    mock_db.query.return_value.filter.return_value.all.return_value = [mock_link]

    response = client.get(f"/persons/{person_id}/linked_reports")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["report_id"] == "100"
    assert data[0]["role"] == "victim"  

    # Verify calls
    mock_db.query.assert_called_with(ReportPersonsLink)
    mock_db.query.return_value.filter.assert_called_once()

def test_get_linked_reports_no_links(client: TestClient, mock_db: MagicMock):
    """Test GET /persons/{person_id}/linked_reports - no links."""
    mock_db.query.return_value.filter.return_value.all.return_value = []

    response = client.get("/persons/1/linked_reports")
    assert response.status_code == 200
    assert response.json() == []

def test_get_linked_reports_not_found(client: TestClient, mock_db: MagicMock):
    """Test GET /persons/{person_id}/linked_reports - person not found (returns empty)."""
    mock_db.query.return_value.filter.return_value.all.return_value = []

    response = client.get("/persons/9999/linked_reports")
    assert response.status_code == 200
    assert response.json() == []
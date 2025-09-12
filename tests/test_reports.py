import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import date

from app.main import app 
from src.models.data_model import ScamReports, Users, ReportPersonsLink, PersonDetails, ReportStatus, PersonRole
from app.model import ScamReportListResponse, ScamReportResponse, ReportRequest, LinkedPerson, LinkedPersonCreate
from app.routers.reports import CRUDOperations
from src.database.vector_operations import VectorStore

# Import the dependency to override
from app.routers.reports import get_vector_store

# Fixtures for mock objects
@pytest.fixture
def mock_report():
    """Mock a ScamReports object."""
    report = MagicMock(spec=ScamReports)
    report.report_id = 1
    report.scam_incident_date = date(2023, 1, 1)
    report.scam_report_date = date(2023, 1, 2)
    report.scam_type = "PHISHING"
    report.scam_approach_platform = "EMAIL"
    report.scam_communication_platform = "PHONE"
    report.scam_transaction_type = "WIRE"
    report.scam_beneficiary_platform = "BANK"
    report.scam_beneficiary_identifier = "123456"
    report.scam_contact_no = "+123456789"
    report.scam_email = "scam@example.com"
    report.scam_moniker = "Scammer"
    report.scam_url_link = "http://scam.com"
    report.scam_amount_lost = 100.0
    report.scam_incident_description = "Test description"
    report.status = ReportStatus.unassigned
    report.io = None  # Will mock IO separately
    report.pois = []  # Will add linked persons in tests
    return report

@pytest.fixture
def mock_io():
    """Mock a Users object for IO."""
    io = MagicMock(spec=Users)
    io.user_id = 1
    io.first_name = "Jane"
    io.last_name = "Officer"
    return io

@pytest.fixture
def mock_person():
    """Mock a PersonDetails object."""
    person = MagicMock(spec=PersonDetails)
    person.person_id = 1
    person.first_name = "John"
    person.last_name = "Doe"
    
    person._sa_instance_state = MagicMock() 
    
    return person

@pytest.fixture
def mock_link(mock_report, mock_person):
    """Mock a ReportPersonsLink object."""
    link = MagicMock(spec=ReportPersonsLink)
    link.report_id = mock_report.report_id
    link.person_id = mock_person.person_id
    link.role = PersonRole.victim
    link.person = mock_person  
    return link

# Tests

def test_get_reports(client: TestClient, mock_db: MagicMock, mock_report, mock_io, mock_link):
    """Test GET /reports/ - retrieve list of reports with pagination."""
    mock_report.io = mock_io
    mock_report.pois = [mock_link]
    mock_query = mock_db.query.return_value
    mock_query.options.return_value = mock_query 
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [mock_report]

    response = client.get("/reports/?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "reports" in data
    assert len(data["reports"]) == 1
    assert data["reports"][0]["scam_type"] == "PHISHING"
    assert data["reports"][0]["assigned_IO"] == "Jane Officer"
    assert len(data["reports"][0]["linked_persons"]) == 1
    assert data["reports"][0]["linked_persons"][0]["role"] == "victim"

    # Verify query calls (ensures joinedload was used)
    mock_db.query.assert_called_once_with(ScamReports)

@pytest.mark.parametrize("invalid_params, expected_status", [
    ({"limit": "invalid"}, 422),  
    ({"offset": "invalid"}, 422), 
])
def test_get_reports_invalid_params(client: TestClient, invalid_params, expected_status):
    """Test GET /reports/ with invalid params."""
    response = client.get("/reports/", params=invalid_params)
    assert response.status_code == expected_status

def test_create_report(client: TestClient, mock_db: MagicMock, mocker, mock_report, mock_io, mock_link):
    """Test POST /reports/ - create a new report."""
    payload = {
        "scam_incident_date": "2023-01-01",
        "scam_report_date": "2023-01-02",
        "scam_type": "phishing",
        "scam_incident_description": "Test description"
    }

 
    mock_vector_store = MagicMock(spec=VectorStore)
    mock_vector_store.get_embedding.return_value = [0.1] * 384  
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store

    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    mock_query = mock_db.query.return_value
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = mock_report
    mock_report.io = mock_io
    mock_report.pois = [mock_link]

    response = client.post("/reports/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scam_type"] == "PHISHING"  
    assert data["scam_incident_description"] == "Test description"

    mock_db.add.assert_called()  
    mock_db.commit.assert_called()
    mock_vector_store.get_embedding.assert_called_once_with("Test description")

@pytest.mark.parametrize("invalid_payload, expected_status, expected_detail", [
    ({"scam_type": "phishing"}, 400, "Missing required fields"),  # Missing dates/description
    ({"scam_incident_date": "2023-01-01", "scam_report_date": "2023-01-02", "scam_incident_description": ""}, 400, "cannot be empty"),  # Empty description
    ({"scam_incident_date": "invalid", "scam_report_date": "2023-01-02", "scam_incident_description": "desc"}, 400, "Invalid date format"),  # Bad date
])
def test_create_report_invalid(client: TestClient, invalid_payload, expected_status, expected_detail):
    """Test POST /reports/ with invalid data."""
    response = client.post("/reports/", json=invalid_payload)
    assert response.status_code == expected_status
    if expected_detail:
        assert expected_detail in response.json().get("detail", "")

def test_update_report(client: TestClient, mock_db: MagicMock, mocker, mock_report, mock_io, mock_link):
    """Test PUT /reports/{report_id} - update report."""
    report_id = 1
    payload = {"scam_type": "updated phishing", "scam_incident_description": "Updated desc"}

    # Mock VectorStore dependency
    mock_vector_store = MagicMock(spec=VectorStore)
    mock_vector_store.get_embedding.return_value = [0.2] * 384
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store

    # Mock CRUD for update
    mock_crud_class = mocker.patch('app.routers.reports.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.update.return_value = mock_report  # Main update
    mock_crud_instance.update_embedding.return_value = True


    mock_report.scam_type = "UPDATED PHISHING"
    mock_report.scam_incident_description = "Updated desc"

    mock_query = mock_db.query.return_value
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = mock_report
    mock_report.io = mock_io
    mock_report.pois = [mock_link]

    response = client.put(f"/reports/{report_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scam_type"] == "UPDATED PHISHING"  

    mock_crud_instance.update.assert_called_once()
    mock_vector_store.get_embedding.assert_called_once_with("Updated desc")

def test_update_report_not_found(client: TestClient, mock_db: MagicMock, mocker):
    """Test PUT /reports/{report_id} - not found."""
    mock_crud_class = mocker.patch('app.routers.reports.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.update.return_value = None

    response = client.put("/reports/9999", json={"scam_type": "nonexistent"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_delete_report(client: TestClient, mock_db: MagicMock, mocker):
    """Test DELETE /reports/{report_id} - delete report."""
    report_id = 1
    mock_crud_class = mocker.patch('app.routers.reports.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.delete.return_value = True

    response = client.delete(f"/reports/{report_id}")
    assert response.status_code == 204

    mock_crud_instance.delete.assert_called_once_with(mock_db, report_id)

def test_delete_report_not_found(client: TestClient, mock_db: MagicMock, mocker):
    """Test DELETE /reports/{report_id} - not found."""
    mock_crud_class = mocker.patch('app.routers.reports.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.delete.return_value = False

    response = client.delete("/reports/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_get_linked_persons(client: TestClient, mock_db: MagicMock, mock_link):
    """Test GET /reports/{report_id}/linked_persons - get linked persons."""
    report_id = 1
    mock_query = mock_db.query.return_value
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [mock_link]

    response = client.get(f"/reports/{report_id}/linked_persons")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "John Doe"
    assert data[0]["role"] == "victim"

    mock_db.query.assert_called_with(ReportPersonsLink)

def test_get_linked_persons_no_links(client: TestClient, mock_db: MagicMock):
    """Test GET /reports/{report_id}/linked_persons - no links."""
    mock_query = mock_db.query.return_value
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = []

    response = client.get("/reports/1/linked_persons")
    assert response.status_code == 200
    assert response.json() == []

def test_add_linked_person(client: TestClient, mock_db: MagicMock, mock_report, mock_person, mock_link):
    """Test POST /reports/{report_id}/linked_persons - add linked person."""
    report_id = 1
    payload = {"person_id": 1, "role": "victim"}

    # Mock queries for validations
    mock_query = mock_db.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.first.side_effect = [mock_report, mock_person, None]  # Report, person, no link

    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = lambda obj: setattr(obj, 'person', mock_person)  
    mock_link.person = mock_person  

    response = client.post(f"/reports/{report_id}/linked_persons", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "victim"

    mock_db.add.assert_called()  

@pytest.mark.parametrize("invalid_case, payload, expected_status, expected_detail", [
    ("no_report", {"person_id": 1, "role": "victim"}, 404, "Report with ID 1 not found"),
    ("no_person", {"person_id": 999, "role": "victim"}, 404, "Person with ID 999 not found"),
    ("invalid_role", {"person_id": 1, "role": "invalid"}, 400, "Invalid role"),
    ("existing_link", {"person_id": 1, "role": "victim"}, 400, "already linked"),
])
def test_add_linked_person_invalid(client: TestClient, mock_db: MagicMock, invalid_case, payload, expected_status, expected_detail):
    """Test POST /reports/{report_id}/linked_persons invalid cases."""
    mock_query = mock_db.query.return_value
    mock_query.filter.return_value = mock_query

    if invalid_case == "no_report":
        mock_query.first.side_effect = [None]
    elif invalid_case == "no_person":
        mock_query.first.side_effect = [MagicMock(), None]
    elif invalid_case == "existing_link":
        mock_query.first.side_effect = [MagicMock(), MagicMock(), MagicMock()] 

    response = client.post("/reports/1/linked_persons", json=payload)
    assert response.status_code == expected_status
    assert expected_detail in response.json().get("detail", "")

def test_delete_linked_person(client: TestClient, mock_db: MagicMock, mock_link):
    """Test DELETE /reports/{report_id}/linked_persons/{person_id} - delete link."""
    report_id = 1
    person_id = 1
    mock_query = mock_db.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = mock_link
    mock_db.delete.return_value = None
    mock_db.commit.return_value = None

    response = client.delete(f"/reports/{report_id}/linked_persons/{person_id}")
    assert response.status_code == 204

    mock_db.delete.assert_called_with(mock_link)

def test_delete_linked_person_not_found(client: TestClient, mock_db: MagicMock):
    """Test DELETE /reports/{report_id}/linked_persons/{person_id} - not found."""
    mock_query = mock_db.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None

    response = client.delete("/reports/1/linked_persons/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
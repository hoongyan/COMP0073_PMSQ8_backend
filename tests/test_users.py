import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import date, datetime

from app.main import app  
from app.dependencies.db import get_db  
from app.dependencies.auth import get_current_active_user, get_password_hash  
from src.models.data_model import Users, UserRole, UserStatus
from app.model import UserResponse, UserListResponse
from app.routers.users import CRUDOperations 


@pytest.fixture(scope="function")
def mock_user():
    """Fixture for a mock Users object."""
    user = MagicMock(spec=Users)
    user.user_id = 1
    user.first_name = "ADMIN"
    user.last_name = "USER"
    user.sex = None
    user.dob = None
    user.nationality = None
    user.race = None
    user.contact_no = "12345678"
    user.email = "admin@example.com"
    user.blk = None
    user.street = None
    user.unit_no = None
    user.postcode = None
    user.role = UserRole.admin
    user.status = UserStatus.active
    user.registration_datetime = datetime.now()
    user.last_updated_datetime = datetime.now()
    user.password = "hashed_password"
    return user

@pytest.fixture(scope="function")
def set_admin_role(mock_db: MagicMock):
    """Set the mock current_user to have admin role."""
    mock_current_user = app.dependency_overrides[get_current_active_user]()
    mock_current_user.role = UserRole.admin
    yield


def test_get_users(client: TestClient, mock_db: MagicMock, mocker, mock_user, set_admin_role):
    """Test GET /users/ - retrieve list of users with pagination."""
    mock_crud_class = mocker.patch('app.routers.users.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.read_all.return_value = [mock_user]

    response = client.get("/users/?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 1
    assert data["users"][0]["first_name"] == "ADMIN"
    assert data["users"][0]["role"] == "ADMIN"

    mock_crud_instance.read_all.assert_called_once_with(mock_db, limit=10, offset=0)

@pytest.mark.parametrize("invalid_params, expected_status", [
    ({"limit": "invalid"}, 422),
    ({"offset": "invalid"}, 422),
])
def test_get_users_invalid_params(client: TestClient, invalid_params, expected_status, set_admin_role):
    """Test GET /users/ with invalid params (error cases)."""
    response = client.get("/users/", params=invalid_params)
    assert response.status_code == expected_status

def test_create_user(client: TestClient, mock_db: MagicMock, mocker, mock_user, set_admin_role):
    """Test POST /users/ - create a new user."""
    payload = {
        "password": "testpassword",
        "first_name": "New",
        "last_name": "User",
        "contact_no": "87654321",
        "email": "new.user@example.com",
        "role": "ANALYST",
        "dob": "1990-01-01"
    }

    fixed_hash = "fixed_hash_for_test"
    mocker.patch('app.routers.users.get_password_hash', return_value=fixed_hash)

    mock_crud_class = mocker.patch('app.routers.users.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_user.user_id = 2
    mock_user.first_name = "NEW"
    mock_user.last_name = "USER"
    mock_user.dob = date(1990, 1, 1)
    mock_user.role = UserRole.analyst
    mock_user.status = UserStatus.pending
    mock_user.password = fixed_hash
    mock_crud_instance.create.return_value = mock_user

    response = client.post("/users/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "NEW"
    assert data["role"] == "ANALYST"
    assert data["status"] == "PENDING"

    # Verify CRUD call
    expected_data = {
        "password": fixed_hash,  # Hashed
        "first_name": "NEW",
        "last_name": "USER",
        "contact_no": "87654321",
        "email": "new.user@example.com",
        "role": UserRole.analyst,
        "status": UserStatus.pending,
        "dob": date(1990, 1, 1)
    }
    mock_crud_instance.create.assert_called_once_with(mock_db, expected_data)

@pytest.mark.parametrize("invalid_payload, expected_status, expected_detail", [
    ({"password": "testpassword", "first_name": "New"}, 400, "Missing required fields"),
    ({"password": "testpassword", "first_name": "New", "last_name": "User", "contact_no": "12345678", "email": "new@example.com", "role": "INVALID"}, 400, "Invalid role"),
    ({"password": "testpassword", "first_name": "New", "last_name": "User", "contact_no": "12345678", "email": "new@example.com", "role": "ANALYST", "dob": "invalid"}, 400, "Invalid format for dob"),
])
def test_create_user_invalid(client: TestClient, invalid_payload, expected_status, expected_detail, set_admin_role):
    """Test POST /users/ with invalid data (error cases)."""
    response = client.post("/users/", json=invalid_payload)
    assert response.status_code == expected_status
    if expected_detail:
        assert expected_detail in response.json().get("detail", "")

def test_update_user(client: TestClient, mock_db: MagicMock, mocker, mock_user, set_admin_role):
    """Test PUT /users/{user_id} - update a user."""
    user_id = 1
    payload = {"first_name": "Updated Admin", "role": "INVESTIGATION OFFICER", "dob": "1980-05-05"}

    mock_crud_class = mocker.patch('app.routers.users.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_user.first_name = "UPDATED ADMIN"
    mock_user.dob = date(1980, 5, 5)
    mock_user.role = UserRole.io
    mock_crud_instance.update.return_value = mock_user

    response = client.put(f"/users/{user_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "UPDATED ADMIN"
    assert data["role"] == "INVESTIGATION OFFICER"

    expected_update = {
        "first_name": "UPDATED ADMIN",
        "role": UserRole.io,
        "dob": date(1980, 5, 5)
    }
    mock_crud_instance.update.assert_called_once_with(mock_db, user_id, expected_update)

def test_update_user_not_found(client: TestClient, mock_db: MagicMock, mocker, set_admin_role):
    """Test PUT /users/{user_id} - not found error."""
    mock_crud_class = mocker.patch('app.routers.users.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.update.return_value = None

    response = client.put("/users/9999", json={"first_name": "Nonexistent"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_reset_password(client: TestClient, mock_db: MagicMock, mocker, set_admin_role):
    """Test POST /users/{user_id}/reset-password - reset user password."""
    user_id = 1
    payload = {"password": "newpassword"}

    fixed_hash = "fixed_hash_for_test"
    mocker.patch('app.routers.users.get_password_hash', return_value=fixed_hash)

    mock_crud_class = mocker.patch('app.routers.users.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.update.return_value = MagicMock()  # Just needs to be truthy

    response = client.post(f"/users/{user_id}/reset-password", json=payload)
    assert response.status_code == 204

    expected_update = {"password": fixed_hash}
    mock_crud_instance.update.assert_called_once_with(mock_db, user_id, expected_update)

def test_reset_password_not_found(client: TestClient, mock_db: MagicMock, mocker, set_admin_role):
    """Test POST /users/{user_id}/reset-password - not found error."""
    mock_crud_class = mocker.patch('app.routers.users.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.update.return_value = None

    response = client.post("/users/9999/reset-password", json={"password": "newpassword"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_delete_user(client: TestClient, mock_db: MagicMock, mocker, set_admin_role):
    """Test DELETE /users/{user_id} - delete a user."""
    user_id = 1

    mock_crud_class = mocker.patch('app.routers.users.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.delete.return_value = True

    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 204

    mock_crud_instance.delete.assert_called_once_with(mock_db, user_id)

def test_delete_user_not_found(client: TestClient, mock_db: MagicMock, mocker, set_admin_role):
    """Test DELETE /users/{user_id} - not found error."""
    mock_crud_class = mocker.patch('app.routers.users.CRUDOperations', autospec=True)
    mock_crud_instance = mock_crud_class.return_value
    mock_crud_instance.delete.return_value = False

    response = client.delete("/users/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
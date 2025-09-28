import pytest
from fastapi import status
from app.main import app
from app.dependencies.auth import get_current_active_user
from sqlalchemy.exc import SQLAlchemyError
from src.models.data_model import UserRole, UserStatus, Users  
from app.dependencies.auth import authenticate_user, create_access_token, get_password_hash 

@pytest.mark.parametrize(
    "form_data, mock_auth_result, expected_status, expected_detail",
    [
        # Case 1: Valid credentials
        ({"username": "test@example.com", "password": "validpass"}, Users(email="test@example.com", status=UserStatus.active), status.HTTP_200_OK, None),
        # Case 2: Invalid credentials
        ({"username": "wrong@example.com", "password": "wrongpass"}, None, status.HTTP_401_UNAUTHORIZED, "Incorrect email or password"),
        # Case 3: Inactive user
        ({"username": "inactive@example.com", "password": "validpass"}, Users(email="inactive@example.com", status=UserStatus.inactive), status.HTTP_403_FORBIDDEN, "Account is inactive or pending approval"),
    ]
)
def test_login_for_access_token(client, mocker, mock_db, form_data, mock_auth_result, expected_status, expected_detail):
    """Test /api/auth/token endpoint for form-based login."""
    # Mock authenticate_user
    mocker.patch("app.routers.auth.authenticate_user", return_value=mock_auth_result)
    # Mock create_access_token 
    if expected_status == status.HTTP_200_OK:
        mocker.patch("app.routers.auth.create_access_token", return_value="mock_token")

    response = client.post("/api/auth/token", data=form_data)
    assert response.status_code == expected_status
    if expected_status == status.HTTP_200_OK:
        assert response.json()["access_token"] == "mock_token"
        assert response.json()["token_type"] == "bearer"
    else:
        assert expected_detail in response.json()["detail"]

@pytest.mark.parametrize(
    "json_data, mock_auth_result, expected_status, expected_detail",
    [
        # Case 1: Valid JSON signin
        ({"email": "test@example.com", "password": "validpass"}, Users(email="test@example.com", status=UserStatus.active), status.HTTP_200_OK, None),
        # Case 2: Invalid JSON signin
        ({"email": "wrong@example.com", "password": "wrongpass"}, None, status.HTTP_401_UNAUTHORIZED, "Incorrect email or password"),
    ]
)
def test_login_for_access_token_json(client, mocker, mock_db, json_data, mock_auth_result, expected_status, expected_detail):
    """Test /api/auth/signin endpoint for JSON-based login."""
    mocker.patch("app.routers.auth.authenticate_user", return_value=mock_auth_result)
    if expected_status == status.HTTP_200_OK:
        mocker.patch("app.routers.auth.create_access_token", return_value="mock_token")

    response = client.post("/api/auth/signin", json=json_data)
    assert response.status_code == expected_status
    if expected_status == status.HTTP_200_OK:
        assert response.json()["token"] == "mock_token"
    else:
        assert expected_detail in response.json()["detail"]

@pytest.mark.parametrize(
    "user_data, mock_existing_user, mock_hash, expected_status, expected_email",
    [
        # Case 1: New user creation
        ({"email": "new@example.com", "password": "pass12345", "first_name": "John", "last_name": "Doe", "contact_no": "12345678", "role": "INVESTIGATION OFFICER"}, None, "hashed_pass", status.HTTP_200_OK, "new@example.com"),
        # Case 2: Duplicate email
        ({"email": "existing@example.com", "password": "pass12345", "first_name": "John", "last_name": "Doe", "contact_no": "12345678"}, Users(email="existing@example.com"), None, status.HTTP_400_BAD_REQUEST, None),
        # Case 3: DB failure on create
        ({"email": "fail@example.com", "password": "pass12345", "first_name": "John", "last_name": "Doe", "contact_no": "12345678"}, None, "hashed_pass", status.HTTP_500_INTERNAL_SERVER_ERROR, None),
    ]
)
def test_sign_up(client, mocker, mock_db, user_data, mock_existing_user, mock_hash, expected_status, expected_email):
    """Test /api/auth/signup endpoint for user creation."""
    # Mock DB query for existing user
    mock_query = mock_db.query.return_value.filter.return_value.first
    mock_query.return_value = mock_existing_user

    # Mock password hash
    mocker.patch("app.routers.auth.get_password_hash", return_value=mock_hash)

    # Mock CRUD create (simulate success or failure)
    if expected_status == status.HTTP_500_INTERNAL_SERVER_ERROR:
        mock_db.add.side_effect = SQLAlchemyError("DB error")
    else:

        user_data_copy = user_data.copy()
        user_data_copy.pop('password', None)  
        user_data_copy.pop('role', None)  
        mock_created_user = Users(**user_data_copy, password=mock_hash, role=UserRole.io, status=UserStatus.pending)
        mock_db.add.return_value = None  
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda x: setattr(x, "user_id", 1)  # Simulate refresh

    response = client.post("/api/auth/signup", json=user_data)
    assert response.status_code == expected_status
    if expected_status == status.HTTP_200_OK:
        assert response.json()["email"] == expected_email

def test_read_users_me(client, mocker, mock_db):
    """Test /api/auth/users/me endpoint for user profile."""
    # Mock current_user
    mock_user = Users(email="me@example.com", first_name="Me", last_name="User", contact_no="123", role=UserRole.io, status=UserStatus.active)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user  

    response = client.get("/api/auth/users/me")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "me@example.com"
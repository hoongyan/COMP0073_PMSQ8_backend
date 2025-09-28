import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app  
from app.dependencies.db import get_db  
from app.dependencies.auth import get_current_active_user  

@pytest.fixture(scope="function")
def client(mocker):
    """Fixture for TestClient with mocked dependencies."""
    # Mock DB session (returns a mock Session object)
    mock_db = mocker.MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: mock_db

    # Mock current user (for auth-protected endpoints)
    mock_user = mocker.MagicMock()  
    app.dependency_overrides[get_current_active_user] = lambda: mock_user

    client = TestClient(app)
    yield client
    
    app.dependency_overrides = {}

@pytest.fixture(scope="function")
def mock_db(mocker, client):  # Access the mocked DB from client fixture
    """Fixture to get the mocked DB session."""
    return app.dependency_overrides[get_db]()
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.dependencies.roles import require_permission
from src.models.data_model import Users, UserRole, UserStatus

@pytest.fixture
def mock_db():
    return None  # Or mock Session if needed

@pytest.fixture
def mock_admin():
    return Users(role=UserRole.admin, status=UserStatus.active)

@pytest.fixture
def mock_io_with_perm():
    return Users(role=UserRole.io, status=UserStatus.active, permission={"reports": "edit"})

@pytest.fixture
def mock_io_without_perm():
    return Users(role=UserRole.io, status=UserStatus.active, permission={})

def test_admin_bypass(mock_db, mock_admin):
    dep = require_permission("reports", "edit")
    result = dep(mock_db, mock_admin)  # Should pass
    assert result == mock_admin

def test_io_with_perm(mock_db, mock_io_with_perm):
    dep = require_permission("reports", "edit")
    result = dep(mock_db, mock_io_with_perm)  # Pass
    assert result == mock_io_with_perm

def test_io_without_perm(mock_db, mock_io_without_perm):
    dep = require_permission("reports", "edit")
    with pytest.raises(HTTPException) as exc:
        dep(mock_db, mock_io_without_perm)
    assert exc.value.status_code == 403
    assert "Insufficient permissions" in exc.value.detail
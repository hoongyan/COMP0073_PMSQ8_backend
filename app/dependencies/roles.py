import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import Depends, HTTPException

from app.dependencies.db import db_dependency  
from app.dependencies.auth import get_current_active_user  
from src.models.data_model import Users, UserRole  

def admin_role(db: db_dependency, current_user: Users = Depends(get_current_active_user)):
    """
    Dependency to check if the current user has ADMIN role.
    Raises 403 if not. Use this in router endpoints for admin-only access.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Unauthorized: Admin access required")
    return current_user

def io_role(db: db_dependency, current_user: Users = Depends(get_current_active_user)):
    """
    Dependency to check if the current user has INVESTIGATION OFFICER role.
    Raises 403 if not. Use this for IO-specific endpoints.
    """
    if current_user.role != UserRole.io:
        raise HTTPException(status_code=403, detail="Unauthorized: Investigation Officer access required")
    return current_user

def analyst_role(db: db_dependency, current_user: Users = Depends(get_current_active_user)):
    """
    Dependency to check if the current user has ANALYST role.
    Raises 403 if not. Use this for analyst-specific endpoints.
    """
    if current_user.role != UserRole.analyst:
        raise HTTPException(status_code=403, detail="Unauthorized: Analyst access required")
    return current_user

# Optional: A general "authenticated" role for any active user
def any_role(db: db_dependency, current_user: Users = Depends(get_current_active_user)):
    """
    Dependency to allow any active authenticated user.
    Useful for endpoints that don't require a specific role but need login.
    """
    return current_user


import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Annotated, List
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies.db import db_dependency
from app.dependencies.roles import admin_role  
from src.database.database_operations import CRUDOperations
from src.models.data_model import Users, UserRole, UserStatus
from app.dependencies.auth import get_password_hash, get_current_active_user 
from app.model import UserListResponse, UserResponse, UserRequest, ResetPasswordRequest, IOOption, IOListResponse

users_router = APIRouter(
    prefix="/users",
    tags=["users"],
)

FIELDS_TO_UPPERCASE = [
    'first_name', 'last_name', 'sex','nationality', 'race',
    'blk', 'street', 'unit_no', 'postcode'
]

@users_router.get("/", response_model=UserListResponse)
def get_users_endpoint(
    db: db_dependency,
    current_user: Users = Depends(admin_role),  # Restricted to Admins
    limit: int = 100,
    offset: int = 0
):
    """
    Retrieve a list of users with pagination.
    Accessible only by Admins.
    """
    user_crud = CRUDOperations(Users)
    try:
        users = user_crud.read_all(db, limit=limit, offset=offset)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during read: {str(e)}")
    
    enriched_users = [
        UserResponse(
            user_id=user.user_id,
            first_name=user.first_name,
            last_name=user.last_name,
            sex=user.sex,
            dob=user.dob,
            nationality=user.nationality,
            race=user.race,
            contact_no=user.contact_no,
            email=user.email,
            blk=user.blk,
            street=user.street,
            unit_no=user.unit_no,
            postcode=user.postcode,
            role=user.role.value,
            status=user.status.value,
            registration_datetime=user.registration_datetime,
            last_updated_datetime=user.last_updated_datetime
        ) for user in users
    ]
    
    return UserListResponse(users=enriched_users)

@users_router.post("/", response_model=UserResponse)
def create_user_endpoint(
    db: db_dependency,
    data: UserRequest = Body(...),
    current_user: Users = Depends(admin_role)  # Restricted to Admins
):
    """
    Create a new user.
    - Required fields: password, first_name, last_name, contact_no, email, role
    - Password is hashed automatically.
    - Defaults to PENDING status if not provided.
    Accessible only by Admins.
    """
    create_data = data.dict(exclude_unset=True)
    
    # Ensure required fields are present
    required = ['password', 'first_name', 'last_name', 'contact_no', 'email', 'role']
    missing = [field for field in required if field not in create_data or create_data[field] is None]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")
    
    # Uppercase specified fields if present
    for field in FIELDS_TO_UPPERCASE:
        if field in create_data and isinstance(create_data[field], str):
            create_data[field] = create_data[field].upper()
    
    # Parse DOB if provided
    if 'dob' in create_data and create_data['dob']:
        try:
            create_data['dob'] = datetime.strptime(create_data['dob'], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid format for dob (use YYYY-MM-DD)")
    
    role_map = {member.value.upper(): member for member in UserRole}
    try:
        create_data['role'] = role_map[create_data['role'].upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join([m.value for m in UserRole])}")
    
    # Handle status: Map string to enum, default to PENDING
    if 'status' in create_data:
        status_map = {member.value.upper(): member for member in UserStatus}
        try:
            create_data['status'] = status_map[create_data['status'].upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join([m.value for m in UserStatus])}")
    else:
        create_data['status'] = UserStatus.pending
    
    # Hash the password
    create_data['password'] = get_password_hash(create_data['password'])
    
    user_crud = CRUDOperations(Users)
    try:
        new_user = user_crud.create(db, create_data)
        if not new_user:
            raise HTTPException(status_code=500, detail="Failed to create user")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during creation: {str(e)}")
    
    return UserResponse(
        user_id=new_user.user_id,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        sex=new_user.sex,
        dob=new_user.dob,
        nationality=new_user.nationality,
        race=new_user.race,
        contact_no=new_user.contact_no,
        email=new_user.email,
        blk=new_user.blk,
        street=new_user.street,
        unit_no=new_user.unit_no,
        postcode=new_user.postcode,
        role=new_user.role.value,
        status=new_user.status.value,
        registration_datetime=new_user.registration_datetime,
        last_updated_datetime=new_user.last_updated_datetime
    )

@users_router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    db: db_dependency,
    user_id: int,
    data: UserRequest = Body(...),
    current_user: Users = Depends(admin_role)  # Restricted to Admins
):
    """
    Update a user by user_id.
    - Partial updates: Provide only fields to change.
    - If password is provided, it is hashed.
    - Role/status are mapped to enums.
    Accessible only by Admins.
    """
    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    # Uppercase specified fields if present
    for field in FIELDS_TO_UPPERCASE:
        if field in update_data and isinstance(update_data[field], str):
            update_data[field] = update_data[field].upper()
    
    # Parse DOB if provided
    if 'dob' in update_data and update_data['dob']:
        try:
            update_data['dob'] = datetime.strptime(update_data['dob'], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid format for dob (use YYYY-MM-DD)")
    
    # Handle role if provided
    if 'role' in update_data:
        role_map = {member.value.upper(): member for member in UserRole}
        try:
            update_data['role'] = role_map[update_data['role'].upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join([m.value for m in UserRole])}")
    
    # Handle status if provided
    if 'status' in update_data:
        status_map = {member.value.upper(): member for member in UserStatus}
        try:
            update_data['status'] = status_map[update_data['status'].upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join([m.value for m in UserStatus])}")
    
    # Hash password if provided (optional for update)
    if 'password' in update_data:
        update_data['password'] = get_password_hash(update_data['password'])
    
    user_crud = CRUDOperations(Users)
    try:
        updated_user = user_crud.update(db, user_id, update_data)
        if not updated_user:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during update: {str(e)}")

    return UserResponse(
        user_id=updated_user.user_id,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        sex=updated_user.sex,
        dob=updated_user.dob,
        nationality=updated_user.nationality,
        race=updated_user.race,
        contact_no=updated_user.contact_no,
        email=updated_user.email,
        blk=updated_user.blk,
        street=updated_user.street,
        unit_no=updated_user.unit_no,
        postcode=updated_user.postcode,
        role=updated_user.role.value,
        status=updated_user.status.value,
        registration_datetime=updated_user.registration_datetime,
        last_updated_datetime=updated_user.last_updated_datetime
    )

@users_router.post("/{user_id}/reset-password", status_code=204)
def reset_password_endpoint(
    db: db_dependency,
    user_id: int,
    data: ResetPasswordRequest = Body(...),
    current_user: Users = Depends(admin_role)  # Restricted to Admins
):
    """
    Reset password for a user by user_id.
    - Requires new password in body.
    - Password is validated and hashed.
    Accessible only by Admins.
    """
    reset_data = {"password": get_password_hash(data.password)}
    
    user_crud = CRUDOperations(Users)
    try:
        updated_user = user_crud.update(db, user_id, reset_data)
        if not updated_user:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during password reset: {str(e)}")
    return None

@users_router.delete("/{user_id}", status_code=204)
def delete_user_endpoint(
    db: db_dependency,
    user_id: int,
    current_user: Users = Depends(admin_role)  # Restricted to Admins
):
    """
    Delete a user by user_id.
    Accessible only by Admins.
    """
    user_crud = CRUDOperations(Users)
    try:
        deleted = user_crud.delete(db, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during delete: {str(e)}")
    return None



@users_router.get("/io", response_model=IOListResponse)
def get_ios_endpoint(
    db: db_dependency,
    current_user: Users = Depends(get_current_active_user)  # Any active user can access
):
    """
    Retrieve a list of active Investigation Officers (IOs).
    Returns user_id and full_name for dropdown selection.
    Accessible by any active authenticated user.
    """
    try:
        ios = db.query(Users).filter(
            Users.role == UserRole.io,
            Users.status == UserStatus.active
        ).order_by(Users.user_id.asc()).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during read: {str(e)}")
    
    if not ios:
        return IOListResponse(ios=[])
    
    enriched_ios = [
        IOOption(
            user_id=user.user_id,
            full_name=f"{user.first_name} {user.last_name}"
        ) for user in ios
    ]
    
    return IOListResponse(ios=enriched_ios)
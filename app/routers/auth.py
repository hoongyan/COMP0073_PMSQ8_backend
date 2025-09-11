import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime,timedelta
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies.db import db_dependency  
from app.dependencies.auth import authenticate_user, create_access_token, get_current_active_user, get_password_hash
from src.database.database_operations import CRUDOperations
from src.models.data_model import Users, UserStatus, UserRole 
from app.model import Token, TokenJson, SignInRequest, UserIn, UserRead

auth_router = APIRouter(prefix="/api/auth")  

ACCESS_TOKEN_EXPIRE_MINUTES = 60  #adjust as needed 

@auth_router.post("/token", response_model=Token)
def login_for_access_token(db: db_dependency,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2-compatible login endpoint. Use for form-based auth (e.g., in Postman).
    Returns JWT access token if credentials valid.
    """
    user = authenticate_user(form_data.username, form_data.password, db)  # Note: Using 'username' for form, but it's email
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != UserStatus.active:  
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive or pending approval")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.post("/signin", response_model=TokenJson)
def login_for_access_token_json(
    signin_request: SignInRequest, db: db_dependency
):
    """
    JSON-based signin endpoint for frontend. Takes email/password in body.
    Returns JWT token if valid, else 401 error.
    """
    user = authenticate_user(signin_request.email, signin_request.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != UserStatus.active: 
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive or pending approval")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"token": access_token, "token_type": "bearer"}

@auth_router.post("/signup", response_model=UserRead)
def sign_up(user_in: UserIn, db: db_dependency):
    """
    Signup endpoint to create a new user.
    Hashes password, checks for existing email, sets defaults (PENDING status, default role).
    Returns user details (no password) on success.
    """
    # Check if email exists
    try:  
        existing_user = db.query(Users).filter(Users.email == user_in.email).first()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during email check: {str(e)}")
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash the password
    hashed_password = get_password_hash(user_in.password)
    
    # Map role string (value) to enum member
    role_map = {member.value.upper(): member for member in UserRole}  
    if user_in.role:
        try:
            selected_role = role_map[user_in.role.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {user_in.role}. Must be one of: {', '.join([m.value for m in UserRole])}")
    else:
        selected_role = UserRole.io  # Default
    
    user_data = {
        "password": hashed_password,
        "first_name": user_in.first_name,
        "last_name": user_in.last_name,
        "sex": user_in.sex,
        "dob": datetime.strptime(user_in.dob, "%Y-%m-%d").date() if user_in.dob else None,
        "nationality": user_in.nationality,
        "race": user_in.race,
        "contact_no": user_in.contact_no,
        "email": user_in.email,
        "blk": user_in.blk,
        "street": user_in.street,
        "unit_no": user_in.unit_no,
        "postcode": user_in.postcode,
        "role": selected_role,  
        "status": UserStatus.pending,  
    }
    
    user_crud = CRUDOperations(Users)
    try:  
        new_user = user_crud.create(db, user_data)
        if not new_user:
            raise HTTPException(status_code=500, detail="Failed to create user")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during creation: {str(e)}")
    
    return UserRead(
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        contact_no=new_user.contact_no,
        role=new_user.role.value,
        status=new_user.status.value,
    )

@auth_router.get("/users/me", response_model=UserRead)
def read_users_me(current_user: Users = Depends(get_current_active_user)):
    """
    Get profile of the current authenticated user.
    Requires valid JWT token and active status.
    """
    return UserRead(
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        contact_no=current_user.contact_no,
        role=current_user.role.value,
        status=current_user.status.value,
    )
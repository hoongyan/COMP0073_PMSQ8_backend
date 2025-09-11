import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies.db import db_dependency 
from src.models.data_model import Users, UserStatus  
from app.model import TokenData  
from config.settings import get_settings  


settings = get_settings()
SECRET_KEY = settings.secret_key 
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(email: str, password: str, db: db_dependency):
    try: 
        user = db.query(Users).filter(Users.email == email).first()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during authentication: {str(e)}")
    
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(db: db_dependency, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)  
    except JWTError:
        raise credentials_exception
    try: 
        user = db.query(Users).filter(Users.email == token_data.email).first()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during user retrieval: {str(e)}")
    
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: Users = Depends(get_current_user)):
    if current_user.status != UserStatus.active:  
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
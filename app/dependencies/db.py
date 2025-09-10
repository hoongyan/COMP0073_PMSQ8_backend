import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

from src.database.database_operations import get_db 

db_dependency = Annotated[Session, Depends(get_db)]
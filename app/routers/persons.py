import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Annotated, List
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies.db import db_dependency
from app.dependencies.auth import get_current_active_user
from src.database.database_operations import CRUDOperations
from src.models.data_model import PersonDetails, Users, ReportPersonsLink
from app.model import PersonListResponse, PersonResponse, PersonRequest, LinkedReport

persons_router = APIRouter(
    prefix="/persons",
    tags=["persons"],
)

FIELDS_TO_UPPERCASE = [
    'first_name', 'last_name', 'nationality', 'race', 'occupation',
    'blk', 'street', 'unit_no', 'postcode'
]

@persons_router.get("/", response_model=PersonListResponse)
def get_persons_endpoint(
    db: db_dependency,
    current_user: Users = Depends(get_current_active_user),  # Role-Based Account Control (RBAC): Any active authenticated user
    limit: int = 100,
    offset: int = 0
):
    """
    Retrieve a list of persons with pagination.
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    person_crud = CRUDOperations(PersonDetails)
    try:
        persons = person_crud.read_all(db, limit=limit, offset=offset)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during read: {str(e)}")
    
    enriched_persons = [
        PersonResponse(
            person_id=person.person_id,
            first_name=person.first_name,
            last_name=person.last_name,
            sex=person.sex,
            dob=person.dob,
            nationality=person.nationality,
            race=person.race,
            occupation=person.occupation,
            contact_no=person.contact_no,
            email=person.email,
            blk=person.blk,
            street=person.street,
            unit_no=person.unit_no,
            postcode=person.postcode
        ) for person in persons
    ]
    
    return PersonListResponse(persons=enriched_persons)

@persons_router.post("/", response_model=PersonResponse)
def create_person_endpoint(
    db: db_dependency,
    data: PersonRequest = Body(...),
    current_user: Users = Depends(get_current_active_user)  # RBAC: Any active authenticated user
):
    """
    Create a new person.
    - All fields except person_id are required.
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    create_data = data.dict(exclude_unset=True)
    
    #Ensure required fields are present
    required = ['first_name', 'last_name', 'contact_no', 'email']
    missing = [field for field in required if field not in create_data or create_data[field] is None]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")
    
    #Uppercase specified fields if present
    for field in FIELDS_TO_UPPERCASE:
        if field in create_data and isinstance(create_data[field], str):
            create_data[field] = create_data[field].upper()
            
    if 'dob' in create_data and create_data['dob']:
        try:
            create_data['dob'] = datetime.strptime(create_data['dob'], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid format for dob (use YYYY-MM-DD)")
    
    person_crud = CRUDOperations(PersonDetails)
    try:
        new_person = person_crud.create(db, create_data)
        if not new_person:
            raise HTTPException(status_code=500, detail="Failed to create person")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during creation: {str(e)}")
    
    return PersonResponse(
        person_id=new_person.person_id,
        first_name=new_person.first_name,
        last_name=new_person.last_name,
        sex=new_person.sex,
        dob=new_person.dob,
        nationality=new_person.nationality,
        race=new_person.race,
        occupation=new_person.occupation,
        contact_no=new_person.contact_no,
        email=new_person.email,
        blk=new_person.blk,
        street=new_person.street,
        unit_no=new_person.unit_no,
        postcode=new_person.postcode
    )

@persons_router.put("/{person_id}", response_model=PersonResponse)
def update_person_endpoint(
    db: db_dependency,
    person_id: int,
    data: PersonRequest = Body(...),
    current_user: Users = Depends(get_current_active_user)  # RBAC: Any active authenticated user
):
    """
    Update a person by its person_id.
    - Provide only the fields to update in the request body.
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    # Uppercase specified fields if present 
    for field in FIELDS_TO_UPPERCASE:
        if field in update_data and isinstance(update_data[field], str):
            update_data[field] = update_data[field].upper()
            
    if 'dob' in update_data and update_data['dob']:
        try:
            update_data['dob'] = datetime.strptime(update_data['dob'], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid format for dob (use YYYY-MM-DD)")
    
    person_crud = CRUDOperations(PersonDetails)
    try:
        updated_person = person_crud.update(db, person_id, update_data)
        if not updated_person:
            raise HTTPException(status_code=404, detail=f"Person with ID {person_id} not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during update: {str(e)}")

    return PersonResponse(
        person_id=updated_person.person_id,
        first_name=updated_person.first_name,
        last_name=updated_person.last_name,
        sex=updated_person.sex,
        dob=updated_person.dob,
        nationality=updated_person.nationality,
        race=updated_person.race,
        occupation=updated_person.occupation,
        contact_no=updated_person.contact_no,
        email=updated_person.email,
        blk=updated_person.blk,
        street=updated_person.street,
        unit_no=updated_person.unit_no,
        postcode=updated_person.postcode
    )

@persons_router.delete("/{person_id}", status_code=204)
def delete_person_endpoint(
    db: db_dependency,
    person_id: int,
    current_user: Users = Depends(get_current_active_user)  # RBAC: Any active authenticated user
):
    """
    Delete a person by its person_id.
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    person_crud = CRUDOperations(PersonDetails)
    try:
        deleted = person_crud.delete(db, person_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Person with ID {person_id} not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during delete: {str(e)}")
    return None

@persons_router.get("/{person_id}/linked_reports", response_model=List[LinkedReport])
def get_linked_reports_endpoint(
    person_id: int,
    db: db_dependency,
    current_user: Users = Depends(get_current_active_user)  # RBAC: Any active authenticated user
):
    """
    Retrieve linked reports for a person by person_id.
    Returns list of {report_id: str, role: str (lowercase)}.
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    try:
        links = db.query(ReportPersonsLink).filter(ReportPersonsLink.person_id == person_id).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during read: {str(e)}")
        

    if not links:
        return []  
    
    enriched_links = [
        LinkedReport(
            report_id=str(link.report_id),
            role=link.role.value.lower()
        ) for link in links
    ]
    return enriched_links
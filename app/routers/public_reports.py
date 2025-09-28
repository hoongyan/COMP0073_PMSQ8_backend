import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import APIRouter, HTTPException, Body, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date

from app.dependencies.db import db_dependency
from app.model import PublicReportResponse, PublicReportSubmission
from src.database.database_operations import CRUDOperations, db_manager
from src.database.vector_operations import VectorStore
from src.models.data_model import ScamReports, PersonDetails, ReportPersonsLink, ReportStatus, PersonRole, Conversations

public_reports_router = APIRouter(
    prefix="/public/reports",
    tags=["public_reports"],
)

PERSON_FIELDS_TO_UPPERCASE = [
    'first_name', 'last_name', 'nationality', 'race', 'occupation',
    'blk', 'street', 'unit_no', 'postcode'
]
REPORT_FIELDS_TO_UPPERCASE = [
    'scam_type', 'scam_approach_platform', 'scam_communication_platform',
    'scam_transaction_type', 'scam_beneficiary_platform', 'scam_beneficiary_identifier'
]

def get_vector_store():
    return VectorStore(db_manager.session_factory)

@public_reports_router.post("/submit", response_model=PublicReportResponse)
def submit_public_report(
    db: db_dependency,
    data: PublicReportSubmission = Body(...),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Public endpoint for submitting a scam report.
    Creates person, report, and link. No auth required.
    Accessible by public users.
    """
    create_data = data.dict(exclude_unset=True)
    
    #Required fields check
    person_required = ['first_name', 'last_name', 'contact_no', 'email']
    report_required = ['scam_incident_date', 'scam_incident_description']
    missing = [field for field in person_required + report_required if field not in create_data or create_data[field] is None]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")
    
    # Prepare person data with uppercasing
    person_data = {k: create_data.get(k) for k in PersonDetails.__table__.columns.keys() if k in create_data}
    for field in PERSON_FIELDS_TO_UPPERCASE:
        if field in person_data and isinstance(person_data[field], str):
            person_data[field] = person_data[field].upper()
    if 'dob' in person_data and person_data['dob']:
        try:
            person_data['dob'] = datetime.strptime(person_data['dob'], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid format for dob (use YYYY-MM-DD)")
    if person_data.get("dob") and person_data["dob"] > date.today():
        raise HTTPException(status_code=400, detail="Date of birth cannot be in the future")

    # Prepare report data with uppercasing and embedding
    report_data = {k: create_data.get(k) for k in ScamReports.__table__.columns.keys() if k in create_data}
    for field in REPORT_FIELDS_TO_UPPERCASE:
        if field in report_data and isinstance(report_data[field], str):
            report_data[field] = report_data[field].upper()
    report_data["scam_incident_date"] = datetime.strptime(create_data["scam_incident_date"], "%Y-%m-%d").date()
    report_data["scam_report_date"] = datetime.strptime(create_data["scam_report_date"], "%Y-%m-%d").date() if create_data.get("scam_report_date") else date.today()
    report_data["status"] = ReportStatus.unassigned
    report_data["io_in_charge"] = None
    
    if report_data["scam_incident_date"] > report_data["scam_report_date"] or report_data["scam_report_date"] > date.today():
        raise HTTPException(status_code=400, detail="Invalid dates: incident_date <= report_date <= today")
    
    # Embedding 
    embedding = vector_store.get_embedding(report_data["scam_incident_description"])
    report_data["embedding"] = embedding

    role_str = data.role.lower().strip() if data.role else 'reportee'  # Added .strip() for safety (removes extra spaces)
    try:
        link_role = PersonRole[role_str]  # Use lowercase role_str directly
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid role: '{role_str}'. Must be one of: victim, suspect, witness, reportee")
    
    #Create records
    person_crud = CRUDOperations(PersonDetails)
    report_crud = CRUDOperations(ScamReports)
    link_crud = CRUDOperations(ReportPersonsLink)
    conv_crud = CRUDOperations(Conversations)

    try:
        new_person = person_crud.create(db, person_data)
        if not new_person:
            raise HTTPException(status_code=500, detail="Failed to create person record")

        new_report = report_crud.create(db, report_data)
        if not new_report:
            raise HTTPException(status_code=500, detail="Failed to create report record")

        # Link with specified role 
        link_data = {
            "report_id": new_report.report_id,
            "person_id": new_person.person_id,
            "role": link_role,
        }
        new_link = link_crud.create(db, link_data)
        if not new_link:
            raise HTTPException(status_code=500, detail="Failed to link person to report")

        # If conversation_id provided, link it to the new report
        linked_conv_id = None
        if data.conversation_id:
            conversation = db.query(Conversations).filter(Conversations.conversation_id == data.conversation_id).first()
            if not conversation:
                raise HTTPException(status_code=404, detail=f"Conversation with ID {data.conversation_id} not found")
            # Update conversation's report_id
            conv_update = {"report_id": new_report.report_id}
            updated_conv = conv_crud.update(db, data.conversation_id, conv_update)
            if not updated_conv:
                raise HTTPException(status_code=500, detail="Failed to link conversation to report")
            linked_conv_id = updated_conv.conversation_id

        return PublicReportResponse(report_id=new_report.report_id, conversation_id=linked_conv_id)
    
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(ve)}")
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import APIRouter, HTTPException, Body, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from typing import List, Annotated
from datetime import datetime

from config.settings import get_settings
from src.database.database_operations import get_db, CRUDOperations
from src.models.data_model import ScamReports, Users, ReportPersonsLink, PersonDetails, Conversations, Messages
from app.model import ScamReportResponse, ScamReportListResponse, ReportRequest, PersonResponse, PersonListResponse, PersonRequest, LinkedReport, ConversationListResponse, FrontendMessage, FrontendConversation, UserListResponse, UserResponse, UserRequest


router = APIRouter()

settings = get_settings()


db_dependency = Annotated[Session, Depends(get_db)]



@router.get("/get_reports", response_model=ScamReportListResponse)
def get_reports_endpoint( db: db_dependency,limit: int = 100, offset: int = 0,):
    """
    Retrieve a list of scam reports with pagination, including joined data for IO and linked persons.
    """
    scam_crud = CRUDOperations(ScamReports)
    
    # Use enriched query with joins
    reports = db.query(ScamReports).options(
        joinedload(ScamReports.io),
        joinedload(ScamReports.pois).joinedload(ReportPersonsLink.person)
    ).offset(offset).limit(limit).all()
    
    if not reports:
        raise HTTPException(status_code=404, detail="No reports found")
    
    enriched_reports = []
    for report in reports:
        io_name = f"{report.io.first_name} {report.io.last_name}" if report.io else ""
        linked_persons = [
            {
                "id": str(poi.person.person_id),
                "name": f"{poi.person.first_name} {poi.person.last_name}",
                "role": poi.role.value.lower()
            } for poi in report.pois
        ]
        status_title = report.status.value.capitalize()  # Convert to title case, e.g., "Unassigned"
        
        enriched = ScamReportResponse(
            report_id=report.report_id,
            scam_incident_date=report.scam_incident_date,
            scam_report_date=report.scam_report_date,
            scam_type=report.scam_type,
            scam_approach_platform=report.scam_approach_platform,
            scam_communication_platform=report.scam_communication_platform,
            scam_transaction_type=report.scam_transaction_type,
            scam_beneficiary_platform=report.scam_beneficiary_platform,
            scam_beneficiary_identifier=report.scam_beneficiary_identifier,
            scam_contact_no=report.scam_contact_no,
            scam_email=report.scam_email,
            scam_moniker=report.scam_moniker,
            scam_url_link=report.scam_url_link,
            scam_amount_lost=report.scam_amount_lost,
            scam_incident_description=report.scam_incident_description,
            status=status_title,
            assigned_IO=io_name,
            linked_persons=linked_persons
        )
        enriched_reports.append(enriched)
    
    return ScamReportListResponse(reports=enriched_reports)



@router.delete("/delete_reports/{report_id}", status_code=204)
def delete_report_endpoint( db: db_dependency,report_id: int):
    """
    Delete a scam report by its report_id.
    """
    scam_crud = CRUDOperations(ScamReports)
    deleted = scam_crud.delete(db, report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    return None




@router.put("/update_reports/{report_id}", response_model=ScamReportResponse)
def update_report_endpoint( db: db_dependency, report_id: int, data: ReportRequest = Body(...)):
    """
    Update a scam report by its report_id.
    - Provide only the fields to update in the request body.
    """
    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    if 'scam_incident_date' in update_data:
        try:
            update_data['scam_incident_date'] = datetime.strptime(update_data['scam_incident_date'], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid format for scam_incident_date (use YYYY-MM-DD)")
    if 'scam_report_date' in update_data:
        try:
            update_data['scam_report_date'] = datetime.strptime(update_data['scam_report_date'], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid format for scam_report_date (use YYYY-MM-DD)")
    
    # Handle status to uppercase enum
    if 'status' in update_data:
        update_data['status'] = update_data['status'].upper()
    
    scam_crud = CRUDOperations(ScamReports)
    updated_report = scam_crud.update(db, report_id, update_data)
    if not updated_report:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    
    # Enrich the response (similar to get_reports)
    io_name = f"{updated_report.io.first_name} {updated_report.io.last_name}" if updated_report.io else ""
    linked_persons = [
        {
            "id": str(poi.person.person_id),
            "name": f"{poi.person.first_name} {poi.person.last_name}",
            "role": poi.role.value.lower()
        } for poi in updated_report.pois
    ]
    status_title = updated_report.status.value.capitalize()
    
    return ScamReportResponse(
        scam_report_no=updated_report.report_id,
        scam_incident_date=updated_report.scam_incident_date,
        scam_report_date=updated_report.scam_report_date,
        scam_type=updated_report.scam_type,
        scam_approach_platform=updated_report.scam_approach_platform,
        scam_communication_platform=updated_report.scam_communication_platform,
        scam_transaction_type=updated_report.scam_transaction_type,
        scam_beneficiary_platform=updated_report.scam_beneficiary_platform,
        scam_beneficiary_identifier=updated_report.scam_beneficiary_identifier,
        scam_contact_no=updated_report.scam_contact_no,
        scam_email=updated_report.scam_email,
        scam_moniker=updated_report.scam_moniker,
        scam_url_link=updated_report.scam_url_link,
        scam_amount_lost=updated_report.scam_amount_lost,
        scam_incident_description=updated_report.scam_incident_description,
        status=status_title,
        assigned_IO=io_name,
        linked_persons=linked_persons
    )



@router.get("/users", response_model=UserListResponse)
def get_users_endpoint(db: db_dependency, limit: int = 100, offset: int = 0):
    """
    Retrieve a list of users with pagination.
    """
    user_crud = CRUDOperations(Users)
    
    users = db.query(Users).order_by(Users.user_id.asc()).offset(offset).limit(limit).all()
    
    if not users:
        raise HTTPException(status_code=404, detail="No users found")
    
    enriched_users = []
    for user in users:
        enriched = UserResponse(
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
        )
        enriched_users.append(enriched)
    
    return UserListResponse(users=enriched_users)

@router.post("/users", response_model=UserResponse)
def create_user_endpoint(db: db_dependency, data: UserRequest = Body(...)):
    """
    Create a new user.
    - Required fields: password, first_name, last_name, contact_no, email, role
    """
    create_data = data.dict(exclude_unset=True)
    if not create_data:
        raise HTTPException(status_code=400, detail="No data provided")
    
    required_fields = ['password', 'first_name', 'last_name', 'contact_no', 'email', 'role']
    missing = [field for field in required_fields if field not in create_data or create_data[field] is None]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")
    
    if 'dob' in create_data and create_data['dob']:
        try:
            create_data['dob'] = datetime.strptime(create_data['dob'], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid format for dob (use YYYY-MM-DD)")
    
    if 'role' in create_data:
        create_data['role'] = create_data['role'].upper()
    
    if 'status' in create_data:
        create_data['status'] = create_data['status'].upper()
    
    user_crud = CRUDOperations(Users)
    new_user = user_crud.create(db, create_data)
    if not new_user:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
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

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_endpoint(db: db_dependency, user_id: int, data: UserRequest = Body(...)):
    """
    Update a user by its user_id.
    - Provide only the fields to update in the request body.
    """
    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    if 'dob' in update_data and update_data['dob']:
        try:
            update_data['dob'] = datetime.strptime(update_data['dob'], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid format for dob (use YYYY-MM-DD)")
    
    if 'role' in update_data:
        update_data['role'] = update_data['role'].upper()
    
    if 'status' in update_data:
        update_data['status'] = update_data['status'].upper()
    
    user_crud = CRUDOperations(Users)
    updated_user = user_crud.update(db, user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    
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

@router.delete("/users/{user_id}", status_code=204)
def delete_user_endpoint(db: db_dependency, user_id: int):
    """
    Delete a user by its user_id.
    """
    user_crud = CRUDOperations(Users)
    deleted = user_crud.delete(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    return None






import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from typing import Annotated, List
from datetime import datetime, date

from app.dependencies.db import db_dependency
from app.dependencies.auth import get_current_active_user
from src.database.database_operations import CRUDOperations, db_manager
from src.database.vector_operations import VectorStore
from src.models.data_model import ScamReports, Users, ReportPersonsLink, PersonDetails, ReportStatus, PersonRole
from app.model import ScamReportListResponse, ScamReportResponse, ReportRequest, LinkedPerson, LinkedPersonCreate

reports_router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)

FIELDS_TO_UPPERCASE = [
    'scam_type', 'scam_approach_platform', 'scam_communication_platform',
    'scam_transaction_type', 'scam_beneficiary_platform', 'scam_beneficiary_identifier', 'status'
]

def get_vector_store():
    """Dependency to provide VectorStore instance."""
    return VectorStore(db_manager.session_factory)

def enrich_report(db: Session, report: ScamReports) -> ScamReportResponse:
    """Helper to enrich a single report with IO name, linked persons, and status title."""

    io_name = f"{report.io.first_name} {report.io.last_name}" if report.io else ""
    linked_persons = [
        LinkedPerson(
            id=str(poi.person.person_id),
            name=f"{poi.person.first_name} {poi.person.last_name}",
            role=poi.role.value.lower()
        ) for poi in report.pois
    ]
    status_title = report.status.value.capitalize()  
    
    return ScamReportResponse(
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

@reports_router.get("/", response_model=ScamReportListResponse)
def get_reports_endpoint(
    db: db_dependency,
    current_user: Users = Depends(get_current_active_user),  # RBAC: Any active authenticated user
    limit: int = 100,
    offset: int = 0
):
    """
    Retrieve a list of scam reports with pagination, including joined data for IO and linked persons.
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    try:
        reports = db.query(ScamReports).options(
            joinedload(ScamReports.io),
            joinedload(ScamReports.pois).joinedload(ReportPersonsLink.person)
        ).order_by(ScamReports.report_id.asc()).offset(offset).limit(limit).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during read: {str(e)}")
    
    if not reports:
        # raise HTTPException(status_code=404, detail="No reports found")
        return ScamReportListResponse(reports=[])
    
    enriched_reports = [enrich_report(db, report) for report in reports]
    return ScamReportListResponse(reports=enriched_reports)

@reports_router.post("/", response_model=ScamReportResponse)
def create_report_endpoint(
    db: db_dependency,
    data: ReportRequest = Body(...),
    vector_store: VectorStore = Depends(get_vector_store),
    current_user: Users = Depends(get_current_active_user)  # RBAC: Any active authenticated user
):
    """
    Create a new scam report.
    - Required fields: scam_incident_date, scam_report_date, scam_incident_description (must be non-empty).
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    create_data = data.dict(exclude_unset=True)
    
    # Ensure required fields and non-empty description
    required = ['scam_incident_date', 'scam_report_date', 'scam_incident_description']
    missing = [field for field in required if field not in create_data or create_data[field] is None]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")
    if not create_data['scam_incident_description'].strip():
        raise HTTPException(status_code=400, detail="scam_incident_description cannot be empty")
    
    # Uppercase specified fields
    for field in FIELDS_TO_UPPERCASE:
        if field in create_data and isinstance(create_data[field], str):
            create_data[field] = create_data[field].upper()
    
    # Validate and convert dates
    today = date.today()
    try:
        incident_date = datetime.strptime(create_data['scam_incident_date'], "%Y-%m-%d").date()
        report_date = datetime.strptime(create_data['scam_report_date'], "%Y-%m-%d").date()
        if incident_date > report_date or report_date > today:
            raise ValueError("Invalid dates: incident_date <= report_date <= today")
        create_data['scam_incident_date'] = incident_date
        create_data['scam_report_date'] = report_date
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid date format or logic: {str(ve)} (use YYYY-MM-DD)")
    
    # Validate amount if provided
    if 'scam_amount_lost' in create_data and create_data['scam_amount_lost'] < 0:
        raise HTTPException(status_code=400, detail="scam_amount_lost must be >= 0")
    
    # Validate io_in_charge if provided (user exists)
    if 'io_in_charge' in create_data:
        io_id = create_data['io_in_charge']
        if db.query(Users).filter(Users.user_id == io_id).first() is None:
            raise HTTPException(status_code=400, detail=f"Invalid io_in_charge: User ID {io_id} does not exist")
    
    # Validate status if provided (defaults to UNASSIGNED in model)
    if 'status' in create_data:
        try:
            ReportStatus[create_data['status'].lower()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: Must be one of {', '.join([s.value for s in ReportStatus])}")
    
    # Enforce consistency between io_in_charge and status
    if 'io_in_charge' in create_data or 'status' in create_data:
        new_io = create_data.get('io_in_charge')
        new_status = create_data.get('status', ReportStatus.unassigned.value)  # Default if not provided
        
        if new_io is not None and new_status != 'RESOLVED':
            create_data['status'] = 'ASSIGNED'
        elif new_io is None and new_status != 'RESOLVED':
            create_data['status'] = 'UNASSIGNED'
        
        # Validate for consistency (prevent invalid combos)
        if new_status == 'ASSIGNED' and new_io is None:
            raise HTTPException(status_code=400, detail="Cannot set status to ASSIGNED without io_in_charge")
        if new_status == 'UNASSIGNED' and new_io is not None:
            raise HTTPException(status_code=400, detail="Cannot set status to UNASSIGNED with io_in_charge provided")
        
    scam_crud = CRUDOperations(ScamReports)
    try:
        new_report = scam_crud.create(db, create_data)
        if not new_report:
            raise HTTPException(status_code=500, detail="Failed to create report")
        
        # Generate embedding (since description non-empty)
        embedding = vector_store.get_embedding(new_report.scam_incident_description)
        updated = scam_crud.update_embedding(db, new_report.report_id, embedding)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update embedding")
        
        # Load joins for enrich
        new_report = db.query(ScamReports).options(
            joinedload(ScamReports.io),
            joinedload(ScamReports.pois).joinedload(ReportPersonsLink.person)
        ).filter(ScamReports.report_id == new_report.report_id).first()
        
        return enrich_report(db, new_report)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during creation: {str(e)}")

@reports_router.put("/{report_id}", response_model=ScamReportResponse)
def update_report_endpoint(
    db: db_dependency,
    report_id: int,
    data: ReportRequest = Body(...),
    vector_store: VectorStore = Depends(get_vector_store),
    current_user: Users = Depends(get_current_active_user)  # RBAC: Any active authenticated user
):
    """
    Update a scam report by report_id.
    - Provide only fields to update. If updating description, it cannot be empty.
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Check non-empty if updating description
    if 'scam_incident_description' in update_data and not update_data['scam_incident_description'].strip():
        raise HTTPException(status_code=400, detail="scam_incident_description cannot be empty")
    
    # Uppercase specified fields
    for field in FIELDS_TO_UPPERCASE:
        if field in update_data and isinstance(update_data[field], str):
            update_data[field] = update_data[field].upper()
    
    # Validate and convert dates if provided
    today = date.today()
    if 'scam_incident_date' in update_data or 'scam_report_date' in update_data:
        try:
            # Fetch current for cross-validation
            current_report = db.query(ScamReports).filter(ScamReports.report_id == report_id).first()
            if not current_report:
                raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
            
            incident_str = update_data.get('scam_incident_date', current_report.scam_incident_date.strftime("%Y-%m-%d"))
            report_str = update_data.get('scam_report_date', current_report.scam_report_date.strftime("%Y-%m-%d"))
            incident_date = datetime.strptime(incident_str, "%Y-%m-%d").date()
            report_date = datetime.strptime(report_str, "%Y-%m-%d").date()
            if incident_date > report_date or report_date > today:
                raise ValueError("Invalid dates: incident_date <= report_date <= today")
            update_data['scam_incident_date'] = incident_date
            update_data['scam_report_date'] = report_date
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid date format or logic: {str(ve)} (use YYYY-MM-DD)")
    
    # Validate amount if provided
    if 'scam_amount_lost' in update_data and update_data['scam_amount_lost'] < 0:
        raise HTTPException(status_code=400, detail="scam_amount_lost must be >= 0")
    
    # Validate io_in_charge if provided
    if 'io_in_charge' in update_data:
        io_id = update_data['io_in_charge']
        if db.query(Users).filter(Users.user_id == io_id).first() is None:
            raise HTTPException(status_code=400, detail=f"Invalid io_in_charge: User ID {io_id} does not exist")
    
    # Validate status if provided
    if 'status' in update_data:
        try:
            ReportStatus[update_data['status'].lower()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: Must be one of {', '.join([s.value for s in ReportStatus])}")
    
    # Enforce consistency between io_in_charge and status
    if 'io_in_charge' in update_data or 'status' in update_data:
        current_report = db.query(ScamReports).filter(ScamReports.report_id == report_id).first()
        if not current_report:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        
        new_io = update_data.get('io_in_charge', current_report.io_in_charge)
        new_status = update_data.get('status', current_report.status.value)
        
        if new_io is not None and new_status != 'RESOLVED':
            update_data['status'] = 'ASSIGNED'
        elif new_io is None and new_status != 'RESOLVED':
            update_data['status'] = 'UNASSIGNED'
        
        # Validate for consistency (prevent invalid combos)
        if new_status == 'ASSIGNED' and new_io is None:
            raise HTTPException(status_code=400, detail="Cannot set status to ASSIGNED without io_in_charge")
        if new_status == 'UNASSIGNED' and new_io is not None:
            raise HTTPException(status_code=400, detail="Cannot set status to UNASSIGNED with io_in_charge provided")
        
    scam_crud = CRUDOperations(ScamReports)
    try:
        updated_report = scam_crud.update(db, report_id, update_data)
        if not updated_report:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        
        # Generate embedding if description updated
        if 'scam_incident_description' in update_data:
            description = update_data['scam_incident_description']
            embedding = vector_store.get_embedding(description) if description.strip() else None
            updated_emb = scam_crud.update_embedding(db, report_id, embedding)
            if not updated_emb:
                raise HTTPException(status_code=500, detail="Failed to update embedding")
        
        # Load joins for enrich
        updated_report = db.query(ScamReports).options(
            joinedload(ScamReports.io),
            joinedload(ScamReports.pois).joinedload(ReportPersonsLink.person)
        ).filter(ScamReports.report_id == report_id).first()
        
        return enrich_report(db, updated_report)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during update: {str(e)}")

@reports_router.delete("/{report_id}", status_code=204)
def delete_report_endpoint(
    db: db_dependency,
    report_id: int,
    current_user: Users = Depends(get_current_active_user)  # RBAC: Any active authenticated user
):
    """
    Delete a scam report by report_id.
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    scam_crud = CRUDOperations(ScamReports)
    try:
        deleted = scam_crud.delete(db, report_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during delete: {str(e)}")
    return None

@reports_router.get("/{report_id}/linked_persons", response_model=List[LinkedPerson])
def get_linked_persons_endpoint(
    report_id: int,
    db: db_dependency,
    current_user: Users = Depends(get_current_active_user)  # RBAC: Any active authenticated user
):
    """
    Retrieve linked persons for a report by report_id.
    Returns list of {id: str, name: str, role: str (lowercase)}.
    Accessible by any active authenticated user (Admin, IO, Analyst).
    """
    try:
        links = db.query(ReportPersonsLink).options(
            joinedload(ReportPersonsLink.person)
        ).filter(ReportPersonsLink.report_id == report_id).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during read: {str(e)}")
    
    enriched_links = [
        LinkedPerson(
            id=str(link.person.person_id),
            name=f"{link.person.first_name} {link.person.last_name}",
            role=link.role.value.lower()
        ) for link in links
    ]
    return enriched_links


@reports_router.post("/{report_id}/linked_persons", response_model=LinkedPerson)
def add_linked_person_endpoint(
    report_id: int,
    data: LinkedPersonCreate,
    db: db_dependency,
    current_user: Users = Depends(get_current_active_user)
):
    """
    Add a linked person to a report.
    Requires person_id (must exist) and role (victim/suspect/witness/reportee).
    """
    # Validate report exists
    report = db.query(ScamReports).filter(ScamReports.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    
    # Validate person exists
    person = db.query(PersonDetails).filter(PersonDetails.person_id == data.person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail=f"Person with ID {data.person_id} not found")
    
    # Validate role
    try:
        role_enum = PersonRole[data.role.lower()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid role: Must be one of {', '.join([r.value.lower() for r in PersonRole])}")
    
    # Check if link already exists
    existing = db.query(ReportPersonsLink).filter(
        ReportPersonsLink.report_id == report_id,
        ReportPersonsLink.person_id == data.person_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This person is already linked to the report")
    
    # Create link
    new_link = ReportPersonsLink(
        report_id=report_id,
        person_id=data.person_id,
        role=role_enum
    )
    db.add(new_link)
    try:
        db.commit()
        db.refresh(new_link)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during creation: {str(e)}")
    
    # Return enriched
    return LinkedPerson(
        id=str(new_link.person.person_id),
        name=f"{new_link.person.first_name} {new_link.person.last_name}",
        role=new_link.role.value.lower()
    )

@reports_router.delete("/{report_id}/linked_persons/{person_id}", status_code=204)
def delete_linked_person_endpoint(
    report_id: int,
    person_id: int,
    db: db_dependency,
    current_user: Users = Depends(get_current_active_user)
):
    """
    Delete a linked person from a report by person_id.
    """
    link = db.query(ReportPersonsLink).filter(
        ReportPersonsLink.report_id == report_id,
        ReportPersonsLink.person_id == person_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Linked person not found for this report")
    
    try:
        db.delete(link)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during delete: {str(e)}")
    return None
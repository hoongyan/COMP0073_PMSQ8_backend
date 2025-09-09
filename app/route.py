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



# # Mock dependency for user authentication (replace with your actual auth logic)
# async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
#     if token:
#         # Replace with actual user lookup logic (e.g., decode JWT)
#         return {"user_id": 1}  # Example: Return user_id from token
#     return None

db_dependency = Annotated[Session, Depends(get_db)]

# @router.get("/test-db")
# def test_db_connection(db: Session = Depends(get_db)):
#     try:
#         # Run a simple query to test connection
#         result = db.execute(text("SELECT 1")).scalar()
#         if result == 1:
#             return {"status": "success", "message": "Database connection works! Query returned: " + str(result)}
#         else:
#             raise HTTPException(status_code=500, detail="Unexpected query result")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")
    











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


@router.get("/persons", response_model=PersonListResponse)
def get_persons(db: db_dependency, limit: int = 100, offset: int = 0):
    """
    Get a list of persons (pagination with limit/offset). Frontend handles filtering/sorting client-side.
    """
    # Perform the query directly with ordering by person_id ascending for consistent pagination
    persons = db.query(PersonDetails).order_by(PersonDetails.person_id.asc()).offset(offset).limit(limit).all()
    
    if not persons:
        raise HTTPException(status_code=404, detail="No persons found")
    
    enriched_persons = []
    for person in persons:
        enriched = PersonResponse(
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
        )
        enriched_persons.append(enriched)
    
    return PersonListResponse(persons=enriched_persons)


@router.post("/persons", response_model=PersonResponse, status_code=201)
def create_person(db: db_dependency, data: PersonRequest = Body(...)) :
    """
    Create a new person. Required: first_name, last_name, contact_no, email.
    """
    create_data = data.dict(exclude_unset=True)
    if not create_data:
        raise HTTPException(status_code=400, detail="No data provided")
    
    # Basic required fields (matches data model non-nullables)
    required_fields = ["first_name", "last_name", "contact_no", "email"]
    for field in required_fields:
        if field not in create_data or not create_data[field]:
            raise HTTPException(status_code=400, detail=f"Missing or empty required field: {field}")
    
    # Convert dob if provided
    if "dob" in create_data:
        try:
            create_data["dob"] = datetime.strptime(create_data["dob"], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid dob format (use YYYY-MM-DD)")
    
    person_crud = CRUDOperations(PersonDetails)
    new_person = person_crud.create(db, create_data)
    
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

@router.put("/persons/{person_id}", response_model=PersonResponse)
def update_person(db: db_dependency,person_id: int, data: PersonRequest = Body(...)):
    """
    Update a person (partial OK).
    """
    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Convert dob if provided
    if "dob" in update_data:
        try:
            update_data["dob"] = datetime.strptime(update_data["dob"], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid dob format (use YYYY-MM-DD)")
    
    person_crud = CRUDOperations(PersonDetails)
    updated_person = person_crud.update(db, person_id, update_data)
    if not updated_person:
        raise HTTPException(status_code=404, detail=f"Person with ID {person_id} not found")
    
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

@router.delete("/persons/{person_id}", status_code=204)
def delete_person(db: db_dependency, person_id: int):
    """
    Delete a person by ID (cascades to links).
    """
    person_crud = CRUDOperations(PersonDetails)
    deleted = person_crud.delete(db, person_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Person with ID {person_id} not found")
    return None

@router.get("/persons/{person_id}/linked_reports", response_model=List[LinkedReport])
def get_linked_reports(person_id: int, db: db_dependency):
    """
    Get linked reports (with per-report roles) for details popup.
    """
    links = db.query(ReportPersonsLink).filter(ReportPersonsLink.person_id == person_id).all()
    reports = []
    for link in links:
        reports.append(LinkedReport(
            report_id=str(link.report_id),
            role=link.role.value.lower()  # e.g., "victim"
        ))
    return reports




@router.get("/conversations", response_model=ConversationListResponse)
def get_conversations_endpoint(db: db_dependency, limit: int = 100, offset: int = 0):
    """
    Retrieve a paginated list of conversations with associated messages.
    - Messages are sorted by message_id ASC (insertion order).
    - Dates are formatted as 'dd/MM/yy HH:mm' to match frontend.
    - Sender roles are used directly as "HUMAN" or "AI" (uppercase to match DB enum).
    - Summary is generated from the first message (truncated to 100 chars + "...") or "No messages" if empty.
    """
    try:
        # Query conversations with eager-loaded messages, ordered by conversation_id asc (increasing order)
        conversations = db.query(Conversations).options(
            joinedload(Conversations.messages)
        ).order_by(Conversations.conversation_id.asc()).offset(offset).limit(limit).all()
        
        if not conversations:
            raise HTTPException(status_code=404, detail="No conversations found")
        
        enriched_conversations = []
        for conv in conversations:
            # Sort messages by message_id ASC (reflects insertion order)
            sorted_messages = sorted(conv.messages, key=lambda m: m.message_id)
            
            formatted_messages = []
            for msg in sorted_messages:
                formatted_role = msg.sender_role.value  # Directly use "HUMAN" or "AI"
                
                formatted_messages.append({
                    "messageId": str(msg.message_id),
                    "conversationId": str(conv.conversation_id),
                    "senderRole": formatted_role,
                    "content": msg.content,
                    "sentDate": msg.sent_datetime.strftime("%d/%m/%y %H:%M")
                })
            
            # Generate summary: Truncate first message content or default
            summary = (
                formatted_messages[0]["content"][:100] + "..." 
                if formatted_messages else "No messages"
            )
            
            enriched = {
                "conversationId": str(conv.conversation_id),
                "reportId": str(conv.report_id) if conv.report_id else None,
                "creationDate": conv.creation_datetime.strftime("%d/%m/%y %H:%M"),
                "messages": formatted_messages,
                "summary": summary
            }
            enriched_conversations.append(enriched)
        
        return ConversationListResponse(conversations=enriched_conversations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversations: {str(e)}")
    
@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation_endpoint(conversation_id: int, db: db_dependency):
    """
    Delete a conversation by ID. Associated messages are automatically deleted via database cascade.
    """
    conv_crud = CRUDOperations(Conversations)
    deleted = conv_crud.delete(db, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Conversation with ID {conversation_id} not found")
    return None


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
            permission=user.permission,
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
        permission=new_user.permission,
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
        permission=updated_user.permission,
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



# @router.post("/submit-report")
# def submit_report_endpoint(request: SubmitReportRequest):
#     """Submit scam report data for a conversation."""
#     db = SessionLocal()
#     try:
#         conversation = db.query(Conversations).filter(Conversations.id == request.conversation_id).first()
#         if not conversation:
#             raise HTTPException(status_code=404, detail=f"Conversation not found for ID: {request.conversation_id}")

#         scam_report = ScamReportData(
#             conversation_id=request.conversation_id,
#             report_data=request.report_data
#         )
#         db.add(scam_report)
#         db.commit()
#         return {"message": f"Scam report submitted successfully for conversation {request.conversation_id}"}
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=400, detail=f"Failed to submit report: {str(e)}")
#     finally:
#         db.close()

# @router.post("/create-police-chatbot")
# def create_police_chatbot_endpoint(config: PoliceChatbotConfig):
#     """Create a police chatbot based on the provided configuration."""

#     if config.llm_provider not in SUPPORTED_MODELS:
#         raise HTTPException(status_code=400, detail=f"Invalid llm_provider. Must be one of {list(SUPPORTED_MODELS.keys())}")
#     if config.model not in SUPPORTED_MODELS[config.llm_provider]:
#         raise HTTPException(status_code=400, detail=f"Invalid model. Must be one of {SUPPORTED_MODELS[config.llm_provider]}")
    
#     response = create_police_chatbot(
#         agent_type=config.agent_type,
#         agent_name=config.agent_name,
#         llm_provider=config.llm_provider,
#         model=config.model,
#         is_rag=config.is_rag,
#         prompt=config.prompt,
#         allow_search=config.allow_search
#     )
#     if "error" in response:
#         raise HTTPException(status_code=400, detail=response["error"])
#     return response



# @router.post("/chat")
# def chat_endpoint(request: ChatRequest):
#     """
#     Continue a conversation with a police chatbot using its agent_id.
    
#     Args:
#         request (ChatRequest): Request containing agent_id, query, and conversation history.
    
#     Returns:
#         dict: AI response and updated conversation history.
    
#     Raises:
#         HTTPException: If the request is invalid or the agent is not found.
#     """
#     response = get_response_from_ai_agent(
#             agent_id=request.agent_id,
#             query=request.query,
#             user_id=request.user_id,  
#             conversation_history=request.conversation_history
#         )
#     if "error" in response:
#         raise HTTPException(status_code=400, detail=response["error"])
#     return response

# @router.get("/conversations")
# def get_conversations_endpoint():
#     """
#     Retrieve all conversations for admin tracking of chatbot simulations.
#     """
#     response = get_conversation_history()
#     if "error" in response:
#         raise HTTPException(status_code=400, detail=response["error"])
#     return response




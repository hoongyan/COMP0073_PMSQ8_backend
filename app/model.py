from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

class PersonRole(str, Enum):
    victim = "victim"
    suspect = "suspect"
    witness = "witness"
    reportee = "reportee"

class LinkedPerson(BaseModel):
    id: str = Field(..., description="Person ID as string")
    name: str = Field(..., description="Full name")
    role: PersonRole
    
class LinkedReport(BaseModel):  
    report_id: str
    role: str

class ReportStatus(str, Enum):
    unassigned = "Unassigned"
    assigned = "Assigned"
    resolved = "Resolved"

class ScamReportResponse(BaseModel):
    report_id: int = Field(..., alias="report_id", description="Report ID as string")
    scam_incident_date: date | None
    scam_report_date: date | None
    scam_type: str | None
    scam_approach_platform: str | None
    scam_communication_platform: str | None
    scam_transaction_type: str | None
    scam_beneficiary_platform: str | None
    scam_beneficiary_identifier: str | None
    scam_contact_no: str | None
    scam_email: str | None
    scam_moniker: str | None
    scam_url_link: str | None
    scam_amount_lost: float | None
    scam_incident_description: str | None
    status: ReportStatus
    assigned_IO: str | None = Field(..., description="IO full name or empty string")
    linked_persons: List[LinkedPerson] = Field(default_factory=list)
    
    
    
class ReportRequest(BaseModel):
    scam_incident_date: Optional[str] = None  # e.g., "2023-01-01"; converted to date in handler
    scam_report_date: Optional[str] = None    # e.g., "2023-01-02"; converted to date in handler
    scam_type: Optional[str] = None
    scam_approach_platform: Optional[str] = None
    scam_communication_platform: Optional[str] = None
    scam_transaction_type: Optional[str] = None
    scam_beneficiary_platform: Optional[str] = None
    scam_beneficiary_identifier: Optional[str] = None
    scam_contact_no: Optional[str] = None
    scam_email: Optional[str] = None
    scam_moniker: Optional[str] = None
    scam_url_link: Optional[str] = None
    scam_amount_lost: Optional[float] = None
    scam_incident_description: Optional[str] = None
    status: Optional[str] = None  # e.g., "assigned" (converted to uppercase enum like "ASSIGNED")
    io_in_charge: Optional[int] = None  # Foreign key to user_id
    
    
class ScamReportListResponse(BaseModel):
    reports: List[ScamReportResponse]




class PersonResponse(BaseModel):
    person_id: int = Field(..., description="Unique person ID (use this as key)")
    first_name: str
    last_name: str
    sex: str | None
    dob: date | None
    nationality: str | None
    race: str | None
    occupation: str | None
    contact_no: str
    email: str
    blk: str | None
    street: str | None
    unit_no: str | None
    postcode: str  | None

class PersonListResponse(BaseModel):
    persons: List[PersonResponse]

class PersonRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    sex: Optional[str] = None
    dob: Optional[str] = None  # String input, convert to date
    nationality: Optional[str] = None
    race: Optional[str] = None
    occupation: Optional[str] = None
    contact_no: Optional[str] = None
    email: Optional[str] = None
    blk: Optional[str] = None
    street: Optional[str] = None
    unit_no: Optional[str] = None
    postcode: Optional[str] = None



class UserRole(str, Enum):
    admin = "ADMIN"
    io = "INVESTIGATION OFFICER"
    analyst = "ANALYST"

class UserStatus(str, Enum):
    pending = "PENDING"
    active = "ACTIVE"
    inactive = "INACTIVE"

class UserResponse(BaseModel):
    user_id: int = Field(..., description="Unique user ID")
    first_name: str
    last_name: str
    sex: str | None
    dob: date | None
    nationality: str | None
    race: str | None
    contact_no: str
    email: str
    blk: str | None
    street: str | None
    unit_no: str | None
    postcode: str | None
    role: str
    status: str
    permission: Dict[str, Any]
    registration_datetime: datetime
    last_updated_datetime: datetime

class UserListResponse(BaseModel):
    users: List[UserResponse]

class UserRequest(BaseModel):
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    sex: Optional[str] = None
    dob: Optional[str] = None  # String input, convert to date
    nationality: Optional[str] = None
    race: Optional[str] = None
    contact_no: Optional[str] = None
    email: Optional[str] = None
    blk: Optional[str] = None
    street: Optional[str] = None
    unit_no: Optional[str] = None
    postcode: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    permission: Optional[Dict[str, Any]] = None




#For auth-related schemas 

# NEW: Auth-related schemas (add these at the bottom)
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenJson(BaseModel):
    token: str
    token_type: str

class SignInRequest(BaseModel):
    email: EmailStr # Validates it's a real email format
    password: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None  # For JWT payload

class UserIn(BaseModel):  # For signup input
    email: EmailStr
    password: str
    first_name: str  # Required for signup
    last_name: str   # Required for signup
    contact_no: str  # Required
    role: Optional[str] = "INVESTIGATION OFFICER"  # Default role; adjust as needed
    # Add other optional fields from UserRequest if you want them in signup
    sex: Optional[str] = None
    dob: Optional[str] = None
    nationality: Optional[str] = None
    race: Optional[str] = None
    blk: Optional[str] = None
    street: Optional[str] = None
    unit_no: Optional[str] = None
    postcode: Optional[str] = None
    permission: Optional[Dict[str, Any]] = {}  # Default empty dict
    
    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        # Optional: Add complexity, e.g., if not any(c.isdigit() for c in v): raise ValueError('Must include digit')
        return v

    @field_validator('first_name', 'last_name')
    def validate_names(cls, v: str) -> str:
        v = v.strip().upper()  # Trim and uppercase (standardize)
        if len(v) < 2:
            raise ValueError('Name too short (min 2 characters)')
        return v

    @field_validator('contact_no')
    def validate_contact_no(cls, v: str) -> str:
        if not v.isdigit() or not (8 <= len(v) <= 12):
            raise ValueError('Contact number must be 8-12 digits')
        return v

    @field_validator('dob', mode='before')  
    def validate_dob(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                dob_date = datetime.strptime(v, "%Y-%m-%d").date()
                if dob_date > date.today():
                    raise ValueError('Date of birth cannot be in the future')
            except ValueError:
                raise ValueError('Invalid DOB format (use YYYY-MM-DD)')
        return v

    @field_validator('sex')
    def validate_sex(cls, v: Optional[str]) -> Optional[str]:
        if v:
            valid = ['MALE', 'FEMALE', 'OTHER'] 
            if v.upper() not in valid:
                raise ValueError(f'Invalid sex: must be one of {valid}')
            return v.upper()  # Standardize
        return v

class UserRead(BaseModel):  # For profile output (no password)
    email: EmailStr
    first_name: str
    last_name: str
    contact_no: str
    role: str
    status: str
    permission: Dict[str, Any] = Field(default={}, description="User permissions dict, e.g., {'reports': 'edit'}")  # NEW: Add this
    # Add more fields if needed, like from UserResponse































class FrontendMessage(BaseModel):
    messageId: str
    conversationId: str
    senderRole: str  # "Human" or "AI"
    content: str
    sentDate: str  # Formatted as 'dd/MM/yy HH:mm'

class FrontendConversation(BaseModel):
    conversationId: str
    reportId: Optional[str]
    creationDate: str  # Formatted as 'dd/MM/yy HH:mm'
    messages: List[FrontendMessage]
    summary: str  # Generated dynamically (e.g., truncated first message)

class ConversationListResponse(BaseModel):
    conversations: List[FrontendConversation]
    

# class ChatRequest(BaseModel):
#     agent_id: int
#     query: str
#     user_id: Optional[int] = None  # Add user_id for authenticated users
#     conversation_history: list = []
    
# class SimulationRequest(BaseModel):
#     police_agent_id: int
#     victim_agent_id: int
#     max_turns: int = 10
#     initial_query: Optional[str] = None

# class Message(BaseModel):
#     id: int
#     content: str
#     sender_type: str
#     sender_id: Optional[int]
#     agent_id: Optional[int]
    
# class Conversation(BaseModel):
#     conversation_id: int
#     title: str
#     description: Optional[str]
#     messages: List[Message]

# class ConversationHistoryResponse(BaseModel):
#     conversations: List[Conversation]


# class SubmitReportRequest(BaseModel):
#     conversation_id: int
#     report_data: Dict
 
# class PoliceResponse(BaseModel):
#     conversational_response: str = Field(..., description="The conversational response to the victim")
#     firstName: str = Field(default="", description="Victim's first name")
#     lastName: str = Field(default="", description="Victim's last name")
#     telNo: str = Field(default="", description="Victim's telephone number")
#     address: str = Field(default="", description="Victim's address")
#     occupation: str = Field(default="", description="Victim's occupation")
#     age: str = Field(default="", description="Victim's age")
#     incidentDate: str = Field(default="", description="Date of the scam incident")
#     reportDate: str = Field(lambda: datetime.now().strftime("%Y-%m-%d"), description="Date the report is filed")
#     location: str = Field(default="", description="Location of the scam incident")
#     crimeType: str = Field(default="", description="Type of crime (e.g., e-commerce scam)")
#     approachPlatform: str = Field(default="", description="Platform where scammer approached victim")
#     communicationPlatform: str = Field(default="", description="Platform used for communication")
#     bank: str = Field(default="", description="Victim's bank name")
#     bankNo: str = Field(default="", description="Victim's bank account number")
#     contactInfo: str = Field(default="", description="Scammer's contact information")
#     description: str = Field(default="", description="Detailed description of the scam")
#     summary: str = Field(default="", description="Summary of the scam incident")
    



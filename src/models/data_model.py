from sqlalchemy import Column, String, Date, Float, Text, DateTime, CheckConstraint, Integer, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from sqlalchemy import func, text
import enum

Base = declarative_base()

def EnumType(enum_class, **kwargs):
    """Custom Enum column type that uses enum values (not names)."""
    return Enum(
        enum_class,
        name=enum_class.__name__.lower(),  # gives each enum type a nice name in Postgres
        values_callable=lambda obj: [e.value for e in obj],
        **kwargs
    )
    
class PersonRole(enum.Enum):
    victim = "VICTIM"
    suspect = "SUSPECT"
    witness = "WITNESS"
    reportee = "REPORTEE"

class UserRole(enum.Enum):
    admin = "ADMIN"
    io = "INVESTIGATION OFFICER"
    analyst = "ANALYST"
    
class UserStatus(enum.Enum):
    pending = "PENDING"
    active = "ACTIVE"
    inactive = "INACTIVE"
    
class SenderRole(enum.Enum):
    human =  "HUMAN"
    police = "AI"
    
class ReportStatus(enum.Enum):
    unassigned = "UNASSIGNED"
    assigned = "ASSIGNED"
    resolved = "RESOLVED"
      

class ScamReports(Base):
    """
    Data model for scam_reports table in PostgreSQL with pgvector.
    Stores scam generic details. scam_incident_description stored as embeddings for similarity searches. 
    """
    __tablename__ = 'scam_reports'

    report_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    scam_incident_date = Column(Date, nullable=False)
    scam_report_date = Column(Date, nullable=False) #For past reports that have been digitalised or archived. Not necessarily created at the time of data ingestion.
    scam_type = Column(String, nullable=True)
    scam_approach_platform = Column(String, nullable=True)
    scam_communication_platform = Column(String, nullable=True)
    scam_transaction_type = Column(String, nullable=True)
    scam_beneficiary_platform = Column(String, nullable=True)
    scam_beneficiary_identifier = Column(String, nullable=True)
    scam_contact_no = Column(String, nullable=True)
    scam_email = Column(String, nullable=True)
    scam_moniker = Column(String, nullable=True)
    scam_url_link = Column(String, nullable=True)
    scam_amount_lost = Column(Float, nullable=True)
    scam_incident_description = Column(String, nullable=False)
    status = Column(EnumType(ReportStatus), nullable=False, default=ReportStatus.unassigned, server_default=ReportStatus.unassigned.value)
    io_in_charge = Column(Integer, ForeignKey('users.user_id', ondelete="SET NULL"), nullable=True)
    creation_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    embedding = Column(Vector(384))

    io = relationship("Users", back_populates="reports_in_charge")
    pois = relationship("ReportPersonsLink", back_populates="report", cascade="all, delete, delete-orphan")
    conversations = relationship("Conversations", back_populates="report")

class Strategies(Base):
    """
    Data model for strategy table in PostgreSQL with pgvector.
    Stores strategies used to guide profile_rag_ie_kb agent. 
    Knowledgebase Agent in pipeline uses this table for knowledgebase augmentation of interaction/communication strategies.
    """
    __tablename__ = 'strategies'

    strategy_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    strategy_type = Column(String,CheckConstraint('LENGTH(strategy_type) >= 3'), nullable=False)
    response = Column(Text, CheckConstraint('LENGTH(response) >= 5'), nullable=False)
    success_score = Column(Float, nullable=False, )
    user_profile = Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    retrieval_count = Column(Integer, nullable=False, default=0)  # For pruning low-utility strategies
    creation_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # Use server default for timestamp

class PersonDetails(Base):
    """
    Data model for person_details table in PostgreSQL with pgvector.
    Stores information of persons of interest (POIs) including victims, reportees, suspects and witnesses. 
    """
    __tablename__ = 'person_details'
   
    person_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    sex = Column(String, nullable=True)
    dob = Column(Date, nullable=True)
    nationality = Column(String, nullable=True)
    race = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    contact_no = Column(String, nullable=False)
    email = Column(String, nullable=False)
    blk = Column(String, nullable=True)
    street = Column(String, nullable=True)
    unit_no = Column(String, nullable=True)
    postcode = Column(String, nullable=True)
    creation_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now()) #Use server default for timestamp
    last_updated_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now(),onupdate=func.now()) #Use server default for timestamp
   
    # Relationship for reports (many-to-many via association object); cascade delete to remove linked ReportPersonsLink entries when person is deleted
    reports = relationship("ReportPersonsLink", back_populates="person", cascade="all, delete, delete-orphan")

class ReportPersonsLink(Base):
    """
    Data model for report_poi, 
    Stores mapping of report_id to person_id and the person of interests' (POI) associated role (victim, suspect, witness) with the report.
    """
    __tablename__ = 'report_persons_link'
    report_id = Column(Integer, ForeignKey("scam_reports.report_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    person_id = Column(Integer, ForeignKey("person_details.person_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    role = Column(EnumType(PersonRole), nullable=False)
    
    report = relationship("ScamReports", back_populates="pois")
    person = relationship("PersonDetails", back_populates="reports")

class Users(Base):
    """
    Data model for users table in PostgreSQL with pgvector.
    Stores user information of police force staff, including admin, investigation officers and analysts.
    """
    __tablename__ = 'users'
   
    user_id = Column(Integer, primary_key=True, autoincrement=True,nullable=False)
    password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    sex = Column(String, nullable=True)
    dob = Column(Date, nullable=True)
    nationality = Column(String, nullable=True)
    race = Column(String, nullable=True)
    contact_no = Column(String, nullable=False)
    email = Column(String, nullable=False)
    blk = Column(String, nullable=True)
    street = Column(String, nullable=True)
    unit_no = Column(String, nullable=True)
    postcode = Column(String, nullable=True)
    role = Column(EnumType(UserRole), nullable=False)
    status = Column(EnumType(UserStatus), default=UserStatus.pending, nullable=False,server_default=UserStatus.pending.value)
    permission = Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False) 
    registration_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now()) #Use server default for timestamp
    last_updated_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now(),onupdate=func.now()) #Use server default for timestamp

    reports_in_charge = relationship("ScamReports", back_populates="io")

class Conversations(Base):
    """
    Data model for conversations table in PostgreSQL.
    Stores conversations between police AI conversational agent and general users (reportees, victims, etc.).
    """
    __tablename__ = 'conversations'
   
    conversation_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    report_id = Column(Integer, ForeignKey("scam_reports.report_id", ondelete="SET NULL"), nullable=True)
    creation_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
   
    # Relationship for report (many-to-one)
    report = relationship("ScamReports", back_populates="conversations")
    # Relationship for messages (one-to-many); cascade delete to remove all linked messages when conversation is deleted
    messages = relationship("Messages", back_populates="conversation", cascade="all, delete, delete-orphan")
   
class Messages(Base):
    """
    Data model for messages table in PostgreSQL.
    Stores messages exchanged in conversations between police AI conversational agent and general users (reportees, victims, etc.).
    Each message is associated with a conversation and has a sender role (victim or police).
    """
    __tablename__ = 'messages'
    
    message_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    sender_role = Column(EnumType(SenderRole), nullable=False)
    content = Column(Text, nullable=False)
    sent_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    conversation = relationship("Conversations", back_populates="messages")
    
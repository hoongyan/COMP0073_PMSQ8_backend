import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Annotated
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies.db import db_dependency  
from app.dependencies.auth import get_current_active_user 
from app.dependencies.roles import admin_role 
from src.database.database_operations import CRUDOperations
from src.models.data_model import Conversations, Messages, Users
from app.model import ConversationListResponse


conversation_router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],  
)

@conversation_router.get("/", response_model=ConversationListResponse)  
def get_conversations_endpoint(
    db: db_dependency,
    current_user: Users = Depends(admin_role),  
    limit: int = 100, 
    offset: int = 0
):
    """
    Retrieve a paginated list of conversations with associated messages.
    - Messages are sorted by message_id ASC (insertion order).
    - Dates are formatted as 'dd/MM/yy HH:mm' to match frontend.
    - Sender roles are used directly as "HUMAN" or "AI" (uppercase to match DB enum).
    - Summary is generated from the first message (truncated to 100 chars + "...") or "No messages" if empty.
    Admin-only access.
    """
    try:
        conversations = db.query(Conversations).options(
            joinedload(Conversations.messages)
        ).order_by(Conversations.conversation_id.asc()).offset(offset).limit(limit).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during read: {str(e)}")
    
    if not conversations:
        return ConversationListResponse(conversations=[])
        
    enriched_conversations = []
    for conv in conversations:
        # Sort messages by message_id ASC 
        sorted_messages = sorted(conv.messages, key=lambda m: m.message_id)
            
        formatted_messages = []
        for msg in sorted_messages:
            formatted_role = msg.sender_role.value  
                
            formatted_messages.append({
                "messageId": str(msg.message_id),
                "conversationId": str(conv.conversation_id),
                "senderRole": formatted_role,
                "content": msg.content,
                "sentDate": msg.sent_datetime.strftime("%d/%m/%y %H:%M")
            })
            
        # Generate summary by truncating first message content or default
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

@conversation_router.delete("/{conversation_id}", status_code=204)
def delete_conversation_endpoint(
    conversation_id: int, 
    db: db_dependency,
    current_user: Users = Depends(admin_role)  # Role-based Access Control (RBAC): Admin-only
):
    """
    Delete a conversation by ID. Associated messages are automatically deleted via database cascade.
    Admin-only access.
    """
    conv_crud = CRUDOperations(Conversations)
    try:
        deleted = conv_crud.delete(db, conversation_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Conversation with ID {conversation_id} not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error during delete: {str(e)}")
    return None
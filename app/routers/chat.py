from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Body
from typing import Optional, Dict
from src.agents.conversation_manager_new import ConversationManager

chat_router = APIRouter(prefix="/chat")


managers: Dict[int, ConversationManager] = {}

@chat_router.post("/message")
async def send_message(query: str = Body(...), conversation_id: Optional[int] = Body(None)):
    """
    Public endpoint for conversations.
    Creates or continues conversations with AI assistant.
    Accessible by public users.
    """
    try:
        if conversation_id is None:
            manager = ConversationManager()
            # ID will be created in conversation Manager
            result = manager.process_user_query(query, None)
            # Get the new ID from the result
            new_id = result["conversation_id"]
            # Store in the dict
            managers[new_id] = manager
            return result
        else:
            # Existing conversation: Create if not in dict 
            if conversation_id not in managers:
                managers[conversation_id] = ConversationManager()
            # Get the manager
            manager = managers[conversation_id]
            # Process
            result = manager.process_user_query(query, conversation_id)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@chat_router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: int):
    """
    Public endpoint for conversations.
    Websocket endpoint for real-time chat.
    """
    await websocket.accept()
    try:
        # Existing conversation: Create manager if not in dict
        if conversation_id not in managers:
            managers[conversation_id] = ConversationManager()
        # Get the manager
        manager = managers[conversation_id]
        
        while True:
            data = await websocket.receive_text()  # User message
            result = manager.process_user_query(data, conversation_id)
            await websocket.send_text(result["response"])  # AI response
    except WebSocketDisconnect:
        pass  
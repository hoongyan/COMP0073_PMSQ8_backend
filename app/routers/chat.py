from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Body
from typing import Optional
from src.agents.conversation_manager_new import ConversationManager

chat_router = APIRouter(prefix="/chat")

manager = ConversationManager()

@chat_router.post("/message")
async def send_message(query: str = Body(...), conversation_id: Optional[int] = Body(None)):
    try:
        result = manager.process_user_query(query, conversation_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@chat_router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: int):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            result = manager.process_user_query(data, conversation_id)
            await websocket.send_text(result["response"])
    except WebSocketDisconnect:
        pass
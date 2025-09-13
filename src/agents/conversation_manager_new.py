# import sys
# import os
# from datetime import datetime
# import json
# from enum import Enum
# from typing import List, Dict, Optional, Union

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
# from config.settings import get_settings
# from config.logging_config import setup_logger
# from src.agents.police.profile_rag_ie_kb_agent import ProfileRAGIEKBAgent  # Focus on this agent
# from src.database.database_operations import DatabaseManager, CRUDOperations
# from src.models.data_model import Conversations, Messages, SenderRole

# class ConversationMode(Enum):
#     AUTONOMOUS = "autonomous"
#     NONAUTONOMOUS = "nonautonomous"

# class ConversationType(Enum):
#     IE = "ie"
#     RAG_IE = "rag_ie"
#     PROFILE_RAG_IE = "profile_rag_ie"
#     PROFILE_RAG_IE_KB = "profile_rag_ie_kb" 

# class ConversationManager:
#     """
#     Manages conversations in non-autonomous mode (human-police AI).
#     Handles DB storage for conversations and messages, agent invocation, and error resilience.
#     Autonomous/simulation code removed as not needed.
#     """
#     def __init__(
#         self,
#         mode: ConversationMode,
#         conversation_type: ConversationType = ConversationType.PROFILE_RAG_IE_KB,
#         police_model_name: str = "qwen2.5:7b",
#         police_llm_provider: str = "Ollama",
#         max_turns: int = 10,  # Kept but unused in non-auto
#         json_file: str = "data/victim_profile/victim_details.json"  # Kept but unused
#     ):
#         """
#         Initialize the manager for non-autonomous mode with DB integration.
#         """
#         self.settings = get_settings()
#         self.logger = setup_logger("ConversationManager", self.settings.log.subdirectories["agent"])
#         self.conversation_type = conversation_type
#         self.mode = mode

#         # Police agent config
#         self.police_model_name = police_model_name
#         self.police_llm_provider = police_llm_provider
#         self.max_turns = max_turns
#         self.json_file = json_file
#         self.conversation_id: Optional[int] = None
#         self.conversation_history: List[Dict] = []  # In-memory cache, refreshed from DB
#         self.turn_count: int = 0
#         self.police_chatbot: Optional[ProfileRAGIEKBAgent] = None

#         # DB setup (new)
#         self.db_manager = DatabaseManager()
#         self.conversation_crud = CRUDOperations(Conversations, self.db_manager.session_factory)
#         self.message_crud = CRUDOperations(Messages, self.db_manager.session_factory)

#         # Removed all CSV/IDManager code to avoid multi-user issues

#     def _create_or_load_conversation(self, db: Session, conversation_id: Optional[int] = None) -> int:
#         """Create a new conversation or load existing one. Returns ID."""
#         if conversation_id:
#             conv = self.conversation_crud.read(db, conversation_id)
#             if not conv:
#                 raise ValueError(f"Conversation {conversation_id} not found")
#             self.conversation_id = conv.conversation_id
#         else:
#             # Create new (report_id can be set later if needed)
#             new_conv_data = {"report_id": None}  # Empty; timestamps auto-set by DB
#             new_conv = self.conversation_crud.create(db, new_conv_data)
#             if not new_conv:
#                 raise ValueError("Failed to create conversation")
#             self.conversation_id = new_conv.conversation_id
#         return self.conversation_id

#     def _load_history_from_db(self, db: Session) -> List[Dict]:
#         """Load messages for this conversation, sorted by sent_datetime ASC."""
#         messages = db.query(Messages).filter(Messages.conversation_id == self.conversation_id).order_by(Messages.sent_datetime.asc()).all()
#         self.conversation_history = [
#             {"role": msg.sender_role.value.lower(), "content": msg.content} for msg in messages
#         ]  # Lowercase role for agent compatibility (e.g., 'human', 'ai')
#         return self.conversation_history

#     def _save_message(self, db: Session, role: SenderRole, content: str):
#         """Save a message to DB."""
#         data = {
#             "conversation_id": self.conversation_id,
#             "sender_role": role,
#             "content": content,
#             # sent_datetime auto-set by DB
#         }
#         saved_msg = self.message_crud.create(db, data)
#         if not saved_msg:
#             raise ValueError("Failed to save message")
#         self.logger.info(f"Saved message for conv {self.conversation_id}: {role.value}")

#     def process_user_query(self, query: str, conversation_id: Optional[int] = None) -> Dict:
#         """Process a user query in non-autonomous mode, save to DB, return AI response."""
#         if self.mode != ConversationMode.NONAUTONOMOUS:
#             raise ValueError("Only for non-autonomous mode")
        
#         if self.conversation_type != ConversationType.PROFILE_RAG_IE_KB:
#             raise ValueError("Only for PROFILE_RAG_IE_KB")

#         # Use a new session for each invocation (thread-safe for multi-user)
#         with self.db_manager.session_factory() as db:
#             db.begin()  # Start transaction
#             try:
#                 self._create_or_load_conversation(db, conversation_id)
#                 self._load_history_from_db(db)  # Refresh history from DB

#                 # Save user message
#                 self._save_message(db, SenderRole.human, query)

#                 # Initialize agent if not already (singleton per manager instance)
#                 if not self.police_chatbot:
#                     self.police_chatbot = ProfileRAGIEKBAgent(
#                         model_name=self.police_model_name,
#                         llm_provider=self.police_llm_provider,
#                         rag_csv_path=None  # Disable CSV logging to avoid issues
#                     )

#                 # Build history for agent (assuming agent uses langchain messages)
#                 agent_history = []
#                 for msg in self.conversation_history:
#                     if msg["role"] == "human":
#                         agent_history.append(HumanMessage(content=msg["content"]))
#                     elif msg["role"] == "ai":  # Adjust if your agent uses 'police' or AIMessage
#                         agent_history.append(AIMessage(content=msg["content"]))

#                 # Invoke agent (adapt to your agent's method; assuming it takes query + history + conv_id)
#                 response = self.police_chatbot.process_query(
#                     query=query,
#                     messages=agent_history,  # Pass loaded history
#                     conversation_id=self.conversation_id
#                 )

#                 ai_response = response.get("response", "I'm sorry, there was an error processing your request.")

#                 # Save AI message
#                 self._save_message(db, SenderRole.police, ai_response)

#                 # Update in-memory history (optional, for caching)
#                 self.conversation_history.append({"role": "human", "content": query})
#                 self.conversation_history.append({"role": "ai", "content": ai_response})  # Use 'ai' for consistency

#                 db.commit()  # Commit transaction
#                 return {
#                     "response": ai_response,
#                     "conversation_id": self.conversation_id,
#                     "structured_data": response.get("structured_data", {})  # If your agent returns extra data
#                 }
#             except Exception as e:
#                 db.rollback()  # Rollback on error
#                 self.logger.error(f"Error processing query for conv {self.conversation_id}: {str(e)}")
#                 raise ValueError(f"Error: {str(e)}")

#     def reset_state(self):
#         """Reset in-memory state (DB persists)."""
#         self.conversation_id = None
#         self.conversation_history = []
#         self.turn_count = 0
#         if self.police_chatbot:
#             self.police_chatbot.reset_state()
#         self.logger.debug("ConversationManager state reset")

#     def end_conversation(self, conversation_id: int):
#         """End and optionally clean up (e.g., reset agent). No delete—persist in DB."""
#         self.reset_state()
#         self.logger.info(f"Conversation {conversation_id} ended")
#         return {"status": "Conversation ended"}

import sys
import os
from datetime import datetime
import json
from typing import List, Dict, Optional, Union
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config.settings import get_settings
from config.logging_config import setup_logger
from src.agents.profile_rag_ie_kb_agent import ProfileRAGIEKBAgent
from src.database.database_operations import DatabaseManager, CRUDOperations
from src.models.data_model import Conversations, Messages, SenderRole

class ConversationManager:
    """
    Manages conversations for human-police AI interactions.
    Handles DB storage for conversations and messages, agent invocation, and error resilience.
    Hardcoded for ProfileRAGIEKBAgent, no modes/types.
    """
    def __init__(
        self,
        police_model_name: str = "granite3.2:8b",
        police_llm_provider: str = "Ollama",
        max_turns: int = 10,  # Kept but unused
        json_file: str = "data/victim_profile/victim_details.json"  # Kept but unused
    ):
        """
        Initialize the manager with hardcoded agent.
        """
        self.settings = get_settings()
        self.logger = setup_logger("ConversationManager", self.settings.log.subdirectories["agent"])
        self.logger.info("ConversationManager activated and initialized")

        # Police agent config
        self.police_model_name = police_model_name
        self.police_llm_provider = police_llm_provider
        self.max_turns = max_turns
        self.json_file = json_file
        self.conversation_id: Optional[int] = None
        self.conversation_history: List[Dict] = []
        self.turn_count: int = 0
        self.police_chatbot: Optional[ProfileRAGIEKBAgent] = None

        # DB setup (fixed: no session_factory in CRUDOperations)
        self.db_manager = DatabaseManager()
        self.conversation_crud = CRUDOperations(Conversations)  # Only model
        self.message_crud = CRUDOperations(Messages)  # Only model
        self.logger.info("Database CRUD operations initialized")

    def _create_or_load_conversation(self, db: Session, conversation_id: Optional[int] = None) -> int:
        """Create a new conversation or load existing one. Returns ID."""
        if conversation_id:
            conv = self.conversation_crud.read(db, conversation_id)
            if not conv:
                raise ValueError(f"Conversation {conversation_id} not found")
            self.conversation_id = conv.conversation_id
            self.logger.info(f"Loaded existing conversation ID: {self.conversation_id}")
        else:
            new_conv_data = {"report_id": None}
            new_conv = self.conversation_crud.create(db, new_conv_data)
            if not new_conv:
                raise ValueError("Failed to create conversation")
            self.conversation_id = new_conv.conversation_id
            self.logger.info(f"Created new conversation ID: {self.conversation_id}")
        return self.conversation_id

    def _load_history_from_db(self, db: Session) -> List[Dict]:
        """Load messages for this conversation, sorted by sent_datetime ASC."""
        messages = db.query(Messages).filter(Messages.conversation_id == self.conversation_id).order_by(Messages.sent_datetime.asc()).all()
        self.conversation_history = [
            {"role": msg.sender_role.value.lower(), "content": msg.content} for msg in messages
        ]
        self.logger.info(f"Loaded {len(self.conversation_history)} messages from DB for conv {self.conversation_id}")
        return self.conversation_history

    def _save_message(self, db: Session, role: SenderRole, content: str):
        """Save a message to DB."""
        data = {
            "conversation_id": self.conversation_id,
            "sender_role": role,
            "content": content,
        }
        saved_msg = self.message_crud.create(db, data)
        if not saved_msg:
            raise ValueError("Failed to save message")
        self.logger.info(f"Saved {role.value} message for conv {self.conversation_id}: {content[:50]}...")

    def process_user_query(self, query: str, conversation_id: Optional[int] = None) -> Dict:
        """Process a user query, save to DB, return AI response."""
        self.logger.info(f"Processing user query for conv {conversation_id}: {query[:50]}...")

        with self.db_manager.session_factory() as db:
            db.begin()
            try:
                self._create_or_load_conversation(db, conversation_id)
                self._load_history_from_db(db)

                self._save_message(db, SenderRole.human, query)

                if not self.police_chatbot:
                    self.police_chatbot = ProfileRAGIEKBAgent(
                        model_name=self.police_model_name,
                        llm_provider=self.police_llm_provider,
                        rag_csv_path=None
                    )
                    self.logger.info("ProfileRAGIEKBAgent initialized")

                agent_history = []
                for msg in self.conversation_history:
                    if msg["role"] == "human":
                        agent_history.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "ai":
                        agent_history.append(AIMessage(content=msg["content"]))

                response = self.police_chatbot.process_query(
                    query=query,
                    messages=agent_history,
                    conversation_id=self.conversation_id
                )

                ai_response = response.get("response", "I'm sorry, there was an error processing your request.")
                structured_data = response.get("structured_data", {})  # Safely get the structured_data dict from the agent's response
                self.logger.info(f"AI response generated: {ai_response[:50]}...")

                self._save_message(db, SenderRole.police, ai_response)

                self.conversation_history.append({"role": "human", "content": query})
                self.conversation_history.append({"role": "ai", "content": ai_response})

                db.commit()
                self.logger.info(f"Query processed successfully for conv {self.conversation_id}")
                return {
                    "response": ai_response,  
                    "conversation_id": self.conversation_id,
                    "structured_data": {
                        "scam_incident_date": structured_data.get("scam_incident_date", ""),
                        "scam_type": structured_data.get("scam_type", ""),
                        "scam_approach_platform": structured_data.get("scam_approach_platform", ""),
                        "scam_communication_platform": structured_data.get("scam_communication_platform", ""),
                        "scam_transaction_type": structured_data.get("scam_transaction_type", ""),
                        "scam_beneficiary_platform": structured_data.get("scam_beneficiary_platform", ""),
                        "scam_beneficiary_identifier": structured_data.get("scam_beneficiary_identifier", ""),
                        "scam_contact_no": structured_data.get("scam_contact_no", ""),
                        "scam_email": structured_data.get("scam_email", ""),
                        "scam_moniker": structured_data.get("scam_moniker", ""),
                        "scam_url_link": structured_data.get("scam_url_link", ""),
                        "scam_amount_lost": structured_data.get("scam_amount_lost", 0),
                        "scam_incident_description": structured_data.get("scam_incident_description", "")
                    }
                }
            except Exception as e:
                db.rollback()
                self.logger.error(f"Error processing query for conv {self.conversation_id}: {str(e)}")
                raise ValueError(f"Error: {str(e)}")

    def reset_state(self):
        """Reset in-memory state (DB persists)."""
        self.conversation_id = None
        self.conversation_history = []
        self.turn_count = 0
        if self.police_chatbot:
            self.police_chatbot.reset_state()
        self.logger.info("ConversationManager state reset")

    def end_conversation(self, conversation_id: int):
        """End and optionally clean up. No delete—persist in DB."""
        self.reset_state()
        self.logger.info(f"Conversation {conversation_id} ended")
        return {"status": "Conversation ended"}
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.conversation_manager_new import ConversationManager


manager = ConversationManager()
response = manager.process_user_query("I received a suspicious SMS from DBS asking me to click a link.")
print(response)
response = manager.process_user_query("It happened on 2025-01-01.", conversation_id=response["conversation_id"])
print(response)
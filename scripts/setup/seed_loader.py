import sys
import os
from datetime import date
from pathlib import Path
import pandas as pd
from sqlalchemy import text
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.dependencies.auth import get_password_hash
from src.database.database_operations import DatabaseManager, CRUDOperations
from src.models.data_model import Users, ReportPersonsLink, Conversations, Messages, UserRole, UserStatus, PersonRole, SenderRole, ReportStatus
from config.settings import get_settings
from config.logging_config import setup_logger

class SeedLoader:
    """Manages loading seed data for users, report_persons_link, conversations, and messages into the database."""
    
    def __init__(self):
        """Initialize components and setup logging."""
        self.settings = get_settings()
        self.logger = setup_logger("SeedLoader", self.settings.log.subdirectories["database"])
        self.db_manager = DatabaseManager()
        self.user_crud = CRUDOperations(Users)
        self.link_crud = CRUDOperations(ReportPersonsLink)
        self.conv_crud = CRUDOperations(Conversations)
        self.msg_crud = CRUDOperations(Messages)
    
    def load_seed_data(self, reset_sequences: bool = False):
        """Load seed data into the database. Assumes reports (1-400) and persons (1-400) already exist."""
        try:
            with self.db_manager.session_factory() as db:
                
                if reset_sequences:
                    try:
                        db.execute(text("ALTER SEQUENCE users_user_id_seq RESTART WITH 1;"))
                        db.execute(text("ALTER SEQUENCE conversations_conversation_id_seq RESTART WITH 1;"))
                        db.execute(text("ALTER SEQUENCE messages_message_id_seq RESTART WITH 1;"))
                        db.commit()
                        self.logger.info("Reset sequences for users, conversations, and messages")
                        print("Reset sequences for users, conversations, and messages")
                    except Exception as e:
                        db.rollback()
                        self.logger.error(f"Failed to reset sequences: {str(e)}")
                        print(f"Failed to reset sequences: {str(e)}")
                        raise

                # Clear existing data
                deleted_users = self.user_crud.delete_all(db)
                print(f"Deleted {deleted_users} existing users")
                deleted_links = self.link_crud.delete_all(db)
                print(f"Deleted {deleted_links} existing report_persons_links")
                deleted_convs = self.conv_crud.delete_all(db)  
                print(f"Deleted {deleted_convs} existing conversations (and associated messages)")

                # Seed Users 
                users_data = [
                    {
                        'password': get_password_hash('password123'), 
                        'first_name': 'JOHN',
                        'last_name': 'DOE',
                        'sex': 'MALE',
                        'dob': date(1985, 5, 15),
                        'nationality': 'SINGAPOREAN',
                        'race': 'CHINESE',
                        'contact_no': '6512345678',
                        'email': 'john.doe@police.gov.sg',
                        'blk': '123',
                        'street': 'ORCHARD ROAD',
                        'unit_no': '#05-67',
                        'postcode': '238878',
                        'role': UserRole.admin.value,  # 'ADMIN'
                        'status': UserStatus.active.value,  # 'ACTIVE'
                    },
                    {
                        'password': get_password_hash('securepass456'),
                        'first_name': 'JANE',
                        'last_name': 'SMITH',
                        'sex': 'FEMALE',
                        'dob': date(1990, 8, 22),
                        'nationality': 'SINGAPOREAN',
                        'race': 'MALAY',
                        'contact_no': '6598765432',
                        'email': 'jane.smith@police.gov.sg',
                        'blk': '456',
                        'street': 'BUKIT TIMAH ROAD',
                        'unit_no': '#12-34',
                        'postcode': '259768',
                        'role': UserRole.io.value,  # 'INVESTIGATION OFFICER'
                        'status': UserStatus.active.value,  # 'ACTIVE'
                    },
                    {
                        'password': get_password_hash('analystpass789'),
                        'first_name': 'BOB',
                        'last_name': 'JOHNSON',
                        'sex': 'MALE',
                        'dob': date(1982, 3, 10),
                        'nationality': 'SINGAPOREAN',
                        'race': 'INDIAN',
                        'contact_no': '6511122233',
                        'email': 'bob.johnson@police.gov.sg',
                        'blk': '789',
                        'street': 'JURONG EAST STREET',
                        'unit_no': '#08-90',
                        'postcode': '600789',
                        'role': UserRole.analyst.value,  # 'ANALYST'
                        'status': UserStatus.pending.value,  # 'PENDING'
                    }
                ]
                users_df = pd.DataFrame(users_data)
                inserted_users = self.user_crud.create_bulk(db, users_df)
                self.logger.info(f"Inserted {inserted_users} users")
                print(f"Inserted {inserted_users} users")
                
                # Verify sample user
                if inserted_users > 0:
                    users = self.user_crud.read_all(db, limit=1)
                    if users:
                        print(f"Verified sample user: {users[0].first_name} ({users[0].role})")

                # Seed ReportPersonsLink
                links = []
                roles = [PersonRole.victim.value, PersonRole.suspect.value, PersonRole.witness.value] 
                for i in range(1, 401):
                    role = roles[(i - 1) % 3]
                    links.append({'report_id': i, 'person_id': i, 'role': role})
                links_df = pd.DataFrame(links)
                inserted_links = self.link_crud.create_bulk(db, links_df)
                self.logger.info(f"Inserted {inserted_links} report_persons_links")
                print(f"Inserted {inserted_links} report_persons_links")
                
                # Verify sample link
                if inserted_links > 0:
                    sample_link = self.link_crud.read_all(db, limit=1)
                    if sample_link:
                        print(f"Verified sample link: report_id={sample_link[0].report_id}, person_id={sample_link[0].person_id}, role={sample_link[0].role}")

                # Seed Conversations 
                convs_data = [
                    {'report_id': 10},
                    {'report_id': 11},
                    {'report_id': 12}
                ]
                conv_ids = []
                for conv_data in convs_data:
                    created_conv = self.conv_crud.create(db, conv_data)
                    if created_conv:
                        conv_ids.append(created_conv.conversation_id)
                    else:
                        self.logger.warning("Failed to create a conversation")
                self.logger.info(f"Created {len(conv_ids)} conversations: {conv_ids}")
                print(f"Created {len(conv_ids)} conversations: {conv_ids}")

                # Seed Messages 
                for conv_id in conv_ids:
                    messages_data = [
                        {'conversation_id': conv_id, 'sender_role': SenderRole.human.value, 'content': 'Hello, I was scammed and need to report it.'},  # 'HUMAN'
                        {'conversation_id': conv_id, 'sender_role': SenderRole.police.value, 'content': 'I\'m sorry to hear that. Can you provide more details?'},  # 'AI'
                        {'conversation_id': conv_id, 'sender_role': SenderRole.human.value, 'content': 'Yes, it happened on WhatsApp.'}  # 'HUMAN'
                    ]
                    messages_df = pd.DataFrame(messages_data)
                    inserted_msgs = self.msg_crud.create_bulk(db, messages_df)
                    self.logger.info(f"Inserted {inserted_msgs} messages for conversation {conv_id}")
                    print(f"Inserted {inserted_msgs} messages for conversation {conv_id}")
                    
                # Verify sample message
                if conv_ids:
                    sample_msgs = self.msg_crud.read_all(db, limit=1)
                    if sample_msgs:
                        print(f"Verified sample message: conversation_id={sample_msgs[0].conversation_id}, sender={sample_msgs[0].sender_role}")

        except Exception as e:
            self.logger.error(f"Error in seed data loading: {str(e)}")
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Load seed data for users, links, conversations, and messages.")
    parser.add_argument("--reset-sequences", action="store_true", help="Reset ID sequences before loading data")
    args = parser.parse_args()
    loader = SeedLoader()
    loader.load_seed_data(reset_sequences=args.reset_sequences)
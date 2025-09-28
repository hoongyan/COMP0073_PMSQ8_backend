import argparse
import sys
import os
from pathlib import Path
import json
import pandas as pd 
from sqlalchemy import text
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))
from src.database.database_operations import DatabaseManager, CRUDOperations, StrategiesCRUD
from src.database.vector_operations import VectorStore
from src.preprocessing.preprocess import ScamReportPreprocessor, PersonPreprocessor
from src.models.data_model import ScamReports, Strategies, PersonDetails
from config.settings import get_settings
from config.logging_config import setup_logger
from scripts.setup.init_db import DatabaseInitializer

class DataLoader:
    """Manages data loading and storage into the database."""
    
    def __init__(self):
        """Initialize components and setup logging."""
        self.settings = get_settings()
        self.logger = setup_logger("DataLoader", self.settings.log.subdirectories["database"])
        self.db_manager = DatabaseManager()
        self.strategy_crud = StrategiesCRUD()  
        self.crud = CRUDOperations(ScamReports) 
        self.person_crud = CRUDOperations(PersonDetails)  
        self.vector_store = VectorStore(self.db_manager.session_factory)  
        self.preprocessor = ScamReportPreprocessor(self.vector_store)
    
    def load_and_store_data(self, initialize_schema: bool = False):
        """Clear existing data and load new scam reports into the database."""
        try:
            # Initialize database schema if requested (through flag)
            if initialize_schema:
                initializer = DatabaseInitializer()
                initializer.initialize_database()
            
            with self.db_manager.session_factory() as db:
                
                deleted_count = self.crud.delete_all(db)
                self.logger.info(f"Deleted {deleted_count} existing records")
                print(f"Deleted {deleted_count} existing records")
                
                try:
                    db.execute(text("ALTER SEQUENCE scam_reports_report_id_seq RESTART WITH 1;"))
                    db.commit() 
                    self.logger.info("Reset scam report ID sequence to start from 1")
                    print("Reset scam report ID sequence to start from 1")
                except Exception as e:
                    db.rollback()  
                    self.logger.error(f"Failed to reset scam report ID sequence: {str(e)}")
                    print(f"Failed to reset scam report ID sequence: {str(e)}")
                    raise  
                
                # Preprocess data
                processed_df = self.preprocessor.preprocess()
                
                expected_columns = [
                    "scam_incident_date", "scam_report_date", "scam_type",
                    "scam_approach_platform", "scam_communication_platform", "scam_transaction_type",
                    "scam_beneficiary_platform", "scam_beneficiary_identifier", "scam_contact_no",
                    "scam_email", "scam_moniker", "scam_url_link", "scam_amount_lost",
                    "scam_incident_description", "embedding"
                ]
                if not all(col in processed_df.columns for col in expected_columns):
                    missing = [col for col in expected_columns if col not in processed_df.columns]
                    self.logger.error(f"Missing columns in DataFrame: {missing}")
                    raise ValueError(f"Missing columns in DataFrame: {missing}")
                
                # Insert data
                inserted_count = self.crud.create_bulk(db, processed_df)
                self.logger.info(f"Inserted {inserted_count} new records")
                print(f"Inserted {inserted_count} new records")
                
                # Verify sample record
                if not processed_df.empty:

                    records = self.crud.read_all(db, limit=1)
                    if records:
                        sample_record = records[0]
                        self.logger.info(f"Verified sample record with scam_type: {sample_record.scam_type}")
                        print(f"Verified sample record with scam_type: {sample_record.scam_type}")
                    else:
                        self.logger.warning(f"Sample record not found")
                        print(f"Sample record not found")
                        
                # Load strategies from seed file
                self.logger.info("Loading strategies from seed file...")
                
                # Clear existing strategies
                deleted_strategy_count = self.strategy_crud.delete_all(db)
                self.logger.info(f"Deleted {deleted_strategy_count} existing strategies")
                print(f"Deleted {deleted_strategy_count} existing strategies")
                
                # Reset the ID sequence to start from 1 
                try:
                    db.execute(text("ALTER SEQUENCE strategies_strategy_id_seq RESTART WITH 1;"))
                    db.commit() 
                    self.logger.info("Reset strategy ID sequence to start from 1")
                    print("Reset strategy ID sequence to start from 1")
                except Exception as e:
                    db.rollback() 
                    self.logger.error(f"Failed to reset strategy ID sequence: {str(e)}")
                    print(f"Failed to reset strategy ID sequence: {str(e)}")
                    raise  

                # Load seed JSON 
                seed_path = Path(self.settings.data.strategy_seed_json)
                if not seed_path.exists():
                    self.logger.error(f"Seed file not found: {seed_path}")
                    raise FileNotFoundError(f"Seed file not found: {seed_path}")
                
                with open(seed_path, 'r') as f:
                    strategies = json.load(f)
                
                # Convert to DataFrame for bulk insert 
                strategies_df = pd.DataFrame(strategies)
                
                # Validate DataFrame columns for strategies 
                expected_strategy_columns = [
                    "strategy_type", "response", "success_score", "user_profile",
                ]
                
                if not all(col in strategies_df.columns for col in expected_strategy_columns):
                    missing = [col for col in expected_strategy_columns if col not in strategies_df.columns]
                    self.logger.error(f"Missing columns in strategies DataFrame: {missing}")
                    raise ValueError(f"Missing columns in strategies DataFrame: {missing}")
                
                # Insert strategies
                inserted_strategy_count = self.strategy_crud.create_bulk(db, strategies_df)
                self.logger.info(f"Inserted {inserted_strategy_count} new strategies")
                print(f"Inserted {inserted_strategy_count} new strategies")
                
                # Verify sample strategy
                if not strategies_df.empty:
                    read_strategies = self.strategy_crud.read_all(db, limit=1)
                    if read_strategies:
                        self.logger.info(f"Verified sample strategy with type: {read_strategies[0].strategy_type}")
                        print(f"Verified sample strategy with type: {read_strategies[0].strategy_type}")
                    else:
                        self.logger.warning("No strategies found after insertion")
                        print("No strategies found after insertion")
                
                # Load persons 
                person_preprocessor = PersonPreprocessor()
                person_df = person_preprocessor.preprocess()
                
                # Clear existing persons
                deleted_person_count = self.person_crud.delete_all(db)
                self.logger.info(f"Deleted {deleted_person_count} existing person records")
                print(f"Deleted {deleted_person_count} existing person records")
                
                # Reset the ID sequence to start from 1 
                try:
                    db.execute(text("ALTER SEQUENCE person_details_person_id_seq RESTART WITH 1;"))
                    db.commit()  # Commit the reset.
                    self.logger.info("Reset person details ID sequence to start from 1")
                    print("Reset person details ID sequence to start from 1")
                except Exception as e:
                    db.rollback()  
                    self.logger.error(f"Failed to reset person details ID sequence: {str(e)}")
                    print(f"Failed to reset person details ID sequence: {str(e)}")
                    raise  
                
                # Insert persons
                inserted_person_count = self.person_crud.create_bulk(db, person_df)
                self.logger.info(f"Inserted {inserted_person_count} new person records")
                print(f"Inserted {inserted_person_count} new person records")
                
                # Verify sample person
                if not person_df.empty:
                    read_persons = self.person_crud.read_all(db, limit=1)
                    if read_persons:
                        sample_person = read_persons[0]
                        self.logger.info(f"Verified sample person record with first_name: {sample_person.first_name}")
                        print(f"Verified sample person record with first_name: {sample_person.first_name}")
                    else:
                        self.logger.warning("No person records found after insertion")
                        print("No person records found after insertion")
            
        except Exception as e:
            self.logger.error(f"Error in data loading: {str(e)}")
            print(f"Error: {str(e)}")
            raise
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load scam report data into the database.")
    parser.add_argument("--initialize-schema", action="store_true", help="Initialize database schema before loading data")
    args = parser.parse_args()
    loader = DataLoader()
    loader.load_and_store_data(initialize_schema=args.initialize_schema)
    
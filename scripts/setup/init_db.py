import sys
import os
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.database.database_operations import DatabaseManager
from config.settings import get_settings
from config.logging_config import setup_logger


class DatabaseInitializer:
    """Initializes the database schema, pgvector extension, and HNSW index."""
    
    def __init__(self):
        """Initialize components and setup logging."""
        self.settings = get_settings()
        self.logger = setup_logger("DatabaseInitializer", self.settings.log.subdirectories["database"])
        self.db_manager = DatabaseManager()
    
    
    def initialize_database(self, skip_index: bool=False):
        """Initialize the database schema, pgvector extension, and HNSW index."""
        try:
            # Test database connection
            if not self.db_manager.test_connection():
                self.logger.error("Database connection failed")
                raise RuntimeError("Database connection failed")
            
            # Enable pgvector extension
            if not self.db_manager.enable_pgvector():
                self.logger.error("Failed to enable pgvector extension")
                raise RuntimeError("Failed to enable pgvector extension")
            
            if not skip_index:  # NEW: Only create index if not skipping
                # Create HNSW index for scam_report and strategy table
                if not self.db_manager.create_hnsw_index("scam_reports", column_name="embedding"):
                    self.logger.error("Failed to create HNSW index")
                    raise RuntimeError("Failed to create HNSW index")
            
            # # Create HNSW index for scam_report and strategy table
            # if not self.db_manager.create_hnsw_index("scam_reports", column_name="embedding"):
            #     self.logger.error("Failed to create HNSW index")
            #     raise RuntimeError("Failed to create HNSW index")
            
            self.logger.info("Database extensions and indexes initialized successfully")
            print("Database extensions and indexes initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    # NEW: Add argument parser for --skip-index
    parser = argparse.ArgumentParser(description="Initialize the database extensions and indexes.")
    parser.add_argument("--skip-index", action="store_true", help="Skip creating the HNSW index")
    args = parser.parse_args()
    
    initializer = DatabaseInitializer()
    # initializer.initialize_database()
    initializer.initialize_database(skip_index=args.skip_index)
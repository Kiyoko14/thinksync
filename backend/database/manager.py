import supabase
from config import supabase as client
import os

class DatabaseManager:
    def __init__(self):
        self.access_token = os.getenv("SUPABASE_ACCESS_TOKEN")
        self.org_id = os.getenv("SUPABASE_ORG_ID")
    
    async def create_supabase_project(self, name: str) -> dict:
        # Implementation as in database.py router
        pass
    
    async def generate_credentials(self, project_id: str) -> dict:
        # Get credentials
        pass

database_manager = DatabaseManager()
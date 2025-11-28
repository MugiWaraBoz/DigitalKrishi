import os
from supabase import create_client, Client
from flask import current_app

class SupabaseDB:
    def __init__(self):
        self.url = None
        self.key = None
        self.client: Client = None
        # Don't connect immediately
    
    def connect(self):
        """Initialize Supabase client when needed"""
        if self.client is not None:
            return self.client
            
        try:
            self.url = os.getenv('SUPABASE_URL')
            self.key = os.getenv('SUPABASE_KEY')
            
            # Validate URL format
            if not self.url or not self.url.startswith('https://'):
                raise ValueError("SUPABASE_URL must start with https://")
            
            if not self.key:
                raise ValueError("SUPABASE_KEY is missing")
            
            self.client = create_client(self.url, self.key)
            print(f"✅ Supabase connected to: {self.url}")
            return self.client
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            print(f"URL: {self.url}")
            print(f"Key present: {bool(self.key)}")
            self.client = None
            return None

# Global instance
db = SupabaseDB()

def get_supabase():
    # Ensure connection is established when needed
    if db.client is None:
        db.connect()
    return db.client
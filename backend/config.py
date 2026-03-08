import os
from supabase import create_client, Client
from dotenv import load_dotenv
import redis
from typing import Optional

load_dotenv()

# Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")

supabase: Optional[Client] = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✓ Supabase initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Supabase: {e}")
        supabase = None
else:
    print("⚠ Supabase credentials not found in environment variables")

# Redis
redis_url = os.getenv("REDIS_URL")
redis_client: Optional[redis.Redis] = None
if redis_url:
    try:
        redis_client = redis.from_url(redis_url)
        redis_client.ping()  # Test connection
        print("✓ Redis initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Redis: {e}")
        redis_client = None
else:
    print("⚠ Redis URL not found in environment variables")

# OpenAI
openai_key = os.getenv("OPENAI_API_KEY")
openai_client = None
if openai_key:
    try:
        import openai
        openai.api_key = openai_key
        openai_client = openai
        print("✓ OpenAI initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize OpenAI: {e}")
        openai_client = None
else:
    print("⚠ OpenAI API key not found in environment variables")
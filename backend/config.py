import os
from supabase import create_client, Client
from dotenv import load_dotenv
import redis

load_dotenv()

# Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")

supabase: Client = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Failed to initialize Supabase: {e}")
        supabase = None

# Redis
redis_url = os.getenv("REDIS_URL")
redis_client = None
if redis_url:
    try:
        redis_client = redis.from_url(redis_url)
    except Exception as e:
        print(f"Failed to initialize Redis: {e}")
        redis_client = None

# OpenAI
openai_key = os.getenv("OPENAI_API_KEY")
openai_client = None
if openai_key:
    try:
        import openai
        openai.api_key = openai_key
        openai_client = openai
    except Exception as e:
        print(f"Failed to initialize OpenAI: {e}")
        openai_client = None
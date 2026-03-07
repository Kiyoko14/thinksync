from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import supabase, redis_client, openai_client

app = FastAPI(title="AI DevOps Platform", version="1.0.0")

# CORS - Open for everyone for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://api.thinksync.art"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI DevOps Platform API"}

# Include routers
from routers import auth, servers, chats, agents, database
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(chats.router)
app.include_router(agents.router)
app.include_router(database.router)

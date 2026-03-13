import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import supabase, redis_client, openai_client

app = FastAPI(title="AI DevOps Platform", version="1.0.0")

# CORS Configuration — allow Replit dev domain and production domain
_replit_domain = os.getenv("REPLIT_DEV_DOMAIN", "")
allowed_origins = [
    "https://app.thinksync.art",
    *(
        [f"https://{_replit_domain}"]
        if _replit_domain else []
    ),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI DevOps Platform API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment"""
    health_status = {
        "status": "healthy",
        "database": "connected" if supabase else "disconnected",
        "redis": "connected" if redis_client else "disconnected",
        "openai": "configured" if openai_client else "not_configured"
    }
    return health_status

# Include routers
from routers import auth, servers, chats, agents, database, deployments, tasks, messages
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(agents.router)
app.include_router(database.router)
app.include_router(deployments.router)
app.include_router(tasks.router)

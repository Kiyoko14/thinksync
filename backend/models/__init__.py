from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime

class User(BaseModel):
    id: str
    email: str
    created_at: datetime

class Server(BaseModel):
    id: str
    user_id: str
    name: str
    host: str
    ssh_user: str
    ssh_port: int = 22
    ssh_auth_method: Literal["private_key", "password"] = "private_key"
    ssh_key: Optional[str] = None
    ssh_password: Optional[str] = None
    created_at: datetime

class Chat(BaseModel):
    id: str
    server_id: str
    user_id: str
    name: str
    workspace_path: str
    created_at: datetime

class Message(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    created_at: datetime

class Action(BaseModel):
    id: str
    chat_id: str
    action_json: dict
    result: Optional[str]
    created_at: datetime

class Task(BaseModel):
    id: str
    chat_id: str
    state: str
    step: str
    attempts: int = 0
    created_at: datetime

class Workspace(BaseModel):
    id: str
    chat_id: str
    path: str
    created_at: datetime

class Database(BaseModel):
    id: str
    user_id: str
    server_id: Optional[str]
    project_id: str
    db_url: str
    created_at: datetime
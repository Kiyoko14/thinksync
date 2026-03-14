"""
Repository layer initialization.

Provides singleton instances of all repositories.
"""

from .base import BaseRepository
from .repositories import (
    ServerRepository,
    ChatRepository,
    MessageRepository,
    DeploymentRepository,
    SecretRepository,
)

# Singleton instances
server_repo = ServerRepository()
chat_repo = ChatRepository()
message_repo = MessageRepository()
deployment_repo = DeploymentRepository()
secret_repo = SecretRepository()

__all__ = [
    "BaseRepository",
    "ServerRepository",
    "ChatRepository",
    "MessageRepository",
    "DeploymentRepository",
    "SecretRepository",
    "server_repo",
    "chat_repo",
    "message_repo",
    "deployment_repo",
    "secret_repo",
]

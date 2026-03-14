"""
Server repository for database operations.

Provides specialized methods for server management.
"""

from typing import Dict, List, Optional
from .base import BaseRepository


class ServerRepository(BaseRepository):
    """Repository for server operations."""
    
    def __init__(self):
        super().__init__("servers")
    
    async def find_by_user(
        self,
        user_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Find all servers for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            
        Returns:
            List of user's servers
        """
        return await self.find_all(
            filters={"user_id": user_id},
            order_by="created_at",
            desc=True,
            limit=limit,
        )
    
    async def find_by_host(
        self,
        user_id: str,
        host: str,
    ) -> Optional[Dict]:
        """
        Find a server by host for a specific user.
        
        Args:
            user_id: User ID
            host: Server hostname
            
        Returns:
            Matching server or None
        """
        return await self.find_one({
            "user_id": user_id,
            "host": host,
        })
    
    async def update_connection_status(
        self,
        server_id: str,
        status: str,
        user_id: str,
    ) -> Optional[Dict]:
        """
        Update server connection status.
        
        Args:
            server_id: Server ID
            status: New status (online/offline/error)
            user_id: User ID for access control
            
        Returns:
            Updated server or None
        """
        return await self.update(
            server_id,
            {"connection_status": status},
            user_id=user_id,
        )


class ChatRepository(BaseRepository):
    """Repository for chat operations."""
    
    def __init__(self):
        super().__init__("chats")
    
    async def find_by_server(
        self,
        server_id: str,
        user_id: str,
    ) -> List[Dict]:
        """
        Find all chats for a server.
        
        Args:
            server_id: Server ID
            user_id: User ID for access control
            
        Returns:
            List of chats
        """
        return await self.find_all(
            filters={"server_id": server_id, "user_id": user_id},
            order_by="created_at",
            desc=True,
        )
    
    async def find_by_name(
        self,
        user_id: str,
        name: str,
    ) -> Optional[Dict]:
        """
        Find a chat by name for a user.
        
        Args:
            user_id: User ID
            name: Chat name
            
        Returns:
            Matching chat or None
        """
        return await self.find_one({
            "user_id": user_id,
            "name": name,
        })


class MessageRepository(BaseRepository):
    """Repository for message operations."""
    
    def __init__(self):
        super().__init__("messages")
    
    async def find_by_chat(
        self,
        chat_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict]:
        """
        Find messages for a chat.
        
        Args:
            chat_id: Chat ID
            limit: Maximum number of messages
            offset: Number of messages to skip
            
        Returns:
            List of messages ordered by creation time
        """
        if not self.db:
            return []
        
        def query():
            q = self.db.table(self.table_name).select("*").eq("chat_id", chat_id)
            q = q.order("created_at", desc=False)
            
            if offset:
                q = q.range(offset, offset + (limit or 100) - 1)
            elif limit:
                q = q.limit(limit)
            
            return q.execute()
        
        from config import async_db
        response = await async_db(query)
        return response.data or []
    
    async def create_bulk(
        self,
        messages: List[Dict],
    ) -> List[Dict]:
        """
        Create multiple messages at once.
        
        Args:
            messages: List of message data
            
        Returns:
            List of created messages
        """
        if not self.db:
            raise Exception("Database not configured")
        
        from config import async_db
        response = await async_db(
            lambda: self.db.table(self.table_name).insert(messages).execute()
        )
        
        return response.data or []


class DeploymentRepository(BaseRepository):
    """Repository for deployment operations."""
    
    def __init__(self):
        super().__init__("deployments")
    
    async def find_by_server(
        self,
        server_id: str,
        user_id: str,
        limit: Optional[int] = 20,
    ) -> List[Dict]:
        """
        Find deployments for a server.
        
        Args:
            server_id: Server ID
            user_id: User ID for access control
            limit: Maximum number of results
            
        Returns:
            List of deployments ordered by creation time
        """
        return await self.find_all(
            filters={"server_id": server_id, "user_id": user_id},
            order_by="created_at",
            desc=True,
            limit=limit,
        )
    
    async def find_pending(
        self,
        user_id: str,
    ) -> List[Dict]:
        """
        Find all pending deployments for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of pending deployments
        """
        return await self.find_all(
            filters={"user_id": user_id, "status": "pending"},
            order_by="created_at",
            desc=False,
        )
    
    async def update_status(
        self,
        deployment_id: str,
        status: str,
        user_id: str,
    ) -> Optional[Dict]:
        """
        Update deployment status.
        
        Args:
            deployment_id: Deployment ID
            status: New status
            user_id: User ID for access control
            
        Returns:
            Updated deployment or None
        """
        return await self.update(
            deployment_id,
            {"status": status},
            user_id=user_id,
        )


class SecretRepository(BaseRepository):
    """Repository for secrets management."""
    
    def __init__(self):
        super().__init__("server_secrets")
    
    async def find_by_server(
        self,
        server_id: str,
        user_id: str,
    ) -> List[Dict]:
        """
        Find all secrets for a server.
        
        Args:
            server_id: Server ID
            user_id: User ID for access control
            
        Returns:
            List of secrets
        """
        return await self.find_all(
            filters={"server_id": server_id, "user_id": user_id},
            order_by="name",
        )
    
    async def find_by_name(
        self,
        server_id: str,
        name: str,
        user_id: str,
    ) -> Optional[Dict]:
        """
        Find a secret by name.
        
        Args:
            server_id: Server ID
            name: Secret name
            user_id: User ID for access control
            
        Returns:
            Matching secret or None
        """
        return await self.find_one({
            "server_id": server_id,
            "name": name,
            "user_id": user_id,
        })
    
    async def upsert(
        self,
        server_id: str,
        name: str,
        value: str,
        user_id: str,
    ) -> Dict:
        """
        Create or update a secret.
        
        Args:
            server_id: Server ID
            name: Secret name
            value: Secret value
            user_id: User ID
            
        Returns:
            Created or updated secret
        """
        existing = await self.find_by_name(server_id, name, user_id)
        
        if existing:
            return await self.update(
                existing["id"],
                {"value": value},
                user_id=user_id,
            )
        else:
            return await self.create({
                "server_id": server_id,
                "name": name,
                "value": value,
                "user_id": user_id,
            })

"""
Base repository for database operations.

Provides abstract base class for all repositories with common CRUD operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from config import supabase, async_db

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository class.
    
    Provides common database operations with async support and proper
    error handling. All repositories should inherit from this class.
    """
    
    def __init__(self, table_name: str):
        """
        Initialize repository.
        
        Args:
            table_name: Name of the Supabase table
        """
        self.table_name = table_name
        self.db = supabase
    
    async def find_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        desc: bool = False,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find all records matching filters.
        
        Args:
            filters: Dictionary of column:value filters
            order_by: Column to order by
            desc: Whether to sort descending
            limit: Maximum number of results
            
        Returns:
            List of matching records
        """
        if not self.db:
            return []
        
        def query():
            q = self.db.table(self.table_name).select("*")
            
            if filters:
                for key, value in filters.items():
                    q = q.eq(key, value)
            
            if order_by:
                q = q.order(order_by, desc=desc)
            
            if limit:
                q = q.limit(limit)
            
            return q.execute()
        
        response = await async_db(query)
        return response.data or []
    
    async def find_one(
        self,
        filters: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Find a single record matching filters.
        
        Args:
            filters: Dictionary of column:value filters
            
        Returns:
            Matching record or None
        """
        if not self.db:
            return None
        
        def query():
            q = self.db.table(self.table_name).select("*")
            for key, value in filters.items():
                q = q.eq(key, value)
            return q.limit(1).execute()
        
        response = await async_db(query)
        data = response.data or []
        return data[0] if data else None
    
    async def find_by_id(
        self,
        id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a record by ID.
        
        Args:
            id: Record ID
            user_id: Optional user ID for access control
            
        Returns:
            Matching record or None
        """
        filters = {"id": id}
        if user_id:
            filters["user_id"] = user_id
        
        return await self.find_one(filters)
    
    async def create(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new record.
        
        Args:
            data: Record data
            
        Returns:
            Created record with generated fields
            
        Raises:
            Exception: If creation fails
        """
        if not self.db:
            raise Exception("Database not configured")
        
        response = await async_db(
            lambda: self.db.table(self.table_name).insert(data).execute()
        )
        
        if not response.data:
            raise Exception(f"Failed to create {self.table_name} record")
        
        return response.data[0]
    
    async def update(
        self,
        id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a record by ID.
        
        Args:
            id: Record ID
            data: Updated data
            user_id: Optional user ID for access control
            
        Returns:
            Updated record or None
        """
        if not self.db:
            raise Exception("Database not configured")
        
        def query():
            q = self.db.table(self.table_name).update(data).eq("id", id)
            if user_id:
                q = q.eq("user_id", user_id)
            return q.execute()
        
        response = await async_db(query)
        data = response.data or []
        return data[0] if data else None
    
    async def delete(
        self,
        id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: Record ID
            user_id: Optional user ID for access control
            
        Returns:
            True if deleted, False otherwise
        """
        if not self.db:
            raise Exception("Database not configured")
        
        def query():
            q = self.db.table(self.table_name).delete().eq("id", id)
            if user_id:
                q = q.eq("user_id", user_id)
            return q.execute()
        
        response = await async_db(query)
        return len(response.data or []) > 0
    
    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Count records matching filters.
        
        Args:
            filters: Dictionary of column:value filters
            
        Returns:
            Number of matching records
        """
        if not self.db:
            return 0
        
        def query():
            q = self.db.table(self.table_name).select("id", count="exact")
            
            if filters:
                for key, value in filters.items():
                    q = q.eq(key, value)
            
            return q.execute()
        
        response = await async_db(query)
        return response.count or 0
    
    async def exists(
        self,
        filters: Dict[str, Any],
    ) -> bool:
        """
        Check if a record exists matching filters.
        
        Args:
            filters: Dictionary of column:value filters
            
        Returns:
            True if exists, False otherwise
        """
        count = await self.count(filters)
        return count > 0

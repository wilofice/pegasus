"""Base repository class for common database operations."""
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from models.base import Base

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""
    
    def __init__(self, model: Type[T], db_session: AsyncSession):
        self.model = model
        self.db_session = db_session
    
    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new record."""
        instance = self.model(**data)
        self.db_session.add(instance)
        await self.db_session.commit()
        await self.db_session.refresh(instance)
        return instance
    
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """Get a record by ID."""
        result = await self.db_session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination."""
        result = await self.db_session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()
    
    async def update(self, id: UUID, data: Dict[str, Any]) -> Optional[T]:
        """Update a record by ID."""
        instance = await self.get_by_id(id)
        if not instance:
            return None
        
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        await self.db_session.commit()
        await self.db_session.refresh(instance)
        return instance
    
    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID."""
        instance = await self.get_by_id(id)
        if not instance:
            return False
        
        await self.db_session.delete(instance)
        await self.db_session.commit()
        return True
    
    async def count(self) -> int:
        """Count total records."""
        result = await self.db_session.execute(select(self.model))
        return len(result.scalars().all())
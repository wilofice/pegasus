"""Base repository class for common database operations."""

from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import Select

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def get(self, id: Any) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await self.db.get(self.model, id)
        return result
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination."""
        query = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create(self, data: Dict[str, Any]) -> ModelType:
        """Create a new record."""
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance
    
    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[ModelType]:
        """Update an existing record."""
        instance = await self.get(id)
        if instance:
            for key, value in data.items():
                setattr(instance, key, value)
            await self.db.commit()
            await self.db.refresh(instance)
        return instance
    
    async def delete(self, id: Any) -> bool:
        """Delete a record."""
        instance = await self.get(id)
        if instance:
            await self.db.delete(instance)
            await self.db.commit()
            return True
        return False
    
    def query(self) -> Select:
        """Get a base query for the model."""
        return select(self.model)
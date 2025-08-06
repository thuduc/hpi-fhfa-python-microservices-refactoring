"""Base model classes for RSAI microservices."""

from datetime import datetime
from typing import Optional, Any, Dict
from uuid import UUID, uuid4
from pydantic import BaseModel as PydanticBaseModel, Field


class BaseModel(PydanticBaseModel):
    """Base model with common configuration."""
    
    class Config:
        # Enable arbitrary types
        arbitrary_types_allowed = True
        # Use enum values instead of enum names
        use_enum_values = True
        # Validate assignment
        validate_assignment = True
        # JSON encoders for common types
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class TimestampedModel(BaseModel):
    """Model with automatic timestamp tracking."""
    
    id: Optional[UUID] = Field(default_factory=uuid4, description="Unique identifier")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    
    success: bool = Field(description="Whether the request was successful")
    message: str = Field(description="Human-readable message")
    data: Optional[Any] = Field(default=None, description="Response data")
    errors: Optional[list[str]] = Field(default=None, description="List of error messages")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    request_id: Optional[str] = Field(default=None, description="Request correlation ID")


class PaginatedResponse(APIResponse):
    """Paginated API response."""
    
    total_count: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    
    @classmethod
    def create(cls, data: list[Any], total_count: int, page: int, page_size: int, **kwargs) -> "PaginatedResponse":
        """Create a paginated response."""
        total_pages = (total_count + page_size - 1) // page_size
        return cls(
            success=True,
            message="Data retrieved successfully",
            data=data,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            **kwargs
        )
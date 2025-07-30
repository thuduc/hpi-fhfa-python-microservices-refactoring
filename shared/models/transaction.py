"""Transaction data models for RSAI microservices."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from enum import Enum
from pydantic import Field, validator

from .base import TimestampedModel


class TransactionType(str, Enum):
    """Types of real estate transactions."""
    ARMS_LENGTH = "arms_length"
    NON_ARMS_LENGTH = "non_arms_length"
    FORECLOSURE = "foreclosure"
    SHORT_SALE = "short_sale"


class PropertyType(str, Enum):
    """Types of properties."""
    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi_family"
    OTHER = "other"


class TransactionBase(TimestampedModel):
    """Base transaction model with common fields."""
    
    property_id: str = Field(..., description="Unique property identifier")
    transaction_date: date = Field(..., description="Date of transaction")
    transaction_price: Decimal = Field(..., gt=0, description="Transaction price in USD")
    transaction_type: TransactionType = Field(default=TransactionType.ARMS_LENGTH, description="Type of transaction")
    
    # Geographic information
    census_tract_2010: str = Field(..., description="2010 Census tract identifier")
    cbsa_id: str = Field(..., description="Core Based Statistical Area identifier")
    county_fips: Optional[str] = Field(None, description="County FIPS code")
    state_code: Optional[str] = Field(None, description="State code")
    zip_code: Optional[str] = Field(None, description="ZIP code")
    
    # Property characteristics
    property_type: Optional[PropertyType] = Field(None, description="Type of property")
    square_footage: Optional[int] = Field(None, gt=0, description="Living area in square feet")
    bedrooms: Optional[int] = Field(None, ge=0, le=20, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, ge=0, le=20, description="Number of bathrooms")
    year_built: Optional[int] = Field(None, ge=1800, le=2030, description="Year property was built")
    
    @validator('transaction_price')
    def validate_price(cls, v):
        """Validate transaction price is reasonable."""
        if v < 1000:
            raise ValueError("Transaction price must be at least $1,000")
        if v > 1_000_000_000:
            raise ValueError("Transaction price cannot exceed $1 billion")
        return v
    
    @validator('census_tract_2010')
    def validate_census_tract(cls, v):
        """Validate census tract format."""
        if len(v) < 6:
            raise ValueError("Census tract must be at least 6 characters")
        return v
    
    @validator('cbsa_id')
    def validate_cbsa(cls, v):
        """Validate CBSA identifier."""
        if not v.isdigit() or len(v) != 5:
            raise ValueError("CBSA ID must be a 5-digit number")
        return v


class Transaction(TransactionBase):
    """Complete transaction model for database storage."""
    
    # Processing metadata
    data_source: Optional[str] = Field(None, description="Source of the transaction data")
    processing_status: Optional[str] = Field(default="pending", description="Processing status")
    validation_errors: Optional[list[str]] = Field(default=None, description="Validation error messages")
    
    # Derived fields (calculated during processing)
    price_per_sqft: Optional[Decimal] = Field(None, description="Price per square foot")
    is_repeat_sale: Optional[bool] = Field(default=False, description="Whether this property has multiple sales")
    supertract_id: Optional[str] = Field(None, description="Assigned supertract identifier")


class TransactionCreate(TransactionBase):
    """Model for creating new transactions."""
    pass


class TransactionUpdate(TimestampedModel):
    """Model for updating existing transactions."""
    
    transaction_price: Optional[Decimal] = Field(None, gt=0, description="Updated transaction price")
    transaction_type: Optional[TransactionType] = Field(None, description="Updated transaction type")
    processing_status: Optional[str] = Field(None, description="Updated processing status")
    validation_errors: Optional[list[str]] = Field(None, description="Updated validation errors")
    supertract_id: Optional[str] = Field(None, description="Updated supertract assignment")


class TransactionSummary(TimestampedModel):
    """Summary statistics for transactions."""
    
    total_transactions: int = Field(description="Total number of transactions")
    date_range_start: date = Field(description="Earliest transaction date")
    date_range_end: date = Field(description="Latest transaction date")
    price_range_min: Decimal = Field(description="Minimum transaction price")
    price_range_max: Decimal = Field(description="Maximum transaction price")
    median_price: Decimal = Field(description="Median transaction price")
    unique_properties: int = Field(description="Number of unique properties")
    repeat_sales_properties: int = Field(description="Number of properties with multiple sales")
    geographic_coverage: dict[str, int] = Field(description="Count by geographic area")


class RepeatSalePair(TimestampedModel):
    """Model for repeat sale pairs used in index calculation."""
    
    property_id: str = Field(..., description="Property identifier")
    first_sale_id: str = Field(..., description="First transaction ID")
    second_sale_id: str = Field(..., description="Second transaction ID")
    
    first_sale_date: date = Field(..., description="First sale date")
    second_sale_date: date = Field(..., description="Second sale date")
    first_sale_price: Decimal = Field(..., gt=0, description="First sale price")
    second_sale_price: Decimal = Field(..., gt=0, description="Second sale price")
    
    # Calculated fields
    price_ratio: Decimal = Field(..., description="Second price / First price")
    log_price_ratio: float = Field(..., description="Natural log of price ratio")
    holding_period_days: int = Field(..., gt=0, description="Days between sales")
    holding_period_years: float = Field(..., gt=0, description="Years between sales")
    
    # Geographic assignment
    census_tract_2010: str = Field(..., description="Census tract")
    cbsa_id: str = Field(..., description="CBSA identifier")
    supertract_id: Optional[str] = Field(None, description="Assigned supertract")
    
    @validator('second_sale_date')
    def validate_sale_order(cls, v, values):
        """Ensure second sale is after first sale."""
        if 'first_sale_date' in values and v <= values['first_sale_date']:
            raise ValueError("Second sale date must be after first sale date")
        return v
    
    @validator('price_ratio')
    def validate_price_ratio(cls, v, values):
        """Validate price ratio calculation."""
        if 'first_sale_price' in values and 'second_sale_price' in values:
            expected_ratio = values['second_sale_price'] / values['first_sale_price']
            if abs(v - expected_ratio) > 0.001:  # Allow for rounding differences
                raise ValueError("Price ratio doesn't match calculated value")
        return v
"""Geographic data models for RSAI microservices."""

from typing import Optional, Dict, List
from decimal import Decimal
from pydantic import Field, validator
from enum import Enum

from .base import TimestampedModel


class GeographicLevel(str, Enum):
    """Geographic aggregation levels."""
    PROPERTY = "property"
    TRACT = "tract"
    SUPERTRACT = "supertract"
    COUNTY = "county"
    CBSA = "cbsa"
    STATE = "state"
    NATIONAL = "national"


class GeographicUnit(TimestampedModel):
    """Base geographic unit model."""
    
    geographic_id: str = Field(..., description="Unique geographic identifier")
    geographic_level: GeographicLevel = Field(..., description="Level of geographic aggregation")
    name: Optional[str] = Field(None, description="Human-readable name")
    
    # Coordinates (centroid or representative point)
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    
    # Hierarchical relationships
    parent_id: Optional[str] = Field(None, description="Parent geographic unit ID")
    children_ids: Optional[List[str]] = Field(default=None, description="Child geographic unit IDs")
    
    # Statistical properties
    total_area_sqkm: Optional[float] = Field(None, gt=0, description="Total area in square kilometers")
    population: Optional[int] = Field(None, ge=0, description="Population count")
    housing_units: Optional[int] = Field(None, ge=0, description="Number of housing units")
    
    # RSAI-specific metadata
    transaction_count: Optional[int] = Field(default=0, description="Number of transactions in this unit")
    property_count: Optional[int] = Field(default=0, description="Number of unique properties")
    repeat_sales_count: Optional[int] = Field(default=0, description="Number of repeat sale pairs")
    
    @validator('latitude', 'longitude')
    def validate_coordinates(cls, v, field):
        """Validate coordinate values."""
        if v is not None:
            if field.name == 'latitude' and not -90 <= v <= 90:
                raise ValueError("Latitude must be between -90 and 90")
            elif field.name == 'longitude' and not -180 <= v <= 180:
                raise ValueError("Longitude must be between -180 and 180")
        return v


class CensusTract(GeographicUnit):
    """2010 Census tract geographic unit."""
    
    tract_code: str = Field(..., description="Census tract code")
    county_fips: str = Field(..., description="County FIPS code")
    state_fips: str = Field(..., description="State FIPS code")
    
    # Census demographics
    median_household_income: Optional[Decimal] = Field(None, description="Median household income")
    median_home_value: Optional[Decimal] = Field(None, description="Median home value")
    
    def __init__(self, **data):
        # Set geographic level automatically
        data['geographic_level'] = GeographicLevel.TRACT
        super().__init__(**data)


class CBSA(GeographicUnit):
    """Core Based Statistical Area geographic unit."""
    
    cbsa_code: str = Field(..., description="CBSA code")
    cbsa_type: str = Field(..., description="Metropolitan or Micropolitan")
    principal_city: Optional[str] = Field(None, description="Principal city name")
    
    # Economic indicators
    population_2020: Optional[int] = Field(None, description="2020 Census population")
    gdp_per_capita: Optional[Decimal] = Field(None, description="GDP per capita")
    
    def __init__(self, **data):
        # Set geographic level automatically
        data['geographic_level'] = GeographicLevel.CBSA
        super().__init__(**data)


class SupertractDefinition(TimestampedModel):
    """Definition of a dynamically generated supertract."""
    
    supertract_id: str = Field(..., description="Unique supertract identifier")
    cbsa_id: str = Field(..., description="Parent CBSA identifier")
    name: Optional[str] = Field(None, description="Human-readable supertract name")
    
    # Constituent tracts
    tract_ids: List[str] = Field(..., min_items=1, description="List of census tract IDs in this supertract")
    
    # Generation metadata
    generation_method: str = Field(..., description="Algorithm used to generate supertract")
    generation_parameters: Dict[str, float] = Field(..., description="Parameters used in generation")
    min_observations_threshold: int = Field(..., description="Minimum observations requirement")
    
    # Statistical properties
    total_transactions: int = Field(..., ge=0, description="Total transactions in supertract")
    total_properties: int = Field(..., ge=0, description="Total unique properties")
    total_repeat_pairs: int = Field(..., ge=0, description="Total repeat sale pairs")
    
    # Geographic properties
    centroid_latitude: Optional[float] = Field(None, description="Geographic centroid latitude")
    centroid_longitude: Optional[float] = Field(None, description="Geographic centroid longitude")
    total_area_sqkm: Optional[float] = Field(None, gt=0, description="Total area in square kilometers")
    
    @validator('tract_ids')
    def validate_unique_tracts(cls, v):
        """Ensure tract IDs are unique."""
        if len(v) != len(set(v)):
            raise ValueError("Tract IDs must be unique")
        return v
    
    @validator('total_repeat_pairs')
    def validate_sufficient_observations(cls, v, values):
        """Validate minimum observations requirement is met."""
        if 'min_observations_threshold' in values and v < values['min_observations_threshold']:
            raise ValueError(f"Supertract must have at least {values['min_observations_threshold']} repeat pairs")
        return v


class DistanceMatrix(TimestampedModel):
    """Geographic distance matrix between census tracts."""
    
    tract_id_1: str = Field(..., description="First census tract ID")
    tract_id_2: str = Field(..., description="Second census tract ID")
    
    # Distance measurements
    euclidean_distance_km: float = Field(..., ge=0, description="Euclidean distance in kilometers")
    great_circle_distance_km: float = Field(..., ge=0, description="Great circle distance in kilometers")
    
    # Optional advanced distance measures
    road_distance_km: Optional[float] = Field(None, ge=0, description="Road network distance in kilometers")
    travel_time_minutes: Optional[float] = Field(None, ge=0, description="Estimated travel time in minutes")
    
    # Calculation metadata
    calculation_method: str = Field(..., description="Method used to calculate distance")
    calculation_timestamp: Optional[str] = Field(None, description="When distance was calculated")
    
    @validator('tract_id_2')
    def validate_different_tracts(cls, v, values):
        """Ensure we're not calculating distance from a tract to itself."""
        if 'tract_id_1' in values and v == values['tract_id_1']:
            raise ValueError("Cannot calculate distance from a tract to itself")
        return v


class ClusteringResult(TimestampedModel):
    """Result of geographic clustering algorithm."""
    
    cbsa_id: str = Field(..., description="CBSA where clustering was performed")
    algorithm: str = Field(..., description="Clustering algorithm used")
    parameters: Dict[str, float] = Field(..., description="Algorithm parameters")
    
    # Results
    total_tracts: int = Field(..., ge=0, description="Total tracts processed")
    total_supertracts: int = Field(..., ge=0, description="Total supertracts generated")
    unclustered_tracts: List[str] = Field(default=[], description="Tracts that couldn't be clustered")
    
    # Quality metrics
    average_supertract_size: float = Field(..., description="Average number of tracts per supertract")
    min_supertract_observations: int = Field(..., description="Minimum observations in any supertract")
    coverage_ratio: float = Field(..., ge=0, le=1, description="Ratio of tracts successfully clustered")
    
    # Execution metadata
    execution_time_seconds: float = Field(..., ge=0, description="Time taken to execute clustering")
    memory_usage_mb: Optional[float] = Field(None, description="Peak memory usage during clustering")


class SpatialIndex(TimestampedModel):
    """Spatial index for efficient geographic queries."""
    
    index_name: str = Field(..., description="Name of the spatial index")
    geographic_level: GeographicLevel = Field(..., description="Geographic level indexed")
    
    # Index properties
    bounding_box: Dict[str, float] = Field(..., description="Bounding box of indexed area")
    total_features: int = Field(..., ge=0, description="Number of geographic features indexed")
    
    # Index configuration
    grid_size: Optional[int] = Field(None, description="Grid size for spatial indexing")
    max_depth: Optional[int] = Field(None, description="Maximum tree depth")
    
    @validator('bounding_box')
    def validate_bounding_box(cls, v):
        """Validate bounding box has required coordinates."""
        required_keys = ['min_lat', 'max_lat', 'min_lon', 'max_lon']
        if not all(key in v for key in required_keys):
            raise ValueError(f"Bounding box must contain: {required_keys}")
        
        if v['min_lat'] >= v['max_lat']:
            raise ValueError("min_lat must be less than max_lat")
        if v['min_lon'] >= v['max_lon']:
            raise ValueError("min_lon must be less than max_lon")
        
        return v
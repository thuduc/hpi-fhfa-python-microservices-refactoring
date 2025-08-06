"""Index calculation models for RSAI microservices."""

from typing import List, Dict, Any, Optional
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pydantic import Field, validator

from .base import TimestampedModel


class WeightingScheme(str, Enum):
    """House price index weighting schemes."""
    EQUAL = "equal"
    VALUE = "value"
    CASE_SHILLER = "case_shiller"
    BMN = "bmn"


class IndexFrequency(str, Enum):
    """Index calculation frequency."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class IndexValue(TimestampedModel):
    """House price index value for a specific geography and time period."""
    
    geography_id: str = Field(..., description="Geographic unit identifier")
    geography_level: str = Field(..., description="Geographic level (tract, county, cbsa)")
    period: date = Field(..., description="Time period for this index value")
    
    # Index values
    index_value: Decimal = Field(..., gt=0, description="Index value (typically base=100)")
    base_period: Optional[date] = Field(None, description="Base period for index")
    base_value: Decimal = Field(default=Decimal("100"), description="Base index value")
    
    # Calculation metadata
    weighting_scheme: WeightingScheme = Field(..., description="Weighting methodology used")
    frequency: IndexFrequency = Field(..., description="Index calculation frequency")
    
    # Supporting data
    num_pairs: int = Field(..., ge=0, description="Number of repeat sale pairs")
    num_properties: int = Field(..., ge=0, description="Number of unique properties")
    median_price: Optional[Decimal] = Field(None, gt=0, description="Median transaction price")
    
    # Statistical measures
    standard_error: Optional[Decimal] = Field(None, ge=0, description="Standard error of index")
    confidence_lower: Optional[Decimal] = Field(None, description="Lower confidence bound")
    confidence_upper: Optional[Decimal] = Field(None, description="Upper confidence bound")
    
    # Quality indicators
    coverage_ratio: Optional[float] = Field(None, ge=0, le=1, description="Geographic coverage ratio")
    data_quality_score: Optional[float] = Field(None, ge=0, le=1, description="Data quality score")
    
    @validator('confidence_lower', 'confidence_upper')
    def validate_confidence_bounds(cls, v, values):
        """Ensure confidence bounds are reasonable."""
        if v is not None and 'index_value' in values:
            if v < 0:
                raise ValueError("Confidence bounds cannot be negative")
        return v


class RegressionResult(TimestampedModel):
    """Result of BMN regression for a supertract and time period."""
    
    supertract_id: str = Field(..., description="Supertract identifier")
    time_period: str = Field(..., description="Time period identifier")
    
    # Regression coefficients
    time_coefficient: float = Field(..., description="Time dummy coefficient")
    constant_term: Optional[float] = Field(None, description="Regression constant")
    
    # Statistical measures
    standard_error: float = Field(..., ge=0, description="Standard error of coefficient")
    t_statistic: float = Field(..., description="T-statistic for coefficient")
    p_value: float = Field(..., ge=0, le=1, description="P-value for coefficient")
    
    # Model fit
    r_squared: float = Field(..., ge=0, le=1, description="R-squared of regression")
    adjusted_r_squared: float = Field(..., ge=0, le=1, description="Adjusted R-squared")
    f_statistic: Optional[float] = Field(None, ge=0, description="F-statistic for model")
    
    # Data used
    num_observations: int = Field(..., ge=0, description="Number of observations in regression")
    degrees_of_freedom: int = Field(..., ge=0, description="Degrees of freedom")
    
    # Diagnostics
    durbin_watson: Optional[float] = Field(None, description="Durbin-Watson statistic")
    residual_std_error: Optional[float] = Field(None, ge=0, description="Residual standard error")
    
    @validator('p_value')
    def validate_p_value(cls, v):
        """Ensure p-value is valid probability."""
        if not 0 <= v <= 1:
            raise ValueError("P-value must be between 0 and 1")
        return v


class WeightCalculation(TimestampedModel):
    """Weight calculation for a repeat sale pair."""
    
    pair_id: str = Field(..., description="Repeat sale pair identifier")
    property_id: str = Field(..., description="Property identifier")
    
    # Weight values by scheme
    equal_weight: float = Field(default=1.0, description="Equal weighting (always 1.0)")
    value_weight: Optional[float] = Field(None, ge=0, description="Value-based weight")
    case_shiller_weight: Optional[float] = Field(None, ge=0, description="Case-Shiller weight")
    bmn_weight: Optional[float] = Field(None, ge=0, description="BMN regression weight")
    
    # Weight calculation inputs
    average_price: Optional[Decimal] = Field(None, gt=0, description="Average of two sale prices")
    price_variance: Optional[float] = Field(None, ge=0, description="Price variance estimate")
    holding_period_years: float = Field(..., gt=0, description="Holding period in years")
    
    # Quality adjustments
    quality_adjustment: float = Field(default=1.0, description="Quality adjustment factor")
    outlier_flag: bool = Field(default=False, description="Whether pair is flagged as outlier")
    
    @validator('equal_weight')
    def validate_equal_weight(cls, v):
        """Equal weight should always be 1.0."""
        if v != 1.0:
            raise ValueError("Equal weight must be 1.0")
        return v


class IndexCalculationJob(TimestampedModel):
    """Job for calculating house price indices."""
    
    job_name: str = Field(..., description="Human-readable job name")
    cbsa_id: str = Field(..., description="CBSA identifier")
    
    # Calculation parameters
    weighting_scheme: WeightingScheme = Field(..., description="Weighting methodology")
    frequency: IndexFrequency = Field(..., description="Index frequency")
    base_period: Optional[date] = Field(None, description="Base period for index")
    
    # Date range
    start_date: Optional[date] = Field(None, description="Start date for calculation")
    end_date: Optional[date] = Field(None, description="End date for calculation")
    
    # Job status
    status: str = Field(default="pending", description="Job status")
    progress_percentage: int = Field(default=0, ge=0, le=100, description="Completion percentage")
    
    # Results summary
    periods_calculated: Optional[int] = Field(None, ge=0, description="Number of periods calculated")
    total_pairs_used: Optional[int] = Field(None, ge=0, description="Total repeat sale pairs used")
    
    # Timing
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if job failed")


class IndexTimeSeries(TimestampedModel):
    """Time series of index values for a geography."""
    
    geography_id: str = Field(..., description="Geographic unit identifier")
    geography_level: str = Field(..., description="Geographic level")
    weighting_scheme: WeightingScheme = Field(..., description="Weighting methodology")
    frequency: IndexFrequency = Field(..., description="Index frequency")
    
    # Time series data
    periods: List[date] = Field(..., description="Time periods")
    index_values: List[Decimal] = Field(..., description="Index values")
    standard_errors: Optional[List[Optional[Decimal]]] = Field(None, description="Standard errors")
    
    # Series metadata
    base_period: date = Field(..., description="Base period")
    base_value: Decimal = Field(default=Decimal("100"), description="Base index value")
    
    # Summary statistics
    total_periods: int = Field(..., ge=0, description="Number of periods")
    min_value: Decimal = Field(..., description="Minimum index value")
    max_value: Decimal = Field(..., description="Maximum index value")
    mean_value: Decimal = Field(..., description="Mean index value")
    
    # Growth rates
    period_growth_rates: Optional[List[Optional[float]]] = Field(None, description="Period-over-period growth")
    annual_growth_rates: Optional[List[Optional[float]]] = Field(None, description="Year-over-year growth")
    
    @validator('index_values')
    def validate_index_values_length(cls, v, values):
        """Ensure index values match periods length."""
        if 'periods' in values and len(v) != len(values['periods']):
            raise ValueError("Index values must match periods length")
        return v


class IndexComparison(TimestampedModel):
    """Comparison of indices across geographies or methodologies."""
    
    comparison_name: str = Field(..., description="Comparison name")
    comparison_type: str = Field(..., description="Type of comparison (geography, methodology, etc.)")
    
    # Comparison data
    geographies: List[str] = Field(..., description="Geographic units compared")
    periods: List[date] = Field(..., description="Time periods compared")
    index_series: Dict[str, List[Decimal]] = Field(..., description="Index series by geography")
    
    # Statistical comparisons
    correlations: Optional[Dict[str, float]] = Field(None, description="Correlation matrix")
    volatilities: Optional[Dict[str, float]] = Field(None, description="Volatility measures")
    
    # Performance metrics
    cumulative_returns: Optional[Dict[str, float]] = Field(None, description="Cumulative returns")
    annualized_returns: Optional[Dict[str, float]] = Field(None, description="Annualized returns")
    sharpe_ratios: Optional[Dict[str, float]] = Field(None, description="Risk-adjusted returns")


class IndexRevision(TimestampedModel):
    """Record of index value revision."""
    
    geography_id: str = Field(..., description="Geographic unit identifier")
    period: date = Field(..., description="Period revised")
    weighting_scheme: WeightingScheme = Field(..., description="Weighting methodology")
    
    # Revision details
    previous_value: Decimal = Field(..., gt=0, description="Previous index value")
    revised_value: Decimal = Field(..., gt=0, description="Revised index value")
    revision_amount: Decimal = Field(..., description="Revision amount (new - old)")
    revision_percentage: float = Field(..., description="Revision as percentage")
    
    # Revision metadata
    revision_reason: str = Field(..., description="Reason for revision")
    data_changes: Optional[Dict[str, Any]] = Field(None, description="Description of data changes")
    
    # Impact assessment
    affected_periods: Optional[List[date]] = Field(None, description="Other periods affected")
    downstream_impacts: Optional[List[str]] = Field(None, description="Downstream systems affected")
    
    @validator('revision_percentage')
    def calculate_revision_percentage(cls, v, values):
        """Calculate revision percentage from amounts."""
        if 'previous_value' in values and 'revised_value' in values:
            expected = float((values['revised_value'] - values['previous_value']) / values['previous_value'] * 100)
            if abs(v - expected) > 0.01:  # Allow small rounding differences
                raise ValueError("Revision percentage doesn't match calculated value")
        return v


class IndexBenchmark(TimestampedModel):
    """Benchmark comparison for index validation."""
    
    geography_id: str = Field(..., description="Geographic unit identifier")
    our_index_id: str = Field(..., description="Our index identifier")
    benchmark_index_id: str = Field(..., description="Benchmark index identifier")
    
    # Comparison period
    start_period: date = Field(..., description="Comparison start period")
    end_period: date = Field(..., description="Comparison end period")
    
    # Statistical comparisons
    correlation: float = Field(..., ge=-1, le=1, description="Correlation with benchmark")
    mean_absolute_difference: float = Field(..., ge=0, description="Mean absolute difference")
    root_mean_square_error: float = Field(..., ge=0, description="RMSE vs benchmark")
    
    # Tracking measures
    tracking_error: float = Field(..., ge=0, description="Tracking error vs benchmark")
    information_ratio: Optional[float] = Field(None, description="Information ratio")
    
    # Performance comparison
    our_cumulative_return: float = Field(..., description="Our index cumulative return")
    benchmark_cumulative_return: float = Field(..., description="Benchmark cumulative return")
    excess_return: float = Field(..., description="Excess return vs benchmark")
    
    # Quality assessment
    benchmark_quality_score: float = Field(..., ge=0, le=1, description="Benchmark comparison quality")
    confidence_level: float = Field(..., ge=0, le=1, description="Confidence in comparison")
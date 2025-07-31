"""Data validation models for RSAI microservices."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import Field, validator

from .base import TimestampedModel


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationRuleType(str, Enum):
    """Types of validation rules."""
    SCHEMA = "schema"
    RANGE = "range"
    PATTERN = "pattern"
    STATISTICAL = "statistical"
    BUSINESS = "business"
    REFERENTIAL = "referential"


class ValidationRule(TimestampedModel):
    """Definition of a data validation rule."""
    
    name: str = Field(..., description="Unique rule name")
    rule_type: ValidationRuleType = Field(..., description="Type of validation rule")
    description: str = Field(..., description="Human-readable description")
    
    # Rule configuration
    target_columns: List[str] = Field(..., description="Columns to validate")
    parameters: Dict[str, Any] = Field(default={}, description="Rule-specific parameters")
    
    # Rule metadata
    severity: ValidationSeverity = Field(default=ValidationSeverity.ERROR, description="Issue severity")
    category: str = Field(..., description="Rule category (e.g., 'data_quality', 'business_logic')")
    tags: List[str] = Field(default=[], description="Searchable tags")
    
    # Rule status
    is_active: bool = Field(default=True, description="Whether rule is active")
    applies_to_data_types: List[str] = Field(default=[], description="Applicable data types")
    
    @validator('name')
    def validate_rule_name(cls, v):
        """Ensure rule name is valid identifier."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Rule name must contain only alphanumeric characters, hyphens, and underscores")
        return v


class ValidationResult(TimestampedModel):
    """Result of applying a validation rule."""
    
    rule_name: str = Field(..., description="Name of the validation rule")
    rule_type: ValidationRuleType = Field(..., description="Type of validation rule")
    severity: ValidationSeverity = Field(..., description="Issue severity")
    
    # Validation outcome
    is_valid: bool = Field(..., description="Whether validation passed")
    message: str = Field(..., description="Validation result message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional validation details")
    
    # Data context
    record_identifier: Optional[str] = Field(None, description="Identifier of the validated record")
    column_name: Optional[str] = Field(None, description="Column that failed validation")
    invalid_value: Optional[Any] = Field(None, description="Value that failed validation")
    
    # Suggestions
    suggested_fix: Optional[str] = Field(None, description="Suggested fix for the issue")
    auto_fixable: bool = Field(default=False, description="Whether issue can be automatically fixed")


class ValidationJob(TimestampedModel):
    """A validation job processing a dataset."""
    
    job_name: str = Field(..., description="Human-readable job name")
    data_source: str = Field(..., description="Source of the data being validated")
    data_type: str = Field(..., description="Type of data (transactions, properties, etc.)")
    
    # Job configuration
    validation_rules: List[str] = Field(..., description="Names of rules to apply")
    parameters: Dict[str, Any] = Field(default={}, description="Job-specific parameters")
    
    # Job status
    status: str = Field(default="pending", description="Job status")
    progress_percentage: int = Field(default=0, ge=0, le=100, description="Completion percentage")
    
    # Results summary
    total_records: Optional[int] = Field(None, description="Total records processed")
    valid_records: Optional[int] = Field(None, description="Number of valid records")
    invalid_records: Optional[int] = Field(None, description="Number of invalid records")
    
    # Timing
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    
    @validator('valid_records', 'invalid_records')
    def validate_record_counts(cls, v, values):
        """Ensure record counts are consistent."""
        if v is not None and 'total_records' in values and values['total_records'] is not None:
            if v < 0 or v > values['total_records']:
                raise ValueError("Record count cannot be negative or exceed total records")
        return v


class QualityMetric(TimestampedModel):
    """Data quality metric measurement."""
    
    metric_name: str = Field(..., description="Name of the quality metric")
    metric_type: str = Field(..., description="Type of metric (completeness, accuracy, consistency, etc.)")
    
    # Metric values
    value: float = Field(..., description="Metric value")
    target_value: Optional[float] = Field(None, description="Target/expected value")
    threshold_min: Optional[float] = Field(None, description="Minimum acceptable value")
    threshold_max: Optional[float] = Field(None, description="Maximum acceptable value")
    
    # Context
    data_source: str = Field(..., description="Data source for this metric")
    column_name: Optional[str] = Field(None, description="Specific column if applicable")
    time_period: Optional[str] = Field(None, description="Time period for this measurement")
    
    # Status
    is_passing: bool = Field(..., description="Whether metric meets thresholds")
    trend: Optional[str] = Field(None, description="Trend direction (improving, declining, stable)")
    
    @validator('value', 'target_value', 'threshold_min', 'threshold_max')
    def validate_numeric_values(cls, v):
        """Ensure numeric values are valid."""
        if v is not None and (v < 0 or v > 1) and cls.__name__ in ['completeness', 'accuracy']:
            raise ValueError("Quality metrics should typically be between 0 and 1")
        return v


class ValidationReport(TimestampedModel):
    """Comprehensive validation report."""
    
    job_id: str = Field(..., description="Associated validation job ID")
    report_name: str = Field(..., description="Report name")
    data_source: str = Field(..., description="Data source validated")
    
    # Summary statistics
    total_records: int = Field(..., ge=0, description="Total records validated")
    valid_records: int = Field(..., ge=0, description="Valid records count")
    invalid_records: int = Field(..., ge=0, description="Invalid records count")
    
    # Rule results summary
    rules_applied: int = Field(..., ge=0, description="Number of rules applied")
    rules_passed: int = Field(..., ge=0, description="Number of rules that passed")
    rules_failed: int = Field(..., ge=0, description="Number of rules that failed")
    
    # Issue breakdown
    critical_issues: int = Field(default=0, ge=0, description="Critical issues found")
    error_issues: int = Field(default=0, ge=0, description="Error issues found")
    warning_issues: int = Field(default=0, ge=0, description="Warning issues found")
    info_issues: int = Field(default=0, ge=0, description="Info issues found")
    
    # Quality scores
    overall_quality_score: float = Field(..., ge=0, le=1, description="Overall quality score (0-1)")
    completeness_score: float = Field(..., ge=0, le=1, description="Data completeness score")
    accuracy_score: float = Field(..., ge=0, le=1, description="Data accuracy score")
    consistency_score: float = Field(..., ge=0, le=1, description="Data consistency score")
    
    # Detailed results
    validation_results: List[ValidationResult] = Field(default=[], description="Detailed validation results")
    quality_metrics: List[QualityMetric] = Field(default=[], description="Quality metrics")
    
    # Recommendations
    recommendations: List[str] = Field(default=[], description="Improvement recommendations")
    auto_fix_suggestions: List[Dict[str, Any]] = Field(default=[], description="Automatic fix suggestions")
    
    @validator('valid_records', 'invalid_records')
    def validate_record_totals(cls, v, values):
        """Ensure record counts sum correctly."""
        if 'valid_records' in values and 'invalid_records' in values and 'total_records' in values:
            if values['valid_records'] + values['invalid_records'] != values['total_records']:
                raise ValueError("Valid + invalid records must equal total records")
        return v


class ValidationTemplate(TimestampedModel):
    """Template for common validation scenarios."""
    
    template_name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    data_type: str = Field(..., description="Applicable data type")
    
    # Template configuration
    default_rules: List[str] = Field(..., description="Default validation rules")
    parameters: Dict[str, Any] = Field(default={}, description="Default parameters")
    
    # Template metadata
    category: str = Field(..., description="Template category")
    tags: List[str] = Field(default=[], description="Searchable tags")
    is_active: bool = Field(default=True, description="Whether template is active")
    
    # Usage statistics
    usage_count: int = Field(default=0, ge=0, description="Number of times used")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")


class DataProfile(TimestampedModel):
    """Statistical profile of a dataset."""
    
    data_source: str = Field(..., description="Data source identifier")
    table_name: Optional[str] = Field(None, description="Table name if applicable")
    
    # Basic statistics
    row_count: int = Field(..., ge=0, description="Total number of rows")
    column_count: int = Field(..., ge=0, description="Total number of columns")
    
    # Column profiles
    column_profiles: Dict[str, Dict[str, Any]] = Field(
        default={}, 
        description="Statistical profile for each column"
    )
    
    # Data quality summary
    missing_value_percentage: float = Field(..., ge=0, le=100, description="Percentage of missing values")
    duplicate_row_percentage: float = Field(..., ge=0, le=100, description="Percentage of duplicate rows")
    
    # Schema information
    schema_version: Optional[str] = Field(None, description="Schema version if applicable")
    data_types: Dict[str, str] = Field(default={}, description="Data type for each column")
    
    # Profiling metadata
    profiled_at: datetime = Field(default_factory=datetime.utcnow, description="When profiling was done")
    profiling_duration_seconds: float = Field(..., ge=0, description="Time taken to profile")


class ValidationRuleExecution(TimestampedModel):
    """Record of a validation rule execution."""
    
    job_id: str = Field(..., description="Associated validation job")
    rule_name: str = Field(..., description="Validation rule name")
    
    # Execution details
    started_at: datetime = Field(..., description="Rule execution start time")
    completed_at: Optional[datetime] = Field(None, description="Rule execution end time")
    duration_seconds: Optional[float] = Field(None, ge=0, description="Execution duration")
    
    # Results
    records_processed: int = Field(..., ge=0, description="Records processed by this rule")
    records_passed: int = Field(..., ge=0, description="Records that passed this rule")
    records_failed: int = Field(..., ge=0, description="Records that failed this rule")
    
    # Performance
    memory_usage_mb: Optional[float] = Field(None, ge=0, description="Peak memory usage")
    cpu_time_seconds: Optional[float] = Field(None, ge=0, description="CPU time used")
    
    # Status
    execution_status: str = Field(..., description="Execution status (success, failed, timeout)")
    error_message: Optional[str] = Field(None, description="Error message if failed")
"""Common models for RSAI microservices."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import Field

from .base import TimestampedModel


class ServiceStatus(str, Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class JobStatus(str, Enum):
    """Generic job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class PipelineStatus(TimestampedModel):
    """Status of a complete RSAI pipeline execution."""
    
    pipeline_id: str = Field(..., description="Unique pipeline identifier")
    pipeline_name: str = Field(..., description="Human-readable pipeline name")
    
    # Pipeline configuration
    cbsa_id: str = Field(..., description="CBSA being processed")
    parameters: Dict[str, Any] = Field(default={}, description="Pipeline parameters")
    
    # Overall status
    status: JobStatus = Field(default=JobStatus.PENDING, description="Overall pipeline status")
    progress_percentage: int = Field(default=0, ge=0, le=100, description="Overall progress")
    
    # Step status
    ingestion_status: JobStatus = Field(default=JobStatus.PENDING, description="Data ingestion status")
    validation_status: JobStatus = Field(default=JobStatus.PENDING, description="Data validation status")
    geography_status: JobStatus = Field(default=JobStatus.PENDING, description="Geography processing status")
    calculation_status: JobStatus = Field(default=JobStatus.PENDING, description="Index calculation status")
    export_status: JobStatus = Field(default=JobStatus.PENDING, description="Export status")
    
    # Job IDs for tracking
    ingestion_job_id: Optional[str] = Field(None, description="Data ingestion job ID")
    validation_job_id: Optional[str] = Field(None, description="Data validation job ID")
    geography_job_id: Optional[str] = Field(None, description="Geography job ID")
    calculation_job_id: Optional[str] = Field(None, description="Index calculation job ID")
    export_job_id: Optional[str] = Field(None, description="Export job ID")
    
    # Timing
    started_at: Optional[datetime] = Field(None, description="Pipeline start time")
    completed_at: Optional[datetime] = Field(None, description="Pipeline completion time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    
    # Results summary
    total_transactions: Optional[int] = Field(None, description="Total transactions processed")
    total_repeat_pairs: Optional[int] = Field(None, description="Total repeat sale pairs")
    periods_calculated: Optional[int] = Field(None, description="Index periods calculated")
    
    # Error tracking
    error_count: int = Field(default=0, ge=0, description="Number of errors encountered")
    warning_count: int = Field(default=0, ge=0, description="Number of warnings")
    last_error: Optional[str] = Field(None, description="Last error message")


class ServiceHealth(TimestampedModel):
    """Health status of a microservice."""
    
    service_name: str = Field(..., description="Service name")
    service_version: str = Field(..., description="Service version")
    status: ServiceStatus = Field(..., description="Service health status")
    
    # Health metrics
    uptime_seconds: int = Field(..., ge=0, description="Service uptime in seconds")
    cpu_usage_percent: Optional[float] = Field(None, ge=0, le=100, description="CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, ge=0, description="Memory usage in MB")
    
    # Dependencies
    database_healthy: bool = Field(..., description="Database connection health")
    redis_healthy: bool = Field(..., description="Redis connection health")
    external_services: Dict[str, bool] = Field(default={}, description="External service health status")
    
    # Performance metrics
    requests_per_minute: Optional[int] = Field(None, ge=0, description="Requests per minute")
    average_response_time_ms: Optional[float] = Field(None, ge=0, description="Average response time")
    error_rate_percent: Optional[float] = Field(None, ge=0, le=100, description="Error rate percentage")
    
    # Recent issues
    recent_errors: List[str] = Field(default=[], description="Recent error messages")
    alerts: List[str] = Field(default=[], description="Active alerts")


class APIResponse(TimestampedModel):
    """Standard API response wrapper."""
    
    success: bool = Field(description="Whether the request was successful")
    message: str = Field(description="Human-readable message")
    data: Optional[Any] = Field(default=None, description="Response data")
    errors: Optional[List[str]] = Field(default=None, description="List of error messages")
    warnings: Optional[List[str]] = Field(default=None, description="List of warning messages")
    
    # Request tracking
    request_id: Optional[str] = Field(default=None, description="Request correlation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    # Pagination (if applicable)
    pagination: Optional[Dict[str, Any]] = Field(default=None, description="Pagination information")
    
    # Performance metrics
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")


class NotificationEvent(TimestampedModel):
    """Event notification for inter-service communication."""
    
    event_type: str = Field(..., description="Type of event")
    event_source: str = Field(..., description="Service that generated the event")
    event_data: Dict[str, Any] = Field(..., description="Event payload data")
    
    # Event metadata
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")
    priority: str = Field(default="normal", description="Event priority (low, normal, high, critical)")
    
    # Routing
    target_services: Optional[List[str]] = Field(None, description="Target services for this event")
    broadcast: bool = Field(default=False, description="Whether to broadcast to all services")
    
    # Delivery tracking
    delivery_attempts: int = Field(default=0, ge=0, description="Number of delivery attempts")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    next_retry_at: Optional[datetime] = Field(None, description="Next retry timestamp")
    
    # Status
    processed: bool = Field(default=False, description="Whether event has been processed")
    processed_at: Optional[datetime] = Field(None, description="When event was processed")
    processing_errors: List[str] = Field(default=[], description="Processing error messages")


class AuditLog(TimestampedModel):
    """Audit log entry for tracking system activities."""
    
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of resource affected")
    
    # User context
    user_id: Optional[str] = Field(None, description="User who performed action")
    service_name: str = Field(..., description="Service that performed action")
    
    # Action details
    action_details: Dict[str, Any] = Field(default={}, description="Detailed action information")
    previous_values: Optional[Dict[str, Any]] = Field(None, description="Previous values before change")
    new_values: Optional[Dict[str, Any]] = Field(None, description="New values after change")
    
    # Request context
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    
    # Outcome
    success: bool = Field(..., description="Whether action was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Compliance
    retention_days: int = Field(default=2555, description="Days to retain this log entry")  # ~7 years
    sensitive_data: bool = Field(default=False, description="Whether log contains sensitive data")


class SystemConfiguration(TimestampedModel):
    """System configuration setting."""
    
    key: str = Field(..., description="Configuration key")
    value: str = Field(..., description="Configuration value")
    value_type: str = Field(..., description="Value type (string, int, float, bool, json)")
    
    # Metadata
    category: str = Field(..., description="Configuration category")
    description: str = Field(..., description="Human-readable description")
    
    # Validation
    allowed_values: Optional[List[str]] = Field(None, description="Allowed values for this setting")
    min_value: Optional[float] = Field(None, description="Minimum numeric value")
    max_value: Optional[float] = Field(None, description="Maximum numeric value")
    
    # Environment
    environment: str = Field(default="production", description="Environment this config applies to")
    service_name: Optional[str] = Field(None, description="Service this config applies to")
    
    # Change tracking
    last_modified_by: Optional[str] = Field(None, description="Who last modified this setting")
    change_reason: Optional[str] = Field(None, description="Reason for last change")
    
    # Status
    is_active: bool = Field(default=True, description="Whether configuration is active")
    requires_restart: bool = Field(default=False, description="Whether change requires service restart")


class PerformanceMetric(TimestampedModel):
    """Performance metric measurement."""
    
    metric_name: str = Field(..., description="Name of the metric")
    metric_type: str = Field(..., description="Type of metric (counter, gauge, histogram)")
    value: float = Field(..., description="Metric value")
    
    # Context
    service_name: str = Field(..., description="Service that generated this metric")
    endpoint: Optional[str] = Field(None, description="API endpoint if applicable")
    operation: Optional[str] = Field(None, description="Operation being measured")
    
    # Labels/Tags
    labels: Dict[str, str] = Field(default={}, description="Metric labels for grouping")
    
    # Timing
    measurement_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When metric was measured")
    time_window_seconds: Optional[int] = Field(None, description="Time window for this measurement")
    
    # Statistical properties
    min_value: Optional[float] = Field(None, description="Minimum value in time window")
    max_value: Optional[float] = Field(None, description="Maximum value in time window")
    percentile_95: Optional[float] = Field(None, description="95th percentile value")
    percentile_99: Optional[float] = Field(None, description="99th percentile value")


class FeatureFlag(TimestampedModel):
    """Feature flag for controlling system behavior."""
    
    flag_name: str = Field(..., description="Feature flag name")
    description: str = Field(..., description="Description of what this flag controls")
    
    # Flag state
    is_enabled: bool = Field(default=False, description="Whether feature is enabled")
    rollout_percentage: int = Field(default=0, ge=0, le=100, description="Percentage rollout")
    
    # Targeting
    target_services: Optional[List[str]] = Field(None, description="Services this flag applies to")
    target_users: Optional[List[str]] = Field(None, description="Specific users to target")
    target_environments: List[str] = Field(default=["development"], description="Target environments")
    
    # Scheduling
    enabled_at: Optional[datetime] = Field(None, description="When flag was enabled")
    disabled_at: Optional[datetime] = Field(None, description="When flag was disabled")
    auto_disable_at: Optional[datetime] = Field(None, description="When to automatically disable")
    
    # Metadata
    owner: Optional[str] = Field(None, description="Flag owner/maintainer")
    jira_ticket: Optional[str] = Field(None, description="Associated JIRA ticket")
    tags: List[str] = Field(default=[], description="Searchable tags")
"""API routes for Data Validation Service."""

import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.validation_engine import ValidationEngine
from ..db.database import get_db
from ..schemas.validation import (
    ValidationJobResponse,
    ValidationRuleResponse,
    ValidationReportResponse,
    DataQualityMetrics,
    ValidationRuleCreate,
    ValidationJobCreate,
)
from ...shared.models import APIResponse

router = APIRouter(tags=["Data Validation"])


@router.post("/validate", response_model=ValidationJobResponse)
async def validate_data(
    job_request: ValidationJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a comprehensive data validation job.
    
    Validates transaction data against configurable rules including:
    - Schema validation
    - Data type validation
    - Range and constraint validation
    - Statistical outlier detection
    - Business rule validation
    """
    validation_engine = ValidationEngine()
    
    # Create validation job
    job = await validation_engine.create_validation_job(
        db=db,
        job_request=job_request,
    )
    
    # Start validation in background
    background_tasks.add_task(
        validation_engine.run_validation_job,
        job_id=job.id,
        db=db,
    )
    
    return ValidationJobResponse.from_orm(job)


@router.get("/jobs", response_model=List[ValidationJobResponse])
async def list_validation_jobs(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    data_source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List validation jobs with optional filtering."""
    validation_engine = ValidationEngine()
    jobs = await validation_engine.get_validation_jobs(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        data_source=data_source,
    )
    
    return [ValidationJobResponse.from_orm(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=ValidationJobResponse)
async def get_validation_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get details of a specific validation job."""
    validation_engine = ValidationEngine()
    job = await validation_engine.get_validation_job(db=db, job_id=job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Validation job not found")
    
    return ValidationJobResponse.from_orm(job)


@router.get("/jobs/{job_id}/report", response_model=ValidationReportResponse)
async def get_validation_report(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get comprehensive validation report for a job."""
    validation_engine = ValidationEngine()
    report = await validation_engine.get_validation_report(db=db, job_id=job_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Validation report not found")
    
    return report


@router.post("/rules", response_model=ValidationRuleResponse)
async def create_validation_rule(
    rule: ValidationRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new validation rule."""
    validation_engine = ValidationEngine()
    created_rule = await validation_engine.create_validation_rule(db=db, rule=rule)
    
    return ValidationRuleResponse.from_orm(created_rule)


@router.get("/rules", response_model=List[ValidationRuleResponse])
async def list_validation_rules(
    category: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List available validation rules."""
    validation_engine = ValidationEngine()
    rules = await validation_engine.get_validation_rules(
        db=db,
        category=category,
        active_only=active_only,
    )
    
    return [ValidationRuleResponse.from_orm(rule) for rule in rules]


@router.put("/rules/{rule_id}", response_model=ValidationRuleResponse)
async def update_validation_rule(
    rule_id: UUID,
    rule_update: ValidationRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing validation rule."""
    validation_engine = ValidationEngine()
    updated_rule = await validation_engine.update_validation_rule(
        db=db,
        rule_id=rule_id,
        rule_update=rule_update,
    )
    
    if not updated_rule:
        raise HTTPException(status_code=404, detail="Validation rule not found")
    
    return ValidationRuleResponse.from_orm(updated_rule)


@router.delete("/rules/{rule_id}")
async def delete_validation_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a validation rule."""
    validation_engine = ValidationEngine()
    success = await validation_engine.delete_validation_rule(db=db, rule_id=rule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Validation rule not found")
    
    return APIResponse(
        success=True,
        message=f"Validation rule {rule_id} deleted successfully",
    )


@router.post("/quick-validate")
async def quick_validate(
    data: Dict[str, Any],
    rules: Optional[List[str]] = None,
):
    """
    Quick validation of a single data record.
    
    Useful for real-time validation during data entry.
    """
    validation_engine = ValidationEngine()
    result = await validation_engine.quick_validate_record(
        data=data,
        rule_names=rules,
    )
    
    return APIResponse(
        success=result["is_valid"],
        message="Quick validation completed",
        data=result,
    )


@router.get("/metrics/quality", response_model=DataQualityMetrics)
async def get_data_quality_metrics(
    data_source: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get data quality metrics and trends."""
    validation_engine = ValidationEngine()
    metrics = await validation_engine.get_data_quality_metrics(
        db=db,
        data_source=data_source,
        date_from=date_from,
        date_to=date_to,
    )
    
    return metrics


@router.post("/outliers/detect")
async def detect_outliers(
    data_source: str,
    method: str = "iqr",
    threshold: float = 1.5,
    columns: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Detect statistical outliers in transaction data.
    
    Methods:
    - iqr: Interquartile Range
    - zscore: Z-Score
    - isolation_forest: Isolation Forest
    """
    validation_engine = ValidationEngine()
    outliers = await validation_engine.detect_outliers(
        db=db,
        data_source=data_source,
        method=method,
        threshold=threshold,
        columns=columns,
    )
    
    return APIResponse(
        success=True,
        message=f"Outlier detection completed using {method} method",
        data=outliers,
    )


@router.post("/schema/validate")
async def validate_schema(
    schema_definition: Dict[str, Any],
    sample_data: Dict[str, Any],
):
    """
    Validate data against a schema definition.
    
    Useful for testing schema rules before applying to datasets.
    """
    validation_engine = ValidationEngine()
    result = await validation_engine.validate_against_schema(
        schema_definition=schema_definition,
        sample_data=sample_data,
    )
    
    return APIResponse(
        success=result["is_valid"],
        message="Schema validation completed",
        data=result,
    )


@router.get("/statistics/summary")
async def get_validation_statistics(
    data_source: Optional[str] = None,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Get validation statistics and trends."""
    validation_engine = ValidationEngine()
    stats = await validation_engine.get_validation_statistics(
        db=db,
        data_source=data_source,
        days=days,
    )
    
    return APIResponse(
        success=True,
        message="Validation statistics retrieved",
        data=stats,
    )


@router.post("/revalidate/{job_id}")
async def revalidate_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    updated_rules: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
):
    """Rerun validation job with updated rules."""
    validation_engine = ValidationEngine()
    job = await validation_engine.get_validation_job(db=db, job_id=job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Validation job not found")
    
    # Start revalidation in background
    background_tasks.add_task(
        validation_engine.revalidate_job,
        job_id=job_id,
        updated_rules=updated_rules,
        db=db,
    )
    
    return APIResponse(
        success=True,
        message=f"Job {job_id} queued for revalidation",
    )


@router.post("/repair/suggest")
async def suggest_data_repairs(
    job_id: UUID,
    max_suggestions: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Suggest automatic repairs for validation failures.
    
    Provides actionable suggestions for fixing data quality issues.
    """
    validation_engine = ValidationEngine()
    suggestions = await validation_engine.suggest_data_repairs(
        db=db,
        job_id=job_id,
        max_suggestions=max_suggestions,
    )
    
    return APIResponse(
        success=True,
        message="Data repair suggestions generated",
        data=suggestions,
    )


@router.post("/export/{job_id}")
async def export_validation_results(
    job_id: UUID,
    format: str = "csv",
    include_valid_records: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Export validation results in various formats."""
    if format not in ["csv", "json", "excel", "parquet"]:
        raise HTTPException(
            status_code=400,
            detail="Format must be one of: csv, json, excel, parquet"
        )
    
    validation_engine = ValidationEngine()
    export_path = await validation_engine.export_validation_results(
        db=db,
        job_id=job_id,
        format=format,
        include_valid_records=include_valid_records,
    )
    
    return APIResponse(
        success=True,
        message=f"Validation results exported in {format} format",
        data={"export_path": export_path},
    )
"""API routes for Data Ingestion Service."""

import asyncio
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.ingestion import DataIngestionEngine
from ..db.database import get_db
from ..db.models import IngestionJob
from ..schemas.ingestion import (
    IngestionJobResponse,
    IngestionJobCreate,
    TransactionBatchResponse,
    DataSourceInfo,
    IngestionStatistics,
)
from ...shared.models import APIResponse, Transaction, TransactionCreate

router = APIRouter(tags=["Data Ingestion"])


@router.post("/upload", response_model=IngestionJobResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    data_source: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a data file for ingestion.
    
    Supports CSV, Parquet, and Excel files containing real estate transaction data.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_extension = file.filename.lower().split('.')[-1]
    if f".{file_extension}" not in [".csv", ".parquet", ".xlsx"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}"
        )
    
    # Create ingestion job
    ingestion_engine = DataIngestionEngine()
    job = await ingestion_engine.create_ingestion_job(
        db=db,
        filename=file.filename,
        data_source=data_source,
        description=description,
    )
    
    # Process file in background
    background_tasks.add_task(
        ingestion_engine.process_file_upload,
        job_id=job.id,
        file=file,
        db=db,
    )
    
    return IngestionJobResponse.from_orm(job)


@router.post("/batch", response_model=TransactionBatchResponse)
async def ingest_batch(
    transactions: List[TransactionCreate],
    data_source: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a batch of transactions via API.
    
    Limited to 50,000 transactions per request for performance.
    """
    if len(transactions) > 50000:
        raise HTTPException(
            status_code=400,
            detail="Batch size cannot exceed 50,000 transactions"
        )
    
    ingestion_engine = DataIngestionEngine()
    result = await ingestion_engine.process_transaction_batch(
        transactions=transactions,
        data_source=data_source,
        db=db,
    )
    
    return result


@router.get("/jobs", response_model=List[IngestionJobResponse])
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List ingestion jobs with optional filtering."""
    ingestion_engine = DataIngestionEngine()
    jobs = await ingestion_engine.get_jobs(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
    )
    
    return [IngestionJobResponse.from_orm(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get details of a specific ingestion job."""
    ingestion_engine = DataIngestionEngine()
    job = await ingestion_engine.get_job(db=db, job_id=job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return IngestionJobResponse.from_orm(job)


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Cancel a running ingestion job."""
    ingestion_engine = DataIngestionEngine()
    success = await ingestion_engine.cancel_job(db=db, job_id=job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already completed")
    
    return APIResponse(
        success=True,
        message=f"Job {job_id} cancelled successfully",
    )


@router.get("/statistics", response_model=IngestionStatistics)
async def get_statistics(
    data_source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get ingestion statistics."""
    ingestion_engine = DataIngestionEngine()
    stats = await ingestion_engine.get_statistics(db=db, data_source=data_source)
    
    return stats


@router.get("/data-sources", response_model=List[DataSourceInfo])
async def list_data_sources(db: AsyncSession = Depends(get_db)):
    """List all available data sources."""
    ingestion_engine = DataIngestionEngine()
    sources = await ingestion_engine.get_data_sources(db=db)
    
    return sources


@router.post("/validate-schema")
async def validate_schema(file: UploadFile = File(...)):
    """
    Validate file schema without ingesting data.
    
    Returns schema information and validation results.
    """
    ingestion_engine = DataIngestionEngine()
    result = await ingestion_engine.validate_file_schema(file)
    
    return APIResponse(
        success=True,
        message="Schema validation completed",
        data=result,
    )


@router.post("/preview")
async def preview_data(
    file: UploadFile = File(...),
    rows: int = 10,
):
    """
    Preview first N rows of uploaded file.
    
    Useful for data exploration before full ingestion.
    """
    if rows > 1000:
        raise HTTPException(
            status_code=400,
            detail="Preview limited to 1000 rows maximum"
        )
    
    ingestion_engine = DataIngestionEngine()
    preview = await ingestion_engine.preview_file_data(file, rows)
    
    return APIResponse(
        success=True,
        message=f"Preview of first {rows} rows",
        data=preview,
    )


@router.post("/reprocess/{job_id}")
async def reprocess_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Reprocess a failed or completed ingestion job."""
    ingestion_engine = DataIngestionEngine()
    job = await ingestion_engine.get_job(db=db, job_id=job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status == "processing":
        raise HTTPException(
            status_code=400,
            detail="Job is currently processing"
        )
    
    # Start reprocessing in background
    background_tasks.add_task(
        ingestion_engine.reprocess_job,
        job_id=job_id,
        db=db,
    )
    
    return APIResponse(
        success=True,
        message=f"Job {job_id} queued for reprocessing",
    )


@router.get("/transactions/count")
async def get_transaction_count(
    data_source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get total transaction count by data source."""
    ingestion_engine = DataIngestionEngine()
    count = await ingestion_engine.get_transaction_count(
        db=db,
        data_source=data_source,
    )
    
    return APIResponse(
        success=True,
        message="Transaction count retrieved",
        data={"count": count, "data_source": data_source},
    )


@router.post("/cleanup")
async def cleanup_old_data(
    days_old: int = 30,
    dry_run: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Clean up old ingestion data.
    
    Set dry_run=False to actually delete data.
    """
    if days_old < 1:
        raise HTTPException(
            status_code=400,
            detail="days_old must be at least 1"
        )
    
    ingestion_engine = DataIngestionEngine()
    result = await ingestion_engine.cleanup_old_data(
        db=db,
        days_old=days_old,
        dry_run=dry_run,
    )
    
    return APIResponse(
        success=True,
        message=f"Cleanup {'simulation' if dry_run else 'completed'}",
        data=result,
    )
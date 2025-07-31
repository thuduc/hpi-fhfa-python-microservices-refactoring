"""API routes for Export Service."""

import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Response
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from ..core.export_engine import ExportEngine
from ..core.visualization_engine import VisualizationEngine
from ..core.report_generator import ReportGenerator
from ..db.database import get_db
from ..schemas.export import (
    ExportJobResponse,
    VisualizationResponse,
    ReportResponse,
    ExportTemplateResponse,
)
from ...shared.models import APIResponse

router = APIRouter(tags=["Export"])


@router.post("/data", response_model=ExportJobResponse)
async def export_data(
    data_type: str,
    format: str,
    filters: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Export data in various formats.
    
    Data types:
    - transactions: Raw transaction data
    - indices: Calculated house price indices
    - supertracts: Geographic supertract definitions
    - validation_results: Data validation reports
    
    Formats: csv, excel, parquet, json
    """
    if data_type not in ["transactions", "indices", "supertracts", "validation_results"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid data type"
        )
    
    if format not in ["csv", "excel", "parquet", "json"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid format"
        )
    
    export_engine = ExportEngine()
    
    # Create export job
    job = await export_engine.create_export_job(
        db=db,
        data_type=data_type,
        format=format,
        filters=filters or {},
    )
    
    # Start export in background
    background_tasks.add_task(
        export_engine.run_data_export,
        job_id=job.id,
        db=db,
    )
    
    return ExportJobResponse.from_orm(job)


@router.get("/jobs", response_model=List[ExportJobResponse])
async def list_export_jobs(
    skip: int = 0,
    limit: int = 100,
    data_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List export jobs with optional filtering."""
    export_engine = ExportEngine()
    jobs = await export_engine.get_export_jobs(
        db=db,
        skip=skip,
        limit=limit,
        data_type=data_type,
        status=status,
    )
    
    return [ExportJobResponse.from_orm(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=ExportJobResponse)
async def get_export_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get details of a specific export job."""
    export_engine = ExportEngine()
    job = await export_engine.get_export_job(db=db, job_id=job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    return ExportJobResponse.from_orm(job)


@router.get("/jobs/{job_id}/download")
async def download_export(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Download the exported file."""
    export_engine = ExportEngine()
    file_path = await export_engine.get_export_file_path(db=db, job_id=job_id)
    
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Export file not found or job not completed"
        )
    
    return FileResponse(
        path=file_path,
        filename=f"export_{job_id}.{file_path.split('.')[-1]}",
        media_type='application/octet-stream'
    )


@router.post("/visualizations/create", response_model=VisualizationResponse)
async def create_visualization(
    chart_type: str,
    data_source: str,
    parameters: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Create data visualizations.
    
    Chart types:
    - line: Time series line chart
    - bar: Bar chart for comparisons
    - scatter: Scatter plot for correlations
    - heatmap: Geographic heatmap
    - histogram: Distribution histogram
    - boxplot: Statistical box plot
    """
    valid_chart_types = ["line", "bar", "scatter", "heatmap", "histogram", "boxplot"]
    if chart_type not in valid_chart_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid chart type. Must be one of: {valid_chart_types}"
        )
    
    viz_engine = VisualizationEngine()
    
    # Create visualization job
    job = await viz_engine.create_visualization_job(
        db=db,
        chart_type=chart_type,
        data_source=data_source,
        parameters=parameters,
    )
    
    # Start visualization creation in background
    background_tasks.add_task(
        viz_engine.create_visualization,
        job_id=job.id,
        db=db,
    )
    
    return VisualizationResponse.from_orm(job)


@router.get("/visualizations", response_model=List[VisualizationResponse])
async def list_visualizations(
    skip: int = 0,
    limit: int = 100,
    chart_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List created visualizations."""
    viz_engine = VisualizationEngine()
    visualizations = await viz_engine.get_visualizations(
        db=db,
        skip=skip,
        limit=limit,
        chart_type=chart_type,
    )
    
    return [VisualizationResponse.from_orm(viz) for viz in visualizations]


@router.get("/visualizations/{viz_id}")
async def get_visualization(viz_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific visualization file."""
    viz_engine = VisualizationEngine()
    file_path = await viz_engine.get_visualization_path(db=db, viz_id=viz_id)
    
    if not file_path:
        raise HTTPException(status_code=404, detail="Visualization not found")
    
    return FileResponse(
        path=file_path,
        filename=f"visualization_{viz_id}.png",
        media_type='image/png'
    )


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(
    report_type: str,
    template: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate comprehensive reports.
    
    Report types:
    - summary: Executive summary report
    - detailed: Detailed analysis report
    - validation: Data validation report
    - methodology: Methodology documentation
    - custom: Custom report from template
    """
    valid_report_types = ["summary", "detailed", "validation", "methodology", "custom"]
    if report_type not in valid_report_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report type. Must be one of: {valid_report_types}"
        )
    
    report_generator = ReportGenerator()
    
    # Create report generation job
    job = await report_generator.create_report_job(
        db=db,
        report_type=report_type,
        template=template,
        parameters=parameters or {},
    )
    
    # Start report generation in background
    background_tasks.add_task(
        report_generator.generate_report,
        job_id=job.id,
        db=db,
    )
    
    return ReportResponse.from_orm(job)


@router.get("/reports", response_model=List[ReportResponse])
async def list_reports(
    skip: int = 0,
    limit: int = 100,
    report_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List generated reports."""
    report_generator = ReportGenerator()
    reports = await report_generator.get_reports(
        db=db,
        skip=skip,
        limit=limit,
        report_type=report_type,
    )
    
    return [ReportResponse.from_orm(report) for report in reports]


@router.get("/reports/{report_id}/download")
async def download_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    """Download a generated report."""
    report_generator = ReportGenerator()
    file_path = await report_generator.get_report_path(db=db, report_id=report_id)
    
    if not file_path:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        path=file_path,
        filename=f"report_{report_id}.pdf",
        media_type='application/pdf'
    )


@router.post("/templates/create", response_model=ExportTemplateResponse)
async def create_export_template(
    name: str,
    template_type: str,
    configuration: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """Create reusable export template."""
    export_engine = ExportEngine()
    template = await export_engine.create_export_template(
        db=db,
        name=name,
        template_type=template_type,
        configuration=configuration,
    )
    
    return ExportTemplateResponse.from_orm(template)


@router.get("/templates", response_model=List[ExportTemplateResponse])
async def list_export_templates(
    template_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List available export templates."""
    export_engine = ExportEngine()
    templates = await export_engine.get_export_templates(
        db=db,
        template_type=template_type,
    )
    
    return [ExportTemplateResponse.from_orm(template) for template in templates]


@router.post("/templates/{template_id}/apply", response_model=ExportJobResponse)
async def apply_export_template(
    template_id: UUID,
    override_parameters: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Apply an export template to create a new export job."""
    export_engine = ExportEngine()
    
    # Create export job from template
    job = await export_engine.apply_export_template(
        db=db,
        template_id=template_id,
        override_parameters=override_parameters or {},
    )
    
    # Start export in background
    background_tasks.add_task(
        export_engine.run_data_export,
        job_id=job.id,
        db=db,
    )
    
    return ExportJobResponse.from_orm(job)


@router.get("/stream/{data_type}")
async def stream_data(
    data_type: str,
    format: str = "json",
    filters: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Stream large datasets for real-time processing.
    
    Useful for large exports that don't fit in memory.
    """
    if data_type not in ["transactions", "indices", "validation_results"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid data type"
        )
    
    export_engine = ExportEngine()
    
    # Create streaming response
    stream = await export_engine.create_data_stream(
        data_type=data_type,
        format=format,
        filters=filters,
        db=db,
    )
    
    # Set appropriate content type
    media_type = {
        "json": "application/json",
        "csv": "text/csv",
        "parquet": "application/octet-stream",
    }.get(format, "application/octet-stream")
    
    return StreamingResponse(
        stream,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=stream.{format}"}
    )


@router.post("/dashboard/create")
async def create_dashboard(
    name: str,
    components: List[Dict[str, Any]],
    layout: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Create interactive dashboard with multiple visualizations.
    
    Components can include charts, tables, maps, and KPIs.
    """
    viz_engine = VisualizationEngine()
    
    # Create dashboard creation job
    job = await viz_engine.create_dashboard_job(
        db=db,
        name=name,
        components=components,
        layout=layout,
    )
    
    # Start dashboard creation in background
    background_tasks.add_task(
        viz_engine.create_dashboard,
        job_id=job.id,
        db=db,
    )
    
    return APIResponse(
        success=True,
        message=f"Dashboard '{name}' creation started",
        data={"job_id": job.id},
    )


@router.get("/formats/supported")
async def get_supported_formats():
    """Get list of supported export formats and their capabilities."""
    return APIResponse(
        success=True,
        message="Supported export formats",
        data={
            "data_formats": {
                "csv": {
                    "description": "Comma-separated values",
                    "supports_streaming": True,
                    "max_size_mb": 1000,
                },
                "excel": {
                    "description": "Microsoft Excel format",
                    "supports_streaming": False,
                    "max_size_mb": 100,
                },
                "parquet": {
                    "description": "Apache Parquet columnar format",
                    "supports_streaming": True,
                    "max_size_mb": 10000,
                },
                "json": {
                    "description": "JavaScript Object Notation",
                    "supports_streaming": True,
                    "max_size_mb": 500,
                },
            },
            "visualization_formats": ["png", "svg", "pdf", "html"],
            "report_formats": ["pdf", "html", "docx"],
        },
    )


@router.post("/cleanup")
async def cleanup_old_exports(
    days_old: int = 7,
    dry_run: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Clean up old export files and jobs."""
    if days_old < 1:
        raise HTTPException(
            status_code=400,
            detail="days_old must be at least 1"
        )
    
    export_engine = ExportEngine()
    result = await export_engine.cleanup_old_exports(
        db=db,
        days_old=days_old,
        dry_run=dry_run,
    )
    
    return APIResponse(
        success=True,
        message=f"Cleanup {'simulation' if dry_run else 'completed'}",
        data=result,
    )


@router.get("/statistics")
async def get_export_statistics(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Get export service usage statistics."""
    export_engine = ExportEngine()
    stats = await export_engine.get_export_statistics(
        db=db,
        days=days,
    )
    
    return APIResponse(
        success=True,
        message="Export statistics retrieved",
        data=stats,
    )
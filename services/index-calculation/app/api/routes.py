"""API routes for Index Calculation Service."""

import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.index_engine import IndexCalculationEngine
from ..core.bmn_regression import BMNRegressionEngine
from ..core.weight_calculator import WeightCalculator
from ..db.database import get_db
from ..schemas.index import (
    IndexCalculationJobResponse,
    BMNRegressionResponse,
    WeightCalculationResponse,
    IndexTimeSeriesResponse,
    IndexParametersResponse,
)
from ...shared.models import APIResponse

router = APIRouter(tags=["Index Calculation"])


@router.post("/calculate", response_model=IndexCalculationJobResponse)
async def calculate_indices(
    cbsa_id: str,
    weighting_scheme: str = "bmn",
    base_period: Optional[str] = None,
    frequency: str = "monthly",
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate house price indices using repeat sales methodology.
    
    Weighting schemes:
    - equal: Equal weighting for all repeat sales pairs
    - value: Value-weighted by transaction amounts
    - case_shiller: Case-Shiller weighting methodology
    - bmn: Bailey-Muth-Nourse regression weighting
    
    Frequencies: monthly, quarterly, annual
    """
    if weighting_scheme not in ["equal", "value", "case_shiller", "bmn"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid weighting scheme"
        )
    
    if frequency not in ["monthly", "quarterly", "annual"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid frequency"
        )
    
    index_engine = IndexCalculationEngine()
    
    # Create index calculation job
    job = await index_engine.create_calculation_job(
        db=db,
        cbsa_id=cbsa_id,
        weighting_scheme=weighting_scheme,
        base_period=base_period,
        frequency=frequency,
    )
    
    # Start calculation in background
    background_tasks.add_task(
        index_engine.run_index_calculation,
        job_id=job.id,
        db=db,
    )
    
    return IndexCalculationJobResponse.from_orm(job)


@router.get("/jobs", response_model=List[IndexCalculationJobResponse])
async def list_calculation_jobs(
    skip: int = 0,
    limit: int = 100,
    cbsa_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List index calculation jobs."""
    index_engine = IndexCalculationEngine()
    jobs = await index_engine.get_calculation_jobs(
        db=db,
        skip=skip,
        limit=limit,
        cbsa_id=cbsa_id,
        status=status,
    )
    
    return [IndexCalculationJobResponse.from_orm(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=IndexCalculationJobResponse)
async def get_calculation_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get details of a specific index calculation job."""
    index_engine = IndexCalculationEngine()
    job = await index_engine.get_calculation_job(db=db, job_id=job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Calculation job not found")
    
    return IndexCalculationJobResponse.from_orm(job)


@router.post("/bmn/regression", response_model=BMNRegressionResponse)
async def run_bmn_regression(
    supertract_id: str,
    time_periods: List[str],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Run Bailey-Muth-Nourse regression for a supertract.
    
    Estimates time-dummy coefficients for house price appreciation.
    """
    bmn_engine = BMNRegressionEngine()
    
    # Create BMN regression job
    job = await bmn_engine.create_bmn_job(
        db=db,
        supertract_id=supertract_id,
        time_periods=time_periods,
    )
    
    # Start regression in background
    background_tasks.add_task(
        bmn_engine.run_bmn_regression,
        job_id=job.id,
        db=db,
    )
    
    return BMNRegressionResponse.from_orm(job)


@router.get("/bmn/results/{supertract_id}")
async def get_bmn_results(
    supertract_id: str,
    period_from: Optional[str] = None,
    period_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get BMN regression results for a supertract."""
    bmn_engine = BMNRegressionEngine()
    results = await bmn_engine.get_bmn_results(
        db=db,
        supertract_id=supertract_id,
        period_from=period_from,
        period_to=period_to,
    )
    
    return APIResponse(
        success=True,
        message="BMN regression results retrieved",
        data=results,
    )


@router.post("/weights/calculate", response_model=WeightCalculationResponse)
async def calculate_weights(
    cbsa_id: str,
    scheme: str = "case_shiller",
    parameters: Optional[Dict[str, float]] = None,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate weights for repeat sales pairs.
    
    Schemes:
    - equal: Equal weights (1.0 for all pairs)
    - value: Value-weighted by average transaction price
    - case_shiller: Case-Shiller variance weighting
    - bmn: BMN regression-based weighting
    """
    weight_calculator = WeightCalculator()
    
    # Create weight calculation job
    job = await weight_calculator.create_weight_job(
        db=db,
        cbsa_id=cbsa_id,
        scheme=scheme,
        parameters=parameters or {},
    )
    
    # Start calculation in background
    background_tasks.add_task(
        weight_calculator.calculate_weights,
        job_id=job.id,
        db=db,
    )
    
    return WeightCalculationResponse.from_orm(job)


@router.get("/weights/{cbsa_id}")
async def get_weights(
    cbsa_id: str,
    scheme: str = "case_shiller",
    limit: int = 1000,
    db: AsyncSession = Depends(get_db),
):
    """Get calculated weights for repeat sales pairs."""
    weight_calculator = WeightCalculator()
    weights = await weight_calculator.get_weights(
        db=db,
        cbsa_id=cbsa_id,
        scheme=scheme,
        limit=limit,
    )
    
    return APIResponse(
        success=True,
        message=f"Retrieved {len(weights)} weights for {scheme} scheme",
        data=weights,
    )


@router.get("/indices/{cbsa_id}/timeseries", response_model=IndexTimeSeriesResponse)
async def get_index_timeseries(
    cbsa_id: str,
    weighting_scheme: str = "bmn",
    frequency: str = "monthly",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get time series of house price indices for a CBSA."""
    index_engine = IndexCalculationEngine()
    timeseries = await index_engine.get_index_timeseries(
        db=db,
        cbsa_id=cbsa_id,
        weighting_scheme=weighting_scheme,
        frequency=frequency,
        date_from=date_from,
        date_to=date_to,
    )
    
    return IndexTimeSeriesResponse(**timeseries)


@router.get("/indices/{cbsa_id}/latest")
async def get_latest_index(
    cbsa_id: str,
    weighting_scheme: str = "bmn",
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent index value for a CBSA."""
    index_engine = IndexCalculationEngine()
    latest = await index_engine.get_latest_index(
        db=db,
        cbsa_id=cbsa_id,
        weighting_scheme=weighting_scheme,
    )
    
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No index data found for this CBSA"
        )
    
    return APIResponse(
        success=True,
        message="Latest index value retrieved",
        data=latest,
    )


@router.get("/indices/compare")
async def compare_indices(
    cbsa_ids: List[str] = Query(...),
    weighting_scheme: str = "bmn",
    period: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Compare index values across multiple CBSAs."""
    if len(cbsa_ids) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 CBSAs allowed for comparison"
        )
    
    index_engine = IndexCalculationEngine()
    comparison = await index_engine.compare_indices(
        db=db,
        cbsa_ids=cbsa_ids,
        weighting_scheme=weighting_scheme,
        period=period,
    )
    
    return APIResponse(
        success=True,
        message=f"Index comparison for {len(cbsa_ids)} CBSAs",
        data=comparison,
    )


@router.post("/indices/rebase")
async def rebase_indices(
    cbsa_id: str,
    new_base_period: str,
    new_base_value: float = 100.0,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Rebase index series to a new base period and value.
    
    Adjusts all index values proportionally to set the specified
    period to the new base value.
    """
    index_engine = IndexCalculationEngine()
    
    # Start rebasing in background
    background_tasks.add_task(
        index_engine.rebase_indices,
        cbsa_id=cbsa_id,
        new_base_period=new_base_period,
        new_base_value=new_base_value,
        db=db,
    )
    
    return APIResponse(
        success=True,
        message=f"Index rebasing started for CBSA {cbsa_id}",
    )


@router.get("/parameters/optimal", response_model=IndexParametersResponse)
async def get_optimal_parameters(
    cbsa_id: str,
    weighting_scheme: str = "bmn",
    db: AsyncSession = Depends(get_db),
):
    """Get optimal parameters for index calculation based on data characteristics."""
    index_engine = IndexCalculationEngine()
    parameters = await index_engine.get_optimal_parameters(
        db=db,
        cbsa_id=cbsa_id,
        weighting_scheme=weighting_scheme,
    )
    
    return IndexParametersResponse(**parameters)


@router.post("/validate/methodology")
async def validate_methodology(
    cbsa_id: str,
    test_periods: List[str],
    validation_method: str = "out_of_sample",
    db: AsyncSession = Depends(get_db),
):
    """
    Validate index calculation methodology.
    
    Methods:
    - out_of_sample: Hold out recent periods for validation
    - cross_validation: K-fold cross validation
    - bootstrap: Bootstrap resampling validation
    """
    if validation_method not in ["out_of_sample", "cross_validation", "bootstrap"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid validation method"
        )
    
    index_engine = IndexCalculationEngine()
    validation_results = await index_engine.validate_methodology(
        db=db,
        cbsa_id=cbsa_id,
        test_periods=test_periods,
        validation_method=validation_method,
    )
    
    return APIResponse(
        success=True,
        message="Methodology validation completed",
        data=validation_results,
    )


@router.get("/diagnostics/{job_id}")
async def get_calculation_diagnostics(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get diagnostic information for an index calculation job."""
    index_engine = IndexCalculationEngine()
    diagnostics = await index_engine.get_calculation_diagnostics(
        db=db,
        job_id=job_id,
    )
    
    if not diagnostics:
        raise HTTPException(
            status_code=404,
            detail="Diagnostics not found for this job"
        )
    
    return APIResponse(
        success=True,
        message="Calculation diagnostics retrieved",
        data=diagnostics,
    )


@router.post("/batch/calculate")
async def batch_calculate_indices(
    cbsa_ids: List[str],
    weighting_scheme: str = "bmn",
    frequency: str = "monthly",
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate indices for multiple CBSAs in batch.
    
    Efficient for processing large numbers of metropolitan areas.
    """
    if len(cbsa_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 CBSAs allowed per batch"
        )
    
    index_engine = IndexCalculationEngine()
    
    # Start batch calculation in background
    background_tasks.add_task(
        index_engine.batch_calculate_indices,
        cbsa_ids=cbsa_ids,
        weighting_scheme=weighting_scheme,
        frequency=frequency,
        db=db,
    )
    
    return APIResponse(
        success=True,
        message=f"Batch calculation started for {len(cbsa_ids)} CBSAs",
    )


@router.get("/statistics/performance")
async def get_performance_statistics(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Get performance statistics for index calculations."""
    index_engine = IndexCalculationEngine()
    stats = await index_engine.get_performance_statistics(
        db=db,
        days=days,
    )
    
    return APIResponse(
        success=True,
        message="Performance statistics retrieved",
        data=stats,
    )
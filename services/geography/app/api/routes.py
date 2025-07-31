"""API routes for Geography Service."""

import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.geography_engine import GeographyEngine
from ..core.supertract_generator import SupertractGenerator
from ..core.distance_calculator import DistanceCalculator
from ..db.database import get_db
from ..schemas.geography import (
    SupertractJobResponse,
    DistanceCalculationResponse,
    GeographicUnitResponse,
    SupertractDefinitionResponse,
    ClusteringParametersResponse,
)
from ...shared.models import APIResponse

router = APIRouter(tags=["Geography"])


@router.post("/supertracts/generate", response_model=SupertractJobResponse)
async def generate_supertracts(
    cbsa_id: str,
    min_observations: int = 40,
    algorithm: str = "hierarchical",
    max_distance_km: float = 50.0,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate supertracts for a CBSA using dynamic clustering.
    
    Algorithms available:
    - hierarchical: Hierarchical clustering based on distance and observations
    - kmeans: K-means clustering with geographic constraints
    - hdbscan: Density-based clustering for irregular shapes
    """
    geography_engine = GeographyEngine()
    
    # Create supertract generation job
    job = await geography_engine.create_supertract_job(
        db=db,
        cbsa_id=cbsa_id,
        min_observations=min_observations,
        algorithm=algorithm,
        max_distance_km=max_distance_km,
    )
    
    # Start generation in background
    background_tasks.add_task(
        geography_engine.run_supertract_generation,
        job_id=job.id,
        db=db,
    )
    
    return SupertractJobResponse.from_orm(job)


@router.get("/supertracts/jobs", response_model=List[SupertractJobResponse])
async def list_supertract_jobs(
    skip: int = 0,
    limit: int = 100,
    cbsa_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List supertract generation jobs."""
    geography_engine = GeographyEngine()
    jobs = await geography_engine.get_supertract_jobs(
        db=db,
        skip=skip,
        limit=limit,
        cbsa_id=cbsa_id,
        status=status,
    )
    
    return [SupertractJobResponse.from_orm(job) for job in jobs]


@router.get("/supertracts/jobs/{job_id}", response_model=SupertractJobResponse)
async def get_supertract_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get details of a specific supertract generation job."""
    geography_engine = GeographyEngine()
    job = await geography_engine.get_supertract_job(db=db, job_id=job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Supertract job not found")
    
    return SupertractJobResponse.from_orm(job)


@router.get("/supertracts/{cbsa_id}", response_model=List[SupertractDefinitionResponse])
async def get_supertracts_by_cbsa(
    cbsa_id: str,
    include_tracts: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Get all supertracts for a CBSA."""
    geography_engine = GeographyEngine()
    supertracts = await geography_engine.get_supertracts_by_cbsa(
        db=db,
        cbsa_id=cbsa_id,
        include_tracts=include_tracts,
    )
    
    return [SupertractDefinitionResponse.from_orm(st) for st in supertracts]


@router.post("/distances/calculate", response_model=DistanceCalculationResponse)
async def calculate_distances(
    tract_ids: List[str],
    method: str = "great_circle",
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate distance matrix between census tracts.
    
    Methods:
    - great_circle: Great circle distance (spherical)
    - euclidean: Euclidean distance (planar approximation)
    - haversine: Haversine formula (spherical)
    """
    if len(tract_ids) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Maximum 1000 tracts allowed per calculation"
        )
    
    distance_calculator = DistanceCalculator()
    
    # Create distance calculation job
    job = await distance_calculator.create_distance_job(
        db=db,
        tract_ids=tract_ids,
        method=method,
    )
    
    # Start calculation in background
    background_tasks.add_task(
        distance_calculator.calculate_distance_matrix,
        job_id=job.id,
        db=db,
    )
    
    return DistanceCalculationResponse.from_orm(job)


@router.get("/distances/{tract_id_1}/{tract_id_2}")
async def get_distance_between_tracts(
    tract_id_1: str,
    tract_id_2: str,
    method: str = "great_circle",
    db: AsyncSession = Depends(get_db),
):
    """Get distance between two specific census tracts."""
    distance_calculator = DistanceCalculator()
    distance = await distance_calculator.get_tract_distance(
        db=db,
        tract_id_1=tract_id_1,
        tract_id_2=tract_id_2,
        method=method,
    )
    
    if distance is None:
        raise HTTPException(
            status_code=404,
            detail="Distance not found or tracts invalid"
        )
    
    return APIResponse(
        success=True,
        message="Distance calculated",
        data={
            "tract_id_1": tract_id_1,
            "tract_id_2": tract_id_2,
            "distance_km": distance,
            "method": method,
        },
    )


@router.get("/tracts/{tract_id}/neighbors")
async def get_neighboring_tracts(
    tract_id: str,
    max_distance_km: float = 10.0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get neighboring census tracts within specified distance."""
    geography_engine = GeographyEngine()
    neighbors = await geography_engine.get_neighboring_tracts(
        db=db,
        tract_id=tract_id,
        max_distance_km=max_distance_km,
        limit=limit,
    )
    
    return APIResponse(
        success=True,
        message=f"Found {len(neighbors)} neighboring tracts",
        data=neighbors,
    )


@router.get("/tracts", response_model=List[GeographicUnitResponse])
async def list_census_tracts(
    cbsa_id: Optional[str] = None,
    county_fips: Optional[str] = None,
    state_code: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000,
    db: AsyncSession = Depends(get_db),
):
    """List census tracts with optional filtering."""
    geography_engine = GeographyEngine()
    tracts = await geography_engine.get_census_tracts(
        db=db,
        cbsa_id=cbsa_id,
        county_fips=county_fips,
        state_code=state_code,
        skip=skip,
        limit=limit,
    )
    
    return [GeographicUnitResponse.from_orm(tract) for tract in tracts]


@router.get("/tracts/{tract_id}", response_model=GeographicUnitResponse)
async def get_census_tract(tract_id: str, db: AsyncSession = Depends(get_db)):
    """Get details of a specific census tract."""
    geography_engine = GeographyEngine()
    tract = await geography_engine.get_census_tract(db=db, tract_id=tract_id)
    
    if not tract:
        raise HTTPException(status_code=404, detail="Census tract not found")
    
    return GeographicUnitResponse.from_orm(tract)


@router.post("/tracts/bulk-load")
async def bulk_load_census_tracts(
    file_url: str,
    format: str = "geojson",
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk load census tract data from external source.
    
    Supports GeoJSON, Shapefile, and CSV formats.
    """
    if format not in ["geojson", "shapefile", "csv"]:
        raise HTTPException(
            status_code=400,
            detail="Format must be one of: geojson, shapefile, csv"
        )
    
    geography_engine = GeographyEngine()
    
    # Start bulk load in background
    background_tasks.add_task(
        geography_engine.bulk_load_tracts,
        file_url=file_url,
        format=format,
        db=db,
    )
    
    return APIResponse(
        success=True,
        message=f"Bulk load started for {format} file: {file_url}",
    )


@router.post("/clustering/optimize")
async def optimize_clustering_parameters(
    cbsa_id: str,
    target_min_observations: int = 40,
    algorithms: List[str] = Query(default=["hierarchical", "kmeans"]),
    db: AsyncSession = Depends(get_db),
):
    """
    Optimize clustering parameters for supertract generation.
    
    Tests different parameter combinations to find optimal settings.
    """
    geography_engine = GeographyEngine()
    optimization_results = await geography_engine.optimize_clustering_parameters(
        db=db,
        cbsa_id=cbsa_id,
        target_min_observations=target_min_observations,
        algorithms=algorithms,
    )
    
    return APIResponse(
        success=True,
        message="Clustering parameter optimization completed",
        data=optimization_results,
    )


@router.get("/clustering/parameters", response_model=ClusteringParametersResponse)
async def get_clustering_parameters(
    cbsa_id: str,
    algorithm: str = "hierarchical",
    db: AsyncSession = Depends(get_db),
):
    """Get recommended clustering parameters for a CBSA."""
    geography_engine = GeographyEngine()
    parameters = await geography_engine.get_clustering_parameters(
        db=db,
        cbsa_id=cbsa_id,
        algorithm=algorithm,
    )
    
    return ClusteringParametersResponse(**parameters)


@router.post("/geocode")
async def geocode_address(
    address: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
):
    """
    Geocode an address to latitude/longitude coordinates.
    
    Uses external geocoding services for address resolution.
    """
    geography_engine = GeographyEngine()
    result = await geography_engine.geocode_address(
        address=address,
        city=city,
        state=state,
        zip_code=zip_code,
    )
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Address could not be geocoded"
        )
    
    return APIResponse(
        success=True,
        message="Address geocoded successfully",
        data=result,
    )


@router.post("/reverse-geocode")
async def reverse_geocode(
    latitude: float,
    longitude: float,
    include_demographics: bool = False,
):
    """
    Reverse geocode coordinates to address and geographic units.
    
    Returns census tract, county, and other geographic identifiers.
    """
    if not (-90 <= latitude <= 90):
        raise HTTPException(
            status_code=400,
            detail="Latitude must be between -90 and 90"
        )
    
    if not (-180 <= longitude <= 180):
        raise HTTPException(
            status_code=400,
            detail="Longitude must be between -180 and 180"
        )
    
    geography_engine = GeographyEngine()
    result = await geography_engine.reverse_geocode(
        latitude=latitude,
        longitude=longitude,
        include_demographics=include_demographics,
    )
    
    return APIResponse(
        success=True,
        message="Coordinates reverse geocoded successfully",
        data=result,
    )


@router.get("/statistics/coverage")
async def get_geographic_coverage(
    data_source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get geographic coverage statistics for transaction data."""
    geography_engine = GeographyEngine()
    coverage = await geography_engine.get_geographic_coverage(
        db=db,
        data_source=data_source,
    )
    
    return APIResponse(
        success=True,
        message="Geographic coverage statistics retrieved",
        data=coverage,
    )


@router.post("/boundaries/export")
async def export_geographic_boundaries(
    cbsa_id: str,
    level: str = "tract",
    format: str = "geojson",
    include_supertracts: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Export geographic boundaries in various formats.
    
    Levels: tract, county, cbsa, supertract
    Formats: geojson, shapefile, kml
    """
    if level not in ["tract", "county", "cbsa", "supertract"]:
        raise HTTPException(
            status_code=400,
            detail="Level must be one of: tract, county, cbsa, supertract"
        )
    
    if format not in ["geojson", "shapefile", "kml"]:
        raise HTTPException(
            status_code=400,
            detail="Format must be one of: geojson, shapefile, kml"
        )
    
    geography_engine = GeographyEngine()
    export_path = await geography_engine.export_boundaries(
        db=db,
        cbsa_id=cbsa_id,
        level=level,
        format=format,
        include_supertracts=include_supertracts,
    )
    
    return APIResponse(
        success=True,
        message=f"Geographic boundaries exported in {format} format",
        data={"export_path": export_path},
    )
# Migration Guide: Monolith to Microservices

## Overview
This guide explains how to migrate from the monolithic RSAI implementation to the new microservices architecture while maintaining data integrity and computational accuracy.

## Architecture Comparison

### Before: Monolithic Structure
```
impl-pandas/
├── rsai/src/
│   ├── main.py              # Pipeline orchestration
│   ├── data/
│   │   ├── ingestion.py     # Data loading
│   │   ├── validation.py    # Data validation
│   │   └── models.py        # Data models
│   ├── geography/
│   │   ├── distance.py      # Distance calculations
│   │   └── supertract.py    # Supertract generation
│   ├── index/
│   │   ├── aggregation.py   # City-level aggregation
│   │   ├── bmn_regression.py # BMN regression
│   │   └── weights.py       # Weight calculations
│   └── output/
│       └── export.py        # Data export
```

### After: Microservices Structure
```
rsai-microservices/
├── services/
│   ├── api-gateway/          # :8000 - Request routing
│   ├── data-ingestion/       # :8001 - Data loading
│   ├── data-validation/      # :8002 - Data quality
│   ├── geography/            # :8003 - Spatial processing
│   ├── index-calculation/    # :8004 - BMN & aggregation
│   ├── export/               # :8005 - Data export
│   ├── orchestration/        # :8006 - Workflow management
│   └── configuration/        # :8007 - Config management
├── shared/                   # Common models & utilities
└── infrastructure/           # Docker, monitoring, etc.
```

## Migration Benefits

### Scalability
- **Independent Scaling**: Scale geography service separately for large datasets
- **Resource Optimization**: Allocate more CPU to index calculation service
- **Load Distribution**: Distribute processing across multiple instances

### Maintainability
- **Service Isolation**: Changes to validation don't affect index calculation
- **Clear Boundaries**: Each service has specific responsibilities
- **Independent Deployments**: Update services without full system restart

### Development
- **Parallel Development**: Teams can work on different services simultaneously
- **Technology Flexibility**: Use optimal tools for each service
- **Testing**: Easier unit and integration testing per service

## Data Flow Migration

### Original Monolithic Flow
```python
# Single process pipeline
pipeline = RSAIPipeline()
transactions = pipeline.load_data("data.csv")
validated = pipeline.validate_data(transactions)
supertracts = pipeline.generate_supertracts(validated)
indices = pipeline.calculate_indices(supertracts)
pipeline.export_results(indices)
```

### New Microservices Flow
```python
# Distributed pipeline via API calls
import httpx

# 1. Data Ingestion
async with httpx.AsyncClient() as client:
    upload_response = await client.post(
        "http://localhost:8000/api/v1/ingestion/upload",
        files={"file": open("data.csv", "rb")},
        data={"data_source": "sample_data"}
    )
    job_id = upload_response.json()["data"]["id"]

# 2. Orchestrated Processing
    pipeline_response = await client.post(
        "http://localhost:8000/api/v1/orchestration/pipelines",
        json={
            "name": "rsai_full_pipeline",
            "ingestion_job_id": job_id,
            "parameters": {
                "min_half_pairs": 40,
                "base_year": 2020
            }
        }
    )
```

## Service-by-Service Migration

### 1. Data Ingestion Service
**Maps from**: `rsai.src.data.ingestion.DataIngestion`

**New Capabilities**:
- File upload via REST API
- Multiple format support (CSV, Parquet, Excel)
- Batch processing with progress tracking
- Data schema validation
- Asynchronous processing with Celery

**Migration Steps**:
```python
# Old monolithic way
ingestion = DataIngestion()
df = ingestion.load_transaction_data("data.csv")

# New microservice way
import httpx
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/api/v1/upload",
        files={"file": open("data.csv", "rb")},
        data={"data_source": "migration_data"}
    )
```

### 2. Data Validation Service
**Maps from**: `rsai.src.data.validation.DataValidator`

**New Capabilities**:
- Real-time validation via API
- Configurable validation rules
- Detailed validation reports
- Statistical quality metrics

**Migration Steps**:
```python
# Old way
validator = DataValidator()
results = validator.validate_transactions(df)

# New way
response = await client.post(
    "http://localhost:8002/api/v1/validate",
    json={"job_id": job_id, "rules": ["price_range", "date_validation"]}
)
```

### 3. Geography Service
**Maps from**: `rsai.src.geography.supertract.SupertractGenerator`

**New Capabilities**:
- Spatial database with PostGIS
- Distance matrix caching
- Multiple clustering algorithms
- Geographic API queries

### 4. Index Calculation Service
**Maps from**: 
- `rsai.src.index.bmn_regression`
- `rsai.src.index.aggregation.CityLevelAggregator`
- `rsai.src.index.weights.WeightCalculator`

**New Capabilities**:
- Distributed BMN regression
- Multiple weighting schemes
- Time series index generation
- Performance optimizations

### 5. Export Service
**Maps from**: `rsai.src.output.export.RSAIExporter`

**New Capabilities**:
- Multiple export formats
- Streaming large datasets
- Scheduled exports
- Visualization generation

## Data Model Changes

### Shared Models
New centralized data models in `shared/models/`:
- `Transaction`: Enhanced with validation metadata
- `GeographicUnit`: Hierarchical geographic representation
- `IndexValue`: Time series index data
- `ValidationResult`: Comprehensive validation reporting

### Database Changes
- **Monolith**: Single SQLite/CSV files
- **Microservices**: PostgreSQL with service-specific schemas
- **Benefits**: ACID transactions, concurrent access, better performance

## Configuration Migration

### Old Configuration
```python
# Hardcoded parameters in Python
pipeline = RSAIPipeline(
    min_half_pairs=40,
    base_index_value=100.0,
    base_year=2020
)
```

### New Configuration
```yaml
# Centralized configuration service
rsai:
  pipeline:
    min_half_pairs: 40
    base_index_value: 100.0
    base_year: 2020
  services:
    ingestion:
      batch_size: 10000
      max_file_size_mb: 100
    geography:
      clustering_algorithm: "hierarchical"
      distance_threshold_km: 50
```

## Testing Migration

### Integration Testing
```python
# Test full pipeline via API
async def test_full_pipeline():
    # Upload data
    upload_response = await upload_test_data()
    assert upload_response.status_code == 200
    
    # Trigger pipeline
    pipeline_response = await trigger_pipeline(upload_response.json()["data"]["id"])
    assert pipeline_response.status_code == 200
    
    # Verify results
    results = await get_pipeline_results(pipeline_response.json()["data"]["id"])
    assert len(results["indices"]) > 0
```

### Service Testing
Each service has comprehensive test suites:
- Unit tests for business logic
- Integration tests with database
- API endpoint tests
- Performance benchmarks

## Monitoring & Observability

### New Capabilities
- **Structured Logging**: JSON logs with correlation IDs
- **Metrics**: Prometheus metrics for each service
- **Tracing**: Request tracing across services
- **Health Checks**: Individual service health monitoring

### Dashboards
- Service performance metrics
- Pipeline execution monitoring
- Error rate tracking
- Resource utilization

## Performance Considerations

### Latency
- **Increased**: Network calls between services add latency
- **Mitigation**: Asynchronous processing, request batching
- **Benefit**: Better resource utilization

### Throughput
- **Improved**: Parallel processing across services
- **Scalability**: Independent service scaling
- **Optimization**: Service-specific performance tuning

## Deployment Strategy

### Phase 1: Parallel Deployment
1. Deploy microservices alongside monolith
2. Route non-critical workloads to microservices
3. Validate results against monolith output
4. Monitor performance and stability

### Phase 2: Gradual Migration
1. Migrate data ingestion workloads
2. Migrate geography processing
3. Migrate index calculations
4. Migrate export operations

### Phase 3: Monolith Retirement
1. Route all traffic to microservices
2. Decommission monolithic application
3. Archive monolith code for reference

## Rollback Strategy

### Quick Rollback
- Keep monolith running in parallel initially
- Route traffic back to monolith if issues arise
- Database rollback procedures

### Data Consistency
- Ensure data synchronization between systems
- Validate computational results match
- Maintain audit trails

## Success Metrics

### Performance
- Pipeline execution time: Target < 20% increase initially
- Individual service response time: < 500ms for API calls
- Throughput: Support 10x more concurrent pipelines

### Reliability
- Service uptime: 99.9% target
- Error rate: < 0.1% for critical operations
- Data accuracy: 100% match with monolith results

### Development
- Deployment frequency: Weekly releases per service
- Feature delivery: 50% faster new feature development
- Bug resolution: 75% faster issue resolution

## Common Pitfalls

### Distributed Data Management
- **Problem**: Data consistency across services
- **Solution**: Event-driven architecture with eventual consistency
- **Mitigation**: Comprehensive testing and monitoring

### Service Dependencies
- **Problem**: Service coupling and cascading failures
- **Solution**: Circuit breaker patterns and graceful degradation
- **Mitigation**: Async communication and retry policies

### Monitoring Complexity
- **Problem**: Distributed tracing and debugging
- **Solution**: Correlation IDs and centralized logging
- **Mitigation**: Comprehensive observability stack

## Support & Resources

### Documentation
- Service API documentation: `/docs` on each service
- Architecture decision records (ADRs)
- Operational runbooks

### Development
- Local development with Docker Compose
- CI/CD pipelines for each service
- Code quality tools and standards

### Operations
- Infrastructure as Code (IaC)
- Monitoring and alerting setup
- Incident response procedures

This migration maintains the mathematical integrity of the RSAI model while providing a modern, scalable architecture for future growth.
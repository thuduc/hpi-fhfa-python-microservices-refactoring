# RSAI Microservices Architecture

## Overview
Microservices implementation of the Repeat-Sales Aggregation Index (RSAI) model, refactored from the original monolithic Python application.

## Architecture
This system is composed of 8 microservices that work together to process real estate transaction data and generate house price indices:

### Core Services
1. **API Gateway** (`:8000`) - Request routing and authentication
2. **Data Ingestion Service** (`:8001`) - Data loading and preprocessing  
3. **Data Validation Service** (`:8002`) - Data quality assessment
4. **Geography Service** (`:8003`) - Spatial data processing and supertract generation
5. **Index Calculation Service** (`:8004`) - BMN regression and index computation
6. **Export Service** (`:8005`) - Data export and visualization
7. **Orchestration Service** (`:8006`) - Workflow management
8. **Configuration Service** (`:8007`) - Centralized configuration

### Shared Components
- **Shared Models** - Common data models and schemas
- **Common Utilities** - Logging, monitoring, database utilities

## Technology Stack
- **Framework**: FastAPI (Python 3.12)
- **Data Processing**: pandas, numpy, statsmodels
- **Databases**: PostgreSQL, PostGIS, TimescaleDB, Redis
- **Message Queue**: Redis Streams
- **Containerization**: Docker + Docker Compose
- **Testing**: pytest, pytest-asyncio

## Quick Start

### Prerequisites
- Python 3.12+
- Docker and Docker Compose
- Git

### Development Setup
```bash
# Clone repository
git clone https://github.com/thuduc/hpi-fhfa-python-microservices-refactoring.git
cd hpi-fhfa-python-microservices-refactoring

# Start infrastructure services
docker-compose up -d postgres redis

# Install dependencies for each service
cd services/data-ingestion
pip install -r requirements.txt

# Run individual service
python -m app.main

# Or run all services
docker-compose up
```

### API Documentation
Once running, visit:
- API Gateway: http://localhost:8000/docs
- Individual service docs at their respective ports

## Service Communication
Services communicate via:
- **REST APIs** for synchronous operations
- **Redis Streams** for asynchronous data flow
- **PostgreSQL** for shared data persistence

## Data Flow
```
Raw Data → Ingestion → Validation → Geography → Index Calculation → Export
           ↓            ↓           ↓           ↓                 ↓
         Events       Events    Events     Events           Events
```

## Development

### Adding a New Service
1. Create service directory in `services/`
2. Copy template structure from existing service
3. Update Docker Compose configuration
4. Add service to API Gateway routing

### Testing
```bash
# Run all tests
pytest

# Run service-specific tests  
cd services/data-ingestion
pytest tests/

# Integration tests
pytest tests/integration/
```

### Code Quality
```bash
# Format code
black .

# Type checking  
mypy .

# Linting
flake8 .
```

## Deployment

### Local Development
```bash
docker-compose up
```

### Production
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## Monitoring
- **Health Checks**: `/health` endpoint on each service
- **Metrics**: Prometheus metrics at `/metrics`
- **Logs**: Structured JSON logging with correlation IDs

## Contributing
1. Fork the repository
2. Create feature branch (`feature/your-feature`)
3. Commit changes with clear messages
4. Add tests for new functionality
5. Submit pull request

## License
MIT License - see LICENSE file for details

## Migration from Monolith
This microservices implementation maintains full compatibility with the original RSAI mathematical models while providing improved scalability and maintainability. See `MIGRATION_GUIDE.md` for detailed migration instructions.
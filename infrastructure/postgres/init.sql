-- Initialize databases for RSAI microservices

-- Create databases for each service
CREATE DATABASE rsai_ingestion;
CREATE DATABASE rsai_validation;
CREATE DATABASE rsai_geography;
CREATE DATABASE rsai_index;
CREATE DATABASE rsai_export;
CREATE DATABASE rsai_orchestration;
CREATE DATABASE rsai_config;

-- Create service-specific users
CREATE USER rsai_ingestion_user WITH PASSWORD 'ingestion_password';
CREATE USER rsai_validation_user WITH PASSWORD 'validation_password';
CREATE USER rsai_geography_user WITH PASSWORD 'geography_password';
CREATE USER rsai_index_user WITH PASSWORD 'index_password';
CREATE USER rsai_export_user WITH PASSWORD 'export_password';
CREATE USER rsai_orchestration_user WITH PASSWORD 'orchestration_password';
CREATE USER rsai_config_user WITH PASSWORD 'config_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE rsai_ingestion TO rsai_ingestion_user;
GRANT ALL PRIVILEGES ON DATABASE rsai_validation TO rsai_validation_user;
GRANT ALL PRIVILEGES ON DATABASE rsai_geography TO rsai_geography_user;
GRANT ALL PRIVILEGES ON DATABASE rsai_index TO rsai_index_user;
GRANT ALL PRIVILEGES ON DATABASE rsai_export TO rsai_export_user;
GRANT ALL PRIVILEGES ON DATABASE rsai_orchestration TO rsai_orchestration_user;
GRANT ALL PRIVILEGES ON DATABASE rsai_config TO rsai_config_user;

-- Enable PostGIS extension for geography service
\c rsai_geography;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Enable TimescaleDB extension for index service (time series data)
\c rsai_index;
CREATE EXTENSION IF NOT EXISTS timescaledb;
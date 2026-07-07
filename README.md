# Property Consultant Agent (Python GIS Backend)

This is the backend service for the Property Consultant Agent, a GIS-enabled platform for searching and evaluating real estate properties. Built with FastAPI, PostgreSQL, and PostGIS, it provides advanced spatial querying capabilities to find properties based on location, proximity to amenities (using OpenStreetMap data), and custom ranking algorithms.

## Features

- **Spatial Search:** Query properties based on complex geographical parameters.
- **Place Resolution:** Resolves places and points of interest using integrated OpenStreetMap (OSM) data.
- **Custom Ranking:** Ranks property search results based on a customizable scoring engine.
- **High Performance:** Built on FastAPI with async support for fast API responses.
- **Robust Database:** Uses PostgreSQL with the PostGIS extension for advanced geospatial operations.

## Technology Stack

- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **Database:** PostgreSQL with [PostGIS](https://postgis.net/)
- **ORM & GIS Extension:** SQLAlchemy, [GeoAlchemy2](https://geoalchemy-2.readthedocs.io/)
- **Geospatial Processing:** [GeoPandas](https://geopandas.org/), [Shapely](https://shapely.readthedocs.io/)
- **Validation:** Pydantic
- **Migrations:** Alembic
- **Testing:** Pytest
- **Containerization:** Docker & Docker Compose

## Detailed Architecture

The project follows a Domain-Driven Design (DDD) inspired layered architecture to ensure separation of concerns and maintainability.

### High-Level Components

1. **API Layer (`app/api`):** 
   Handles HTTP requests and responses. Defines API endpoints (e.g., `/properties/search`) and delegates business logic to the service layer.
   
2. **Core (`app/core`):**
   Contains cross-cutting concerns like application configuration (via Pydantic BaseSettings), logging setup, middlewares (error handling, request IDs), and the database connection manager.

3. **Models (`app/models`):**
   Defines the SQLAlchemy ORM entities representing the database schema.
   - `Property`: The core entity storing property details (price, BHK, area) and geography (POINT).
   - `OSMBase`, `OSMPoint`, `OSMPolygon`, `OSMLine`: Entities mapped to OpenStreetMap tables (from `osm2pgsql`) to power location-based context and place resolution.

4. **Repositories (`app/repositories`):**
   The Data Access Layer. Abstracts database interactions, providing methods for fetching, saving, and querying properties and OSM data.
   - `PropertyRepository`
   - `OSMRepository`

5. **Services (`app/services`):**
   Encapsulates the core business logic.
   - `PropertySearchService`: Orchestrates the overall search flow.
   - **Spatial Services (`app/services/spatial`):**
     - `PlaceResolverService`: Connects to the OSM repository to resolve natural language places into spatial boundaries or points.
     - `SpatialQueryBuilder`: Constructs complex PostGIS SQL queries (e.g., `ST_DWithin`, `ST_Intersects`) via GeoAlchemy2.
   - **Ranking Engine (`app/services/ranking`):**
     - Evaluates and sorts properties based on criteria like distance to POIs, price, or user preferences.

6. **Schemas (`app/schemas`):**
   Pydantic models used for data validation, serialization, and deserialization of API payloads (Request/Response schemas).

7. **Workers (`app/workers`):**
   Handles asynchronous or background processing tasks (e.g., data ingestion, regular index updates).

8. **Migrations (`app/migrations`):**
   Managed by Alembic, containing version-controlled database schema changes.

### Request Flow (Example: Property Search)

1. **Client** sends a `POST /api/v1/properties/search` request with search criteria.
2. **Router** validates the request payload using `PropertySearchRequest` schema.
3. **PropertySearchService** is injected with its dependencies (Repositories, PlaceResolver, SpatialQueryBuilder, RankingEngine) via FastAPI's Dependency Injection.
4. **PlaceResolver** determines the spatial context (e.g., a specific city or neighborhood boundary) using OSM data.
5. **SpatialQueryBuilder** formulates the geospatial query using GeoAlchemy2 based on user filters.
6. **PropertyRepository** executes the query against PostGIS.
7. **RankingEngine** scores the resulting properties.
8. **Router** returns the `PropertySearchResponse` to the client.

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Python 3.11+ (for local development)

### Running with Docker Compose

The easiest way to run the application and its dependencies (PostgreSQL + PostGIS) is using Docker.

1. Clone the repository.
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
3. Build and start the containers:
   ```bash
   docker-compose up --build
   ```
4. The API will be available at `http://localhost:8000`. You can access the interactive Swagger documentation at `http://localhost:8000/docs`.

### Local Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run Alembic migrations to set up your database schema:
   ```bash
   alembic upgrade head
   ```
4. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

# Learning Roadmap Before Working on This Project

You already know Python, NumPy, and Pandas. That is a good base. Before actively building this Real Estate GIS backend, learn the concepts below in this order.

The goal is not to become an expert in everything first. The goal is to understand enough to read the code, make safe changes, debug issues, and build features without guessing.

## 1. Backend Web Development Basics

Learn:

- What an API is
- REST API basics
- HTTP methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- HTTP status codes: `200`, `201`, `400`, `404`, `422`, `500`
- Request body, query params, path params, headers
- JSON request and response formats
- API validation

Why it matters:

This project uses FastAPI. Every feature, such as property search, nearby places, lead creation, and FAQs, will be exposed through API endpoints.

Practice:

- Build a small FastAPI app with:
  - `GET /health`
  - `POST /items`
  - `GET /items/{id}`

## 2. FastAPI

Learn:

- FastAPI app structure
- Routers
- Pydantic request and response models
- Dependency injection
- Middleware
- Error handling
- Swagger docs at `/docs`
- Running with `uvicorn`

Important files in this project:

- `app/main.py`
- `app/api/v1/router.py`
- `app/core/config.py`
- `app/core/middleware.py`

Practice:

- Create one route file for users
- Add request validation using Pydantic
- Return typed response models
- Add a simple dependency function

## 3. Pydantic v2

Learn:

- `BaseModel`
- Field validation
- Optional fields
- Enum validation
- Nested models
- `model_config`
- Difference between input schema and output schema

Why it matters:

Pydantic protects the backend from invalid API input. For example, budget must be numeric, page size should not exceed limits, and nearby category values must be controlled.

Practice:

- Create a `PropertySearchRequest` model
- Validate:
  - city
  - locality
  - budget range
  - BHK
  - amenities

## 4. SQL Basics

Learn:

- Tables, rows, columns
- Primary keys
- Foreign keys
- `SELECT`
- `INSERT`
- `UPDATE`
- `DELETE`
- `WHERE`
- `JOIN`
- `GROUP BY`
- `ORDER BY`
- `LIMIT`
- Indexes
- Constraints

Why it matters:

Even though the project uses SQLAlchemy, you still need to understand the SQL being generated. Search and GIS performance depend heavily on good SQL design.

Practice:

- Create tables for:
  - properties
  - locations
  - amenities
- Write joins between them
- Filter by price, city, BHK, and category

## 5. PostgreSQL

Learn:

- PostgreSQL databases and schemas
- Data types: `TEXT`, `NUMERIC`, `BOOLEAN`, `DATE`, `TIMESTAMPTZ`, `JSONB`, arrays
- Enum types
- Index types
- `EXPLAIN ANALYZE`
- Transactions
- Connection strings

Why it matters:

This project uses PostgreSQL as the main database. It stores properties, leads, chat sessions, FAQs, nearby facilities, and recommendation scores.

Practice:

- Create a local PostgreSQL database
- Connect using `psql` or pgAdmin
- Create tables manually
- Run `EXPLAIN ANALYZE` on filter queries

## 6. PostGIS and GIS Concepts

Learn:

- Latitude and longitude
- Coordinate systems
- SRID `4326`
- `geometry`
- `geography`
- Points, polygons, multipolygons
- Spatial indexes
- Radius search
- Distance calculations
- `ST_DWithin`
- `ST_Distance`
- `ST_MakePoint`
- `ST_SetSRID`

Why it matters:

This is a GIS-aware real estate platform. Features like nearby hospitals, schools, metro stations, and locality expansion depend on PostGIS.

Important concept:

- Use `geometry` for spatial joins and map operations.
- Use `geography` for real-world distance in meters.

Practice:

- Store property latitude/longitude
- Create a PostGIS point
- Find all properties within 3 km of a coordinate
- Find nearest metro station to a property

## 7. SQLAlchemy 2.x

Learn:

- ORM models
- `Mapped`
- `mapped_column`
- Relationships
- Sessions
- `select()`
- Joins
- Filters
- Transactions
- Repository pattern

Why it matters:

The project must not generate raw SQL from user or LLM input. SQLAlchemy query builders help us create safe parameterized queries.

Practice:

- Create SQLAlchemy models for:
  - property
  - property location
  - amenity
- Write repository methods:
  - search properties
  - get property by id
  - get nearby places

## 8. Alembic Migrations

Learn:

- What migrations are
- `alembic revision`
- `alembic upgrade head`
- `upgrade()` and `downgrade()`
- Autogenerate basics
- Manual migrations for extensions, enums, generated columns, and indexes

Why it matters:

Database schema changes must be version-controlled. This is especially important for PostGIS indexes and generated columns.

Practice:

- Create an initial migration
- Add one table
- Add one index
- Upgrade and downgrade the database

## 9. GeoAlchemy2

Learn:

- How GeoAlchemy2 maps PostGIS columns
- `Geometry`
- `Geography`
- Spatial functions through SQLAlchemy
- Calling `ST_DWithin` and `ST_Distance`

Why it matters:

This project uses GeoAlchemy2 to connect SQLAlchemy with PostGIS.

Practice:

- Define a location model with a PostGIS point
- Query locations within a radius
- Order by distance

## 10. Clean Backend Architecture

Learn:

- Route layer
- Schema layer
- Service layer
- Repository layer
- Model layer
- Dependency injection
- Separation of concerns

Why it matters:

This project must stay maintainable. Route handlers should not contain database-heavy logic or business logic.

Project pattern:

```text
API route -> service -> repository -> database
```

Example:

```text
POST /properties/search
-> PropertySearchService
-> PropertyRepository
-> PostgreSQL/PostGIS
```

## 11. Testing with Pytest

Learn:

- Test functions
- Fixtures
- Test clients
- Testing FastAPI endpoints
- Testing validation errors
- Testing repository logic

Why it matters:

Search filters and GIS queries can break silently. Tests help confirm that filters, pagination, and distance calculations still work.

Practice:

- Test `/api/v1/health`
- Test invalid search request
- Test property search with seeded data

## 12. Docker Basics

Learn:

- Dockerfile
- Docker Compose
- Images and containers
- Environment variables
- Ports
- Container networking
- `host.docker.internal`

Why it matters:

In this project, FastAPI can run in Docker while PostgreSQL runs locally on Windows. The container connects to local PostgreSQL using `host.docker.internal`.

Practice:

- Build the FastAPI Docker image
- Run it with Docker Compose
- Confirm `/api/v1/health` works

## 13. Mock Data and Seeding

Learn:

- Faker
- Deterministic random seeds
- CSV loading
- Bulk inserts
- Realistic data distributions
- OSM-style place categories

Why it matters:

The POC needs realistic data: properties, nearby facilities, leads, FAQs, and locality metadata.

Practice:

- Generate 100 fake properties
- Generate property coordinates around a locality center
- Generate nearby facilities like schools and hospitals

## 14. OpenStreetMap and Overpass Basics

Learn:

- What OpenStreetMap is
- What Overpass API is
- OSM tags
- POIs: schools, hospitals, bus stops, metro stations
- Bounding boxes

Why it matters:

Nearby places will be imported from OSM-compatible data structures.

Practice:

- Export hospitals and schools for one city
- Convert OSM data into `nearby_places`

## 15. Logging and Debugging

Learn:

- Python `logging`
- Log levels
- Request IDs
- Reading stack traces
- SQL query logs in development
- Debugging database connection errors

Why it matters:

Backend work is mostly debugging data flow: request -> validation -> query -> response.

Practice:

- Add logs to a service function
- Trigger an error and read the stack trace
- Turn SQL echo on in `.env`

## 16. Minimal AI Integration Concepts

Learn:

- API keys
- Calling external APIs
- Prompt inputs and structured outputs
- Why LLMs should not generate SQL
- Validating AI output before using it

Why it matters:

This project may use Gemini Flash APIs, but AI must remain minimal and controlled. The backend search logic stays deterministic.

Safe AI usage:

- Convert user text into a validated search request
- Summarize property results
- Answer FAQs from approved content

Unsafe AI usage:

- Generating SQL
- Deciding database writes without validation
- Running autonomous loops

## Suggested Learning Order

Follow this sequence:

1. FastAPI basics
2. Pydantic v2
3. SQL basics
4. PostgreSQL
5. SQLAlchemy 2.x
6. Alembic
7. PostGIS
8. GeoAlchemy2
9. Repository and service patterns
10. Pytest
11. Docker
12. Mock data generation
13. OpenStreetMap and Overpass
14. Logging and debugging
15. Minimal AI API usage

## Mini Milestones

Milestone 1:

- Run the current FastAPI app
- Open `/docs`
- Open `/api/v1/health`

Milestone 2:

- Create PostgreSQL database
- Enable PostGIS
- Run first Alembic migration

Milestone 3:

- Insert mock property data
- Search properties by city, price, and BHK

Milestone 4:

- Add nearby places
- Search places within a radius

Milestone 5:

- Build property search API
- Add pagination and sorting

Milestone 6:

- Add lead creation
- Add FAQ retrieval

Milestone 7:

- Add basic GIS scoring
- Add property nearby endpoint

## What You Should Be Comfortable With Before Building Features

You are ready to work on this project when you can:

- Create a FastAPI endpoint
- Validate input using Pydantic
- Write a basic SQL query
- Understand primary keys and foreign keys
- Create a SQLAlchemy model
- Use a database session
- Run an Alembic migration
- Understand latitude and longitude
- Explain `ST_DWithin` at a basic level
- Run tests with pytest
- Read an error traceback

## What You Do Not Need Yet

Do not spend time on these right now:

- Kubernetes
- Redis
- Microservice orchestration
- Advanced recommendation systems
- Vector databases
- Embeddings
- Authentication
- Frontend frameworks
- Complex AI agents

Those can come later. For now, focus on deterministic backend engineering, database design, GIS queries, and clean Python structure.


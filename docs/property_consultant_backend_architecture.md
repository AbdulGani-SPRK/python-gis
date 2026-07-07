# AI-Powered Real Estate Property Consultant Backend Architecture

This document defines a scalable proof-of-concept backend for a GIS-aware property consultant platform using PostgreSQL, PostGIS, FastAPI, SQLAlchemy, GeoPandas, Shapely, Docker, and self-hosted n8n.

Core principle: deterministic backend logic owns search, filtering, ranking, persistence, and GIS calculations. LLMs may interpret user intent into a validated search DTO, summarize results, or answer FAQs, but they must never generate raw SQL.

## 1. Database Design

### Normalization Strategy

- `properties` stores business attributes and listing lifecycle.
- `property_locations` stores one canonical GIS point per property and optional address/locality metadata.
- `property_images`, `property_amenities`, and `property_features` keep repeatable or typed attributes normalized.
- `nearby_places` and `locality_metadata` support spatial context and locality expansion.
- `leads`, `chat_sessions`, and `chat_messages` capture conversion and conversation memory.
- `faq_entries` supports managed FAQ retrieval.
- `recommendation_scores` stores explainable scoring snapshots for audit/debugging.
- `property_comparisons` stores user-selected comparison sets.
- Future embeddings should be added via `pgvector` columns or separate embedding tables to avoid coupling vector refreshes with transactional property rows.

### PostgreSQL Extensions and Enums

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
-- Future:
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE listing_purpose AS ENUM ('rent', 'purchase');
CREATE TYPE property_category AS ENUM ('residential', 'commercial');
CREATE TYPE residential_type AS ENUM ('apartment', 'villa', 'independent_house', 'plot', 'studio', 'penthouse');
CREATE TYPE commercial_type AS ENUM ('office', 'shop', 'showroom', 'warehouse', 'coworking', 'industrial_land');
CREATE TYPE furnishing_status AS ENUM ('unfurnished', 'semi_furnished', 'fully_furnished');
CREATE TYPE property_status AS ENUM ('draft', 'active', 'inactive', 'sold', 'rented');
CREATE TYPE nearby_place_category AS ENUM (
  'hospital', 'school', 'college', 'metro_station', 'railway_station',
  'bus_stop', 'mall', 'airport', 'it_park', 'park', 'gym'
);
CREATE TYPE lead_status AS ENUM ('new', 'contacted', 'qualified', 'converted', 'lost');
CREATE TYPE chat_role AS ENUM ('user', 'assistant', 'system', 'tool');
```

### Core Tables

```sql
CREATE TABLE properties (
  id BIGSERIAL PRIMARY KEY,
  public_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  category property_category NOT NULL,
  residential_subtype residential_type,
  commercial_subtype commercial_type,
  listing_purpose listing_purpose NOT NULL,
  status property_status NOT NULL DEFAULT 'active',
  price NUMERIC(14,2) NOT NULL CHECK (price >= 0),
  maintenance_fee NUMERIC(12,2) CHECK (maintenance_fee >= 0),
  security_deposit NUMERIC(14,2) CHECK (security_deposit >= 0),
  carpet_area_sqft NUMERIC(10,2) CHECK (carpet_area_sqft > 0),
  builtup_area_sqft NUMERIC(10,2) CHECK (builtup_area_sqft > 0),
  bhk SMALLINT CHECK (bhk >= 0 AND bhk <= 10),
  bathrooms SMALLINT CHECK (bathrooms >= 0 AND bathrooms <= 20),
  parking_count SMALLINT DEFAULT 0 CHECK (parking_count >= 0),
  furnishing furnishing_status,
  floor_number SMALLINT,
  total_floors SMALLINT,
  possession_date DATE,
  available_from DATE,
  builder_name TEXT,
  project_name TEXT,
  owner_type TEXT CHECK (owner_type IN ('owner', 'broker', 'builder')),
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT subtype_matches_category CHECK (
    (category = 'residential' AND residential_subtype IS NOT NULL AND commercial_subtype IS NULL)
    OR
    (category = 'commercial' AND commercial_subtype IS NOT NULL AND residential_subtype IS NULL)
  )
);

CREATE TABLE property_locations (
  property_id BIGINT PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
  address_line1 TEXT,
  address_line2 TEXT,
  locality TEXT NOT NULL,
  city TEXT NOT NULL,
  state TEXT NOT NULL,
  pincode TEXT,
  latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
  longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
  geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)) STORED,
  geog GEOGRAPHY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography) STORED,
  geohash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE property_images (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  image_url TEXT NOT NULL,
  alt_text TEXT,
  sort_order SMALLINT NOT NULL DEFAULT 0,
  is_primary BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE property_amenities (
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  amenity_code TEXT NOT NULL,
  amenity_name TEXT NOT NULL,
  amenity_group TEXT,
  PRIMARY KEY (property_id, amenity_code)
);

CREATE TABLE property_features (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  feature_key TEXT NOT NULL,
  feature_value TEXT NOT NULL,
  feature_numeric NUMERIC(14,4),
  unit TEXT,
  UNIQUE (property_id, feature_key)
);
```

### GIS and Context Tables

```sql
CREATE TABLE nearby_places (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'osm',
  source_place_id TEXT,
  name TEXT NOT NULL,
  category nearby_place_category NOT NULL,
  locality TEXT,
  city TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
  longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
  geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)) STORED,
  geog GEOGRAPHY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography) STORED,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source, source_place_id)
);

CREATE TABLE locality_metadata (
  id BIGSERIAL PRIMARY KEY,
  city TEXT NOT NULL,
  locality TEXT NOT NULL,
  centroid GEOMETRY(Point, 4326),
  boundary GEOMETRY(MultiPolygon, 4326),
  avg_rent_2bhk NUMERIC(14,2),
  avg_sale_price_sqft NUMERIC(14,2),
  livability_score NUMERIC(5,2) CHECK (livability_score BETWEEN 0 AND 100),
  commercial_score NUMERIC(5,2) CHECK (commercial_score BETWEEN 0 AND 100),
  transit_score NUMERIC(5,2) CHECK (transit_score BETWEEN 0 AND 100),
  school_score NUMERIC(5,2) CHECK (school_score BETWEEN 0 AND 100),
  hospital_score NUMERIC(5,2) CHECK (hospital_score BETWEEN 0 AND 100),
  metadata JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (city, locality)
);
```

### Lead, Chat, FAQ, Recommendation, Comparison Tables

```sql
CREATE TABLE leads (
  id BIGSERIAL PRIMARY KEY,
  public_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  name TEXT NOT NULL,
  phone TEXT,
  email TEXT,
  preferred_city TEXT,
  preferred_locality TEXT,
  listing_purpose listing_purpose,
  budget_min NUMERIC(14,2),
  budget_max NUMERIC(14,2),
  property_category property_category,
  bhk SMALLINT,
  status lead_status NOT NULL DEFAULT 'new',
  source TEXT NOT NULL DEFAULT 'chat',
  captured_payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_sessions (
  id BIGSERIAL PRIMARY KEY,
  public_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  lead_id BIGINT REFERENCES leads(id) ON DELETE SET NULL,
  user_ref TEXT,
  session_summary TEXT,
  search_context JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_messages (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role chat_role NOT NULL,
  content TEXT NOT NULL,
  tool_name TEXT,
  message_metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE faq_entries (
  id BIGSERIAL PRIMARY KEY,
  category TEXT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  tags TEXT[] NOT NULL DEFAULT '{}',
  is_active BOOLEAN NOT NULL DEFAULT true,
  priority SMALLINT NOT NULL DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE recommendation_scores (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES chat_sessions(id) ON DELETE SET NULL,
  lead_id BIGINT REFERENCES leads(id) ON DELETE SET NULL,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  score NUMERIC(8,4) NOT NULL CHECK (score BETWEEN 0 AND 100),
  budget_score NUMERIC(8,4) NOT NULL DEFAULT 0,
  locality_score NUMERIC(8,4) NOT NULL DEFAULT 0,
  amenity_score NUMERIC(8,4) NOT NULL DEFAULT 0,
  gis_score NUMERIC(8,4) NOT NULL DEFAULT 0,
  freshness_score NUMERIC(8,4) NOT NULL DEFAULT 0,
  explanation JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE property_comparisons (
  id BIGSERIAL PRIMARY KEY,
  public_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  session_id BIGINT REFERENCES chat_sessions(id) ON DELETE SET NULL,
  lead_id BIGINT REFERENCES leads(id) ON DELETE SET NULL,
  property_ids BIGINT[] NOT NULL CHECK (array_length(property_ids, 1) BETWEEN 2 AND 5),
  comparison_snapshot JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Indexing Strategy

```sql
CREATE INDEX idx_properties_active_filters
  ON properties (listing_purpose, category, status, price, bhk, furnishing)
  WHERE status = 'active';
CREATE INDEX idx_properties_residential_subtype ON properties (residential_subtype) WHERE category = 'residential';
CREATE INDEX idx_properties_commercial_subtype ON properties (commercial_subtype) WHERE category = 'commercial';
CREATE INDEX idx_properties_metadata_gin ON properties USING GIN (metadata);
CREATE INDEX idx_property_locations_city_locality ON property_locations (city, locality);
CREATE INDEX idx_property_locations_geom_gist ON property_locations USING GIST (geom);
CREATE INDEX idx_property_locations_geog_gist ON property_locations USING GIST (geog);
CREATE INDEX idx_property_amenities_code ON property_amenities (amenity_code, property_id);
CREATE INDEX idx_nearby_places_category_city ON nearby_places (category, city);
CREATE INDEX idx_nearby_places_geom_gist ON nearby_places USING GIST (geom);
CREATE INDEX idx_nearby_places_geog_gist ON nearby_places USING GIST (geog);
CREATE INDEX idx_locality_boundary_gist ON locality_metadata USING GIST (boundary);
CREATE INDEX idx_leads_status_created ON leads (status, created_at DESC);
CREATE INDEX idx_chat_messages_session_created ON chat_messages (session_id, created_at);
CREATE INDEX idx_faq_question_trgm ON faq_entries USING GIN (question gin_trgm_ops);
CREATE INDEX idx_faq_tags_gin ON faq_entries USING GIN (tags);
CREATE INDEX idx_recommendation_scores_lookup ON recommendation_scores (session_id, score DESC, created_at DESC);
```

## 2. PostGIS Design

Use `geometry(Point, 4326)` for spatial joins, locality containment, and map operations. Use `geography(Point, 4326)` for accurate distance in meters on latitude/longitude. Store both as generated columns to avoid dual-write bugs.

Radius search:

```sql
SELECT p.id, p.title, ST_Distance(pl.geog, ST_MakePoint(:lng, :lat)::geography) AS distance_m
FROM properties p
JOIN property_locations pl ON pl.property_id = p.id
WHERE p.status = 'active'
  AND ST_DWithin(pl.geog, ST_MakePoint(:lng, :lat)::geography, :radius_m)
ORDER BY distance_m
LIMIT :limit;
```

Nearby facilities by category:

```sql
SELECT np.category, np.name, ST_Distance(pl.geog, np.geog) AS distance_m
FROM property_locations pl
JOIN nearby_places np
  ON ST_DWithin(pl.geog, np.geog, :radius_m)
WHERE pl.property_id = :property_id
  AND np.category = ANY(:categories)
ORDER BY np.category, distance_m;
```

Locality expansion:

```sql
SELECT target.locality, ST_Distance(src.centroid::geography, target.centroid::geography) AS distance_m
FROM locality_metadata src
JOIN locality_metadata target
  ON src.city = target.city
 AND src.locality <> target.locality
WHERE src.city = :city
  AND src.locality = :locality
  AND ST_DWithin(src.centroid::geography, target.centroid::geography, :radius_m)
ORDER BY distance_m, target.livability_score DESC;
```

Travel proximity for POC should start with straight-line distance plus category weights. Later, add OSRM/Valhalla/GraphHopper for road-network travel time and cache results in a `travel_time_cache` table keyed by origin geohash, destination id, and mode.

## 3. Property Search Engine

Search flow:

1. Validate request with Pydantic.
2. Convert natural language into a typed `PropertySearchRequest` if chat is used.
3. Build SQLAlchemy expressions from whitelisted fields only.
4. Apply deterministic filters first: status, purpose, category, city, locality, price, BHK, furnishing.
5. Apply amenity filters through `EXISTS` or grouped joins.
6. Apply optional GIS radius filters.
7. Rank with a deterministic score expression.
8. Paginate with keyset pagination for large result sets; offset is acceptable for POC.

Example SQLAlchemy-style query shape:

```python
query = (
    select(Property)
    .join(PropertyLocation)
    .where(Property.status == "active")
    .where(Property.listing_purpose == request.listing_purpose)
    .where(Property.category == request.category)
)

if request.budget_max:
    query = query.where(Property.price <= request.budget_max)
if request.city:
    query = query.where(PropertyLocation.city == request.city)
if request.locality:
    query = query.where(PropertyLocation.locality == request.locality)
```

Hybrid score:

```text
final_score =
  0.30 * budget_fit_score +
  0.20 * locality_match_score +
  0.20 * amenity_match_score +
  0.15 * gis_facility_score +
  0.10 * property_quality_score +
  0.05 * freshness_score
```

Budget fit:

```text
if price within requested range: 100
if price within relaxed range: max(0, 100 - percent_over_budget * 2)
else: 0
```

Amenity similarity:

```text
amenity_score = 100 * matched_requested_amenities / max(1, requested_amenities)
```

Sorting options: `relevance`, `price_asc`, `price_desc`, `newest`, `distance`, `area_desc`.

Fallback strategy:

- Exact locality and budget.
- Same locality with relaxed budget.
- Nearby localities with original budget.
- Nearby localities with relaxed budget.
- Same city, same category, best score.

## 4. Recommendation Engine

Recommendation hierarchy:

1. Exact user intent match.
2. Nearby locality match.
3. Relaxed budget match.
4. Amenity-similar match.
5. Same city popularity/freshness fallback.

GIS facility score:

```text
category_score = min(100, 100 * max(0, 1 - nearest_distance_m / ideal_radius_m))
gis_score = weighted average across requested categories
```

Suggested category weights:

```text
residential: school 0.20, hospital 0.15, metro 0.15, park 0.10, mall 0.10, bus 0.10, gym 0.10, railway 0.05, airport 0.05
commercial: metro 0.20, bus 0.15, railway 0.10, airport 0.10, it_park 0.20, mall 0.10, hospital 0.05, gym 0.05, park 0.05
```

Ranking pipeline:

1. Candidate retrieval with hard filters.
2. Candidate expansion if count is below threshold.
3. Feature enrichment: nearest facilities, locality metadata, amenity overlap.
4. Score calculation in Python service or SQL expression.
5. Persist top scores in `recommendation_scores`.
6. Return scored properties with explanation payload.

## 5. FastAPI Microservice

Recommended folder structure:

```text
app/
  main.py
  core/config.py
  core/database.py
  api/v1/routes/
    properties.py
    recommendations.py
    gis.py
    localities.py
    leads.py
    faqs.py
    comparisons.py
  schemas/
    property.py
    search.py
    recommendation.py
    lead.py
    faq.py
    comparison.py
  models/
    property.py
    gis.py
    lead.py
    chat.py
    faq.py
  repositories/
    property_repository.py
    gis_repository.py
    lead_repository.py
    faq_repository.py
  services/
    property_search_service.py
    recommendation_service.py
    gis_scoring_service.py
    lead_service.py
    faq_service.py
  workers/
    osm_importer.py
    seed_mock_data.py
  migrations/
```

Endpoints:

```text
POST   /api/v1/properties/search
GET    /api/v1/properties/{property_id}/nearby
POST   /api/v1/recommendations
POST   /api/v1/gis/score
GET    /api/v1/localities/suggestions?city=&q=
POST   /api/v1/leads
GET    /api/v1/faqs
POST   /api/v1/comparisons
GET    /api/v1/comparisons/{public_id}

# Admin API
GET    /api/v1/admin/properties
GET    /api/v1/admin/properties/{property_id}
POST   /api/v1/admin/properties
PUT    /api/v1/admin/properties/{property_id}
DELETE /api/v1/admin/properties/{property_id}
GET    /api/v1/admin/properties/resolve-location?lat=&lng=
```

Example request:

```json
{
  "listing_purpose": "rent",
  "category": "residential",
  "city": "Bengaluru",
  "locality": "Whitefield",
  "budget_min": 30000,
  "budget_max": 70000,
  "bhk": 2,
  "amenities": ["parking", "gym", "security"],
  "nearby_categories": ["metro_station", "school", "hospital"],
  "sort": "relevance",
  "page": 1,
  "page_size": 20
}
```

Service design:

- Routes contain HTTP concerns only.
- Schemas validate input and output.
- Services own search, ranking, and orchestration.
- Repositories own SQLAlchemy query construction.
- Database sessions are injected with FastAPI dependencies.
- n8n receives lead and follow-up events through webhooks after DB commit.

## 6. Mock Data Strategy

Generate 500-2000 properties across Bengaluru, Pune, Hyderabad, Mumbai, Delhi NCR, Chennai, and Gurugram.

Pipeline:

1. Use Overpass Turbo to export OSM facilities by city and category.
2. Normalize OSM tags into `nearby_place_category`.
3. Use locality centroid seeds from public datasets or manually curated city-locality CSV.
4. Generate property points around locality centroids with bounded random offsets.
5. Generate realistic price bands per city/locality/category.
6. Use Faker for owners, leads, and chat/session metadata.
7. Generate amenities from weighted lists.
8. Use deterministic random seeds for repeatable tests.

Example localities:

```text
Bengaluru: Whitefield, Indiranagar, Koramangala, HSR Layout, Electronic City
Pune: Hinjewadi, Wakad, Baner, Kharadi, Viman Nagar
Hyderabad: Gachibowli, Hitech City, Kondapur, Madhapur, Kokapet
Gurugram: Cyber City, Golf Course Road, Sohna Road, Sector 56, Dwarka Expressway
Mumbai: Andheri, Powai, Bandra, Thane, Navi Mumbai
```

Seed commands:

```bash
python -m app.workers.osm_importer --city Bengaluru --bbox "12.75,77.35,13.15,77.85"
python -m app.workers.seed_mock_data --properties 1500 --leads 200 --city Bengaluru
```

## 7. Docker Architecture

```yaml
services:
  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: property_consultant
      POSTGRES_USER: property_app
      POSTGRES_PASSWORD: property_app_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U property_app -d property_consultant"]
      interval: 10s
      timeout: 5s
      retries: 5

  fastapi-gis-service:
    build: .
    environment:
      DATABASE_URL: postgresql+psycopg://property_app:property_app_dev@postgres:5432/property_consultant
      API_ENV: local
      N8N_WEBHOOK_BASE_URL: http://n8n:5678/webhook
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  n8n:
    image: n8nio/n8n:latest
    environment:
      N8N_HOST: localhost
      N8N_PORT: 5678
      N8N_PROTOCOL: http
    ports:
      - "5678:5678"
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  postgres_data:
  n8n_data:
```

For the POC, n8n can use its local persisted SQLite volume while the app uses PostGIS. For production, give n8n its own PostgreSQL database or service, separate from the application database. Use Docker secrets or a managed secret store instead of plaintext environment files.

## Scalability Notes

- Partition high-volume tables such as `chat_messages`, `recommendation_scores`, and eventually `properties` by city or creation month.
- Add read replicas for search-heavy traffic.
- Cache common locality searches and nearby facility summaries in Redis when needed.
- Materialize locality-level aggregates for price trends and facility counts.
- Use keyset pagination for deep result browsing.
- Keep vector embeddings in dedicated tables such as `property_embeddings(property_id, model, embedding, updated_at)`.
- Add background jobs for OSM import, score refresh, embedding refresh, and n8n webhook retries.

## Anti-Patterns to Avoid

- Do not let LLMs generate SQL.
- Do not store latitude/longitude only as floats without PostGIS columns and indexes.
- Do not mix lead capture, chat orchestration, and search query construction in route handlers.
- Do not store all amenities as only JSONB if they must be filtered frequently.
- Do not calculate nearest facilities row-by-row in Python for large result sets.
- Do not use offset pagination for very deep pages in production.
- Do not rely on straight-line distance forever for commute-sensitive recommendations.

## POC-First Implementation Plan

1. Create database migrations for the schema and indexes.
2. Implement SQLAlchemy models and repositories.
3. Build `/properties/search` with deterministic filters and relevance scoring.
4. Import OSM nearby places for one city, preferably Bengaluru or Pune.
5. Generate 1000 synthetic properties and validate spatial distribution on a map.
6. Build nearby facility summary and GIS score services.
7. Add lead capture and n8n webhook workflow.
8. Add FAQ retrieval with trigram search.
9. Add property comparison snapshots.
10. Add recommendation score persistence and explainability payloads.
11. Add integration tests for filters, spatial radius search, scoring, and fallback recommendations.
12. Add observability: request IDs, structured logs, slow query logging, and basic metrics.

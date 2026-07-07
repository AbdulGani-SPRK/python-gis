from typing import Any
from pydantic import BaseModel, Field


class ResolvedPlace(BaseModel):
    name: str | None = None
    category: str | None = None
    latitude: float
    longitude: float
    confidence_score: float = Field(default=1.0)
    osm_id: int | None = None
    # Add any extra metadata from OSM if needed
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpatialContext(BaseModel):
    city_boundary: Any | None = None  # Could be a Shapely geometry or WKT string
    locality_boundary: Any | None = None
    resolved_places: list[ResolvedPlace] = Field(default_factory=list)
    search_radius_m: int | None = None

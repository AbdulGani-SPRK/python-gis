from typing import Any
from geoalchemy2.shape import to_shape

from app.core.osm_mapping import OSM_CATEGORY_MAP, AmenityCategory
from app.repositories.osm_repository import OSMRepository
from app.schemas.spatial import ResolvedPlace, SpatialContext


class PlaceResolverService:
    def __init__(self, repository: OSMRepository) -> None:
        self.repository = repository

    def resolve(
        self,
        city: str,
        locality: str | None = None,
        landmarks: list[str] | None = None,
        amenities: list[AmenityCategory] | None = None,
        search_radius_m: int | None = None,
    ) -> SpatialContext:
        """
        Resolves human-readable spatial intents into a SpatialContext containing geometries.
        """
        context = SpatialContext(search_radius_m=search_radius_m)

        # 1. Resolve Administrative Boundaries
        city_boundary = self.repository.resolve_city_boundary(city)
        if city_boundary is not None:
            context.city_boundary = city_boundary
            
            if locality:
                locality_boundary = self.repository.resolve_locality_boundary(locality, city_geom=city_boundary)
                if locality_boundary is not None:
                    context.locality_boundary = locality_boundary

        target_boundary = context.locality_boundary or context.city_boundary

        # 2. Resolve Places (Landmarks)
        if landmarks:
            for landmark in landmarks:
                # We could try to parse category from landmark, but for now we search by name
                places = self.repository.find_places(
                    name=landmark,
                    category_tags=None,
                    boundary_geom=target_boundary,
                    limit=3
                )
                for geom, name, cat in places:
                    # Convert GeoAlchemy element to shapely to extract lat/lon
                    point = to_shape(geom)
                    context.resolved_places.append(
                        ResolvedPlace(
                            name=name or landmark,
                            category="landmark",
                            latitude=point.y,
                            longitude=point.x,
                            confidence_score=1.0 if name and name.lower() == landmark.lower() else 0.8
                        )
                    )

        # 3. Resolve Amenities
        if amenities:
            for amenity in amenities:
                tags = OSM_CATEGORY_MAP.get(amenity)
                if tags:
                    places = self.repository.find_places(
                        name=None,
                        category_tags=tags,
                        boundary_geom=target_boundary,
                        limit=5
                    )
                    for geom, name, cat in places:
                        point = to_shape(geom)
                        context.resolved_places.append(
                            ResolvedPlace(
                                name=name or amenity.value,
                                category=amenity.value,
                                latitude=point.y,
                                longitude=point.x,
                                confidence_score=0.9
                            )
                        )

        return context

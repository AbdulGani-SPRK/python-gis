from app.schemas.spatial import SpatialContext
from app.services.spatial.strategies import SpatialStrategy, WithinRadiusStrategy


class SpatialQueryBuilder:
    def build_strategies(self, context: SpatialContext) -> list[SpatialStrategy]:
        strategies: list[SpatialStrategy] = []
        
        radius = context.search_radius_m or 2000

        # We can implement OR logic for multiple places if we want any of them,
        # but for now, we just add them as separate strategies (AND logic)
        # or we might want to return a composite OR strategy if it's "near X OR Y".
        # Let's assume AND for now, or just focus on the first place if we want to keep it simple,
        # actually a real OR strategy would be better. Let's create an AnyOfRadiusStrategy.
        
        if context.resolved_places:
            strategies.append(
                AnyOfRadiusStrategy(
                    places=[(p.latitude, p.longitude) for p in context.resolved_places],
                    radius_m=radius
                )
            )

        return strategies


from typing import Any
from sqlalchemy import Select, cast, func, or_
from geoalchemy2 import Geography

class AnyOfRadiusStrategy:
    def __init__(self, places: list[tuple[float, float]], radius_m: int):
        self.places = places
        self.radius_m = radius_m

    def apply(self, query: Select, geom_column: Any) -> Select:
        conditions = []
        for lat, lon in self.places:
            point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
            target_geom = cast(point, Geography(geometry_type="POINT", srid=4326))
            conditions.append(func.ST_DWithin(geom_column, target_geom, self.radius_m))
        
        if conditions:
            return query.where(or_(*conditions))
        return query

from typing import Any, Protocol

from sqlalchemy import Select, cast, func
from geoalchemy2 import Geography


class SpatialStrategy(Protocol):
    def apply(self, query: Select, geom_column: Any) -> Select:
        ...


class WithinRadiusStrategy:
    def __init__(self, target_latitude: float, target_longitude: float, radius_m: int):
        self.target_latitude = target_latitude
        self.target_longitude = target_longitude
        self.radius_m = radius_m

    def apply(self, query: Select, geom_column: Any) -> Select:
        point = func.ST_SetSRID(func.ST_MakePoint(self.target_longitude, self.target_latitude), 4326)
        target_geom = cast(point, Geography(geometry_type="POINT", srid=4326))
        return query.where(func.ST_DWithin(geom_column, target_geom, self.radius_m))


class ContainsPolygonStrategy:
    def __init__(self, polygon_wkt: str):
        self.polygon_wkt = polygon_wkt

    def apply(self, query: Select, geom_column: Any) -> Select:
        # Assuming geom_column is Geography, we might need to cast or use PostGIS functions
        # This is a placeholder for future polygon search (e.g., inside locality)
        polygon_geom = cast(func.ST_GeomFromText(self.polygon_wkt, 4326), Geography(geometry_type="POLYGON", srid=4326))
        return query.where(func.ST_Contains(polygon_geom, geom_column))

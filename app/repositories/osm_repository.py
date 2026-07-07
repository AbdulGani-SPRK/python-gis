from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.osm import OSMPoint, OSMPolygon


class OSMRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve_city_boundary(self, city: str) -> Any | None:
        """Find the administrative boundary for a given city."""
        query = select(OSMPolygon.way).where(
            OSMPolygon.name.ilike(city),
            or_(OSMPolygon.boundary == "administrative", OSMPolygon.place == "city"),
        ).limit(1)
        return self.db.execute(query).scalar_one_or_none()

    def resolve_locality_boundary(self, locality: str, city_geom: Any | None = None) -> Any | None:
        """Find the administrative boundary for a given locality."""
        query = select(OSMPolygon.way).where(
            OSMPolygon.name.ilike(locality),
        )
        if city_geom is not None:
            query = query.where(func.ST_Contains(city_geom, OSMPolygon.way))
        query = query.limit(1)
        return self.db.execute(query).scalar_one_or_none()

    def find_places(
        self,
        name: str | None,
        category_tags: list[dict[str, str]] | None,
        boundary_geom: Any | None,
        limit: int = 5,
    ) -> list[tuple[Any, str, str]]:
        """
        Find places matching a name or category tags within an optional boundary.
        Returns tuples of (centroid_geometry, name, matched_category).
        """
        # Build query for points
        point_query = select(
            func.ST_Centroid(func.ST_Transform(OSMPoint.way, 4326)).label("geom"),
            OSMPoint.name,
            self._build_category_literal(category_tags).label("category")
        )
        point_query = self._apply_place_filters(point_query, OSMPoint, name, category_tags, boundary_geom)

        # Build query for polygons
        polygon_query = select(
            func.ST_Centroid(func.ST_Transform(OSMPolygon.way, 4326)).label("geom"),
            OSMPolygon.name,
            self._build_category_literal(category_tags).label("category")
        )
        polygon_query = self._apply_place_filters(polygon_query, OSMPolygon, name, category_tags, boundary_geom)

        # Combine
        union_query = point_query.union_all(polygon_query).limit(limit)
        
        rows = self.db.execute(union_query).all()
        return [(row.geom, row.name, row.category) for row in rows]

    def _apply_place_filters(
        self, query: Select, model: Any, name: str | None, category_tags: list[dict[str, str]] | None, boundary_geom: Any | None
    ) -> Select:
        conditions = []
        if name:
            conditions.append(model.name.ilike(f"%{name}%"))
        
        if category_tags:
            cat_conditions = []
            for tags in category_tags:
                for k, v in tags.items():
                    column = getattr(model, k, None)
                    if column is not None:
                        cat_conditions.append(column == v)
            if cat_conditions:
                conditions.append(or_(*cat_conditions))
        
        if conditions:
            # If both name and category are provided, it's usually an AND condition (e.g., name="Apollo" AND amenity="hospital")
            # Wait, if name is provided and category is not, it's just name.
            # If both, maybe OR or AND depending on search. Let's use AND for more precision, or just OR if they are broad.
            # For this implementation, let's use OR if we are searching generically, but typically if user says "Central Park Metro", 
            # they mean name "Central Park" AND category "metro". 
            # Actually, the requirement was "resolve user input into GIS entities". We'll AND them if both provided.
            # But the user might just provide `name="Central Park Metro Station"` and no category.
            pass
            
            # Let's use AND
            from sqlalchemy import and_
            query = query.where(and_(*conditions))

        if boundary_geom is not None:
            query = query.where(func.ST_Contains(boundary_geom, model.way))
            
        return query

    def _build_category_literal(self, category_tags: list[dict[str, str]] | None) -> Any:
        from sqlalchemy import literal
        # simplistic representation
        if category_tags:
            return literal(str(category_tags[0]))
        return literal("landmark")

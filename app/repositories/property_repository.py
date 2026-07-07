from dataclasses import dataclass
from math import ceil
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import Select, cast, func, null, select
from sqlalchemy.orm import Session

from uuid import UUID
from geoalchemy2 import Geometry

from app.models.property import Property
from app.schemas.property import PropertySearchRequest, PropertySort
from app.schemas.admin_property import AdminPropertyCreate, AdminPropertyUpdate
from app.services.spatial.strategies import SpatialStrategy


@dataclass(frozen=True)
class PropertySearchResult:
    properties: list[tuple[Property, float | None]]
    total: int
    page: int
    page_size: int
    pages: int


class PropertyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        request: PropertySearchRequest,
        spatial_strategies: list["SpatialStrategy"] | None = None
    ) -> PropertySearchResult:
        distance_expr = self._distance_expression(request)
        query = self._base_query(request, distance_expr)
        
        if spatial_strategies:
            for strategy in spatial_strategies:
                query = strategy.apply(query, Property.geom)
                
        total = self._count(query)
        query = self._apply_sorting(query, request, distance_expr)
        query = query.offset((request.page - 1) * request.page_size).limit(request.page_size)

        rows = self.db.execute(query).all()
        properties = [(row[0], self._to_float(row[1])) for row in rows]
        return PropertySearchResult(
            properties=properties,
            total=total,
            page=request.page,
            page_size=request.page_size,
            pages=ceil(total / request.page_size) if total else 0,
        )

    def _base_query(self, request: PropertySearchRequest, distance_expr: Any) -> Select[tuple[Property, Any]]:
        query = select(Property, distance_expr.label("distance_m")).where(Property.listing_status == "active")

        if request.city:
            query = query.where(Property.city.ilike(request.city))
        if request.locality:
            query = query.where(Property.locality.ilike(request.locality))
        if request.property_type:
            query = query.where(Property.property_type.ilike(request.property_type))
        if request.rental_or_purchase:
            query = query.where(Property.rental_or_purchase == request.rental_or_purchase.value)
        if request.budget_min is not None:
            query = query.where(Property.price >= request.budget_min)
        if request.budget_max is not None:
            query = query.where(Property.price <= request.budget_max)
        if request.bhk is not None:
            query = query.where(Property.bhk == request.bhk)
        if request.furnishing:
            query = query.where(Property.furnishing == request.furnishing.value)
        if request.amenities:
            query = query.where(Property.amenities.contains(request.amenities))
        if request.latitude is not None and request.longitude is not None and request.radius_m is not None:
            query = query.where(func.ST_DWithin(Property.geom, self._point_expression(request), request.radius_m))

        return query

    def _apply_sorting(
        self,
        query: Select[tuple[Property, Any]],
        request: PropertySearchRequest,
        distance_expr: Any,
    ) -> Select[tuple[Property, Any]]:
        if request.sort == PropertySort.price_asc:
            return query.order_by(Property.price.asc(), Property.created_at.desc(), Property.id.asc())
        if request.sort == PropertySort.price_desc:
            return query.order_by(Property.price.desc(), Property.created_at.desc(), Property.id.asc())
        if request.sort == PropertySort.newest:
            return query.order_by(Property.created_at.desc(), Property.id.asc())
        if request.sort == PropertySort.area_desc:
            return query.order_by(Property.area_sqft.desc().nullslast(), Property.created_at.desc(), Property.id.asc())
        if request.sort == PropertySort.distance:
            return query.order_by(distance_expr.asc().nullslast(), Property.created_at.desc(), Property.id.asc())
        return query.order_by(Property.created_at.desc(), Property.id.asc())

    def _count(self, query: Select[tuple[Property, Any]]) -> int:
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        return int(self.db.execute(count_query).scalar_one())

    def _distance_expression(self, request: PropertySearchRequest) -> Any:
        if request.latitude is None or request.longitude is None:
            return null()
        return func.ST_Distance(Property.geom, self._point_expression(request))

    def _point_expression(self, request: PropertySearchRequest) -> Any:
        point = func.ST_SetSRID(func.ST_MakePoint(request.longitude, request.latitude), 4326)
        return cast(point, Geography(geometry_type="POINT", srid=4326))

    def get_admin_paginated(
        self, 
        page: int, 
        page_size: int,
        city: str | None = None,
        locality: str | None = None,
        property_type: str | None = None,
        listing_status: str | None = None,
        rental_or_purchase: str | None = None,
        title: str | None = None,
        address: str | None = None
    ) -> tuple[list[dict[str, Any]], int, int]:
        from sqlalchemy import and_
        
        conditions = []
        if title:
            conditions.append(Property.title.ilike(f"%{title}%"))
        if address:
            conditions.append(Property.address.ilike(f"%{address}%"))
        if city:
            conditions.append(Property.city.ilike(f"%{city}%"))
        if locality:
            conditions.append(Property.locality.ilike(f"%{locality}%"))
        if property_type:
            conditions.append(Property.property_type == property_type)
        if listing_status:
            conditions.append(Property.listing_status == listing_status)
        if rental_or_purchase:
            conditions.append(Property.rental_or_purchase == rental_or_purchase)

        total_query = select(func.count()).select_from(Property)
        if conditions:
            total_query = total_query.where(and_(*conditions))
            
        total = self.db.execute(total_query).scalar_one()

        query = select(
            Property,
            func.ST_Y(cast(Property.geom, Geometry)).label("latitude"),
            func.ST_X(cast(Property.geom, Geometry)).label("longitude")
        )
        
        if conditions:
            query = query.where(and_(*conditions))
            
        query = query.order_by(Property.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        
        rows = self.db.execute(query).all()
        results = []
        for prop, lat, lng in rows:
            prop_dict = {c.name: getattr(prop, c.name) for c in prop.__table__.columns if c.name != 'geom'}
            prop_dict['property_id'] = prop_dict.pop('id')
            prop_dict['latitude'] = lat
            prop_dict['longitude'] = lng
            results.append(prop_dict)
            
        pages = ceil(total / page_size) if total else 0
        return results, total, pages

    def get_admin_by_id(self, property_id: UUID) -> dict[str, Any] | None:
        query = select(
            Property,
            func.ST_Y(cast(Property.geom, Geometry)).label("latitude"),
            func.ST_X(cast(Property.geom, Geometry)).label("longitude")
        ).where(Property.id == property_id)
        
        row = self.db.execute(query).first()
        if not row:
            return None
            
        prop, lat, lng = row
        prop_dict = {c.name: getattr(prop, c.name) for c in prop.__table__.columns if c.name != 'geom'}
        prop_dict['property_id'] = prop_dict.pop('id')
        prop_dict['latitude'] = lat
        prop_dict['longitude'] = lng
        return prop_dict

    def create_admin(self, data: AdminPropertyCreate) -> dict[str, Any]:
        property_obj = Property(
            title=data.title,
            property_type=data.property_type,
            bhk=data.bhk,
            price=data.price,
            city=data.city,
            locality=data.locality,
            address=data.address,
            furnishing=data.furnishing.value,
            amenities=data.amenities,
            area_sqft=data.area_sqft,
            floor=data.floor,
            total_floors=data.total_floors,
            rental_or_purchase=data.rental_or_purchase.value,
            listing_status=data.listing_status,
            image_urls=data.image_urls,
        )
        if data.latitude is not None and data.longitude is not None:
            property_obj.geom = cast(
                func.ST_SetSRID(func.ST_MakePoint(data.longitude, data.latitude), 4326),
                Geography(geometry_type="POINT", srid=4326)
            )
            
        self.db.add(property_obj)
        self.db.commit()
        self.db.refresh(property_obj)
        return self.get_admin_by_id(property_obj.id)

    def update_admin(self, property_id: UUID, data: AdminPropertyUpdate) -> dict[str, Any] | None:
        property_obj = self.db.get(Property, property_id)
        if not property_obj:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        
        if 'furnishing' in update_data:
            update_data['furnishing'] = update_data['furnishing'].value
        if 'rental_or_purchase' in update_data:
            update_data['rental_or_purchase'] = update_data['rental_or_purchase'].value

        has_lat = 'latitude' in update_data
        has_lng = 'longitude' in update_data
        
        if has_lat or has_lng:
            lat = update_data.pop('latitude', None)
            lng = update_data.pop('longitude', None)
            if lat is not None and lng is not None:
                property_obj.geom = cast(
                    func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326),
                    Geography(geometry_type="POINT", srid=4326)
                )

        for key, value in update_data.items():
            setattr(property_obj, key, value)
            
        self.db.commit()
        return self.get_admin_by_id(property_id)

    def delete_admin(self, property_id: UUID) -> bool:
        property_obj = self.db.get(Property, property_id)
        if not property_obj:
            return False
        self.db.delete(property_obj)
        self.db.commit()
        return True

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        return float(value)

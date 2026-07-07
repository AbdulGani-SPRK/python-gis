from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.repositories.property_repository import PropertyRepository
from app.repositories.osm_repository import OSMRepository
from app.schemas.admin_property import (
    AdminPropertyCreate,
    AdminPropertyUpdate,
    AdminPropertyResponse,
    AdminPropertyListResponse,
)

router = APIRouter(prefix="/admin/properties", tags=["admin-properties"])


def get_property_repository(db: Session = Depends(get_db)) -> PropertyRepository:
    return PropertyRepository(db)

def get_osm_repository(db: Session = Depends(get_db)) -> OSMRepository:
    return OSMRepository(db)


@router.get("", response_model=AdminPropertyListResponse, summary="List properties for admin")
def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    title: str | None = Query(None, description="Search by title (contains)"),
    address: str | None = Query(None, description="Search by address (contains)"),
    city: str | None = Query(None, description="Filter by city"),
    locality: str | None = Query(None, description="Filter by locality"),
    property_type: str | None = Query(None, description="Filter by property type"),
    listing_status: str | None = Query(None, description="Filter by listing status"),
    rental_or_purchase: str | None = Query(None, description="Filter by rental or purchase"),
    repo: PropertyRepository = Depends(get_property_repository),
):
    results, total, pages = repo.get_admin_paginated(
        page=page,
        page_size=page_size,
        title=title,
        address=address,
        city=city,
        locality=locality,
        property_type=property_type,
        listing_status=listing_status,
        rental_or_purchase=rental_or_purchase
    )
    return {
        "items": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{property_id}", response_model=AdminPropertyResponse, summary="Get property by ID")
def get_property(
    property_id: UUID,
    repo: PropertyRepository = Depends(get_property_repository),
):
    prop = repo.get_admin_by_id(property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return prop


@router.post("", response_model=AdminPropertyResponse, status_code=status.HTTP_201_CREATED, summary="Create a new property")
def create_property(
    data: AdminPropertyCreate,
    repo: PropertyRepository = Depends(get_property_repository),
):
    return repo.create_admin(data)


@router.put("/{property_id}", response_model=AdminPropertyResponse, summary="Update an existing property")
def update_property(
    property_id: UUID,
    data: AdminPropertyUpdate,
    repo: PropertyRepository = Depends(get_property_repository),
):
    prop = repo.update_admin(property_id, data)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a property")
def delete_property(
    property_id: UUID,
    repo: PropertyRepository = Depends(get_property_repository),
):
    if not repo.delete_admin(property_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")


class ReverseGeocodeResponse(BaseModel):
    locality: str | None
    city: str | None


@router.get("/resolve-location", response_model=ReverseGeocodeResponse, summary="Reverse geocode from coordinates using OSM data")
def resolve_location(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    osm_repo: OSMRepository = Depends(get_osm_repository),
):
    # This uses the existing osm db to find the locality or city boundary that contains this point
    from geoalchemy2.elements import WKTElement
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point

    point_geom = from_shape(Point(lng, lat), srid=4326)
    
    # We can use the existing find_places or resolve boundary methods to find what contains this point
    # Since we need containing polygon, we query planet_osm_polygon where boundary contains point
    from app.models.osm import OSMPolygon
    from sqlalchemy import select, func, desc
    
    query = select(OSMPolygon.name, OSMPolygon.place, OSMPolygon.boundary).where(
        func.ST_Contains(
            OSMPolygon.way, 
            func.ST_Transform(func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326), 3857)
        )
    ).where(
        OSMPolygon.name.isnot(None)
    ).order_by(
        desc(OSMPolygon.admin_level) if hasattr(OSMPolygon, 'admin_level') else desc(OSMPolygon.way_area)
    )
    
    # Try to find a locality (suburb/neighbourhood) and city (city/town)
    rows = osm_repo.db.execute(query).all()
    
    locality = None
    city = None
    
    for row in rows:
        name, place, boundary = row
        if place in ('suburb', 'neighbourhood', 'village') or (boundary == 'administrative' and not city):
            if not locality:
                locality = name
        elif place in ('city', 'town') or boundary == 'administrative':
            if not city:
                city = name
                
    return {"locality": locality, "city": city}

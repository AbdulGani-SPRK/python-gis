from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.property import FurnishingStatus, ListingPurpose


class AdminPropertyBase(BaseModel):
    title: str = Field(..., description="Headline or title of the property listing", min_length=5, max_length=300)
    property_type: str = Field(..., description="Type of property", min_length=1, max_length=50)
    bhk: int | None = Field(default=None, description="Number of bedrooms", ge=0, le=20)
    price: int = Field(..., description="Price of the property", ge=0)
    city: str = Field(..., description="City where the property is located", min_length=1, max_length=100)
    locality: str | None = Field(default=None, description="Neighborhood or locality", max_length=100)
    address: str | None = Field(default=None, description="Full address of the property")
    furnishing: FurnishingStatus = Field(default=FurnishingStatus.unfurnished, description="Furnishing status")
    amenities: list[str] = Field(default_factory=list, description="List of amenities available in the property")
    area_sqft: int | None = Field(default=None, description="Carpet area or built-up area in square feet", ge=0)
    floor: int | None = Field(default=None, description="Floor number if in a high-rise")
    total_floors: int | None = Field(default=None, description="Total floors in the building")
    rental_or_purchase: ListingPurpose = Field(default=ListingPurpose.sale, description="Purpose of listing (rent or sale)")
    listing_status: str = Field(default="active", description="Current status of the listing (e.g., active, sold, inactive)")
    image_urls: list[str] = Field(default_factory=list, description="List of image URLs for the property")
    latitude: float | None = Field(default=None, ge=-90, le=90, description="Latitude of the property")
    longitude: float | None = Field(default=None, ge=-180, le=180, description="Longitude of the property")


class AdminPropertyCreate(AdminPropertyBase):
    pass


class AdminPropertyUpdate(AdminPropertyBase):
    title: str | None = Field(default=None, min_length=5, max_length=300)
    property_type: str | None = Field(default=None, min_length=1, max_length=50)
    price: int | None = Field(default=None, ge=0)
    city: str | None = Field(default=None, min_length=1, max_length=100)


class AdminPropertyResponse(AdminPropertyBase):
    model_config = ConfigDict(from_attributes=True)

    property_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminPropertyListResponse(BaseModel):
    items: list[AdminPropertyResponse]
    total: int
    page: int
    page_size: int
    pages: int

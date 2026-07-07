from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PropertySort(StrEnum):
    relevance = "relevance"
    price_asc = "price_asc"
    price_desc = "price_desc"
    newest = "newest"
    area_desc = "area_desc"
    distance = "distance"


class ListingPurpose(StrEnum):
    rent = "rent"
    sale = "sale"


class FurnishingStatus(StrEnum):
    unfurnished = "unfurnished"
    semi_furnished = "semi_furnished"
    fully_furnished = "fully_furnished"


class PropertySearchRequest(BaseModel):
    city: str | None = Field(default=None, min_length=1, max_length=100, description="City name to search in", examples=["Mumbai"])
    locality: str | None = Field(default=None, min_length=1, max_length=100, description="Locality or neighborhood name", examples=["Bandra West"])
    property_type: str | None = Field(default=None, min_length=1, max_length=50, description="Type of the property (e.g., apartment, villa)", examples=["apartment"])
    rental_or_purchase: ListingPurpose | None = Field(default=None, description="Whether looking for rent or sale")
    budget_min: int | None = Field(default=None, ge=0, description="Minimum budget in local currency", examples=[5000000])
    budget_max: int | None = Field(default=None, ge=0, description="Maximum budget in local currency", examples=[15000000])
    bhk: int | None = Field(default=None, ge=0, le=10, description="Number of bedrooms (BHK)", examples=[2])
    furnishing: FurnishingStatus | None = Field(default=None, description="Furnishing status of the property")
    amenities: list[str] = Field(default_factory=list, max_length=30, description="List of required property amenities (e.g., pool, gym)", examples=[["gym", "swimming_pool"]])
    latitude: float | None = Field(default=None, ge=-90, le=90, description="Center latitude for spatial search", examples=[19.0760])
    longitude: float | None = Field(default=None, ge=-180, le=180, description="Center longitude for spatial search", examples=[72.8777])
    radius_m: int | None = Field(default=None, ge=100, le=50000, description="Search radius in meters from lat/lon or resolved places", examples=[2000])
    landmarks: list[str] | None = Field(default=None, description="List of landmarks to search near", examples=[["Bandra Station", "Mount Mary Church"]])
    amenities_near: list[str] | None = Field(default=None, description="List of neighborhood amenities required nearby (e.g., hospital, school)", examples=[["hospital", "park"]])
    sort: PropertySort | None = Field(default=PropertySort.relevance, description="Sorting criteria for the results")
    page: int = Field(default=1, ge=1, description="Page number for pagination")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page")

    @field_validator("city", "locality", "property_type", "rental_or_purchase", mode="before")
    @classmethod
    def normalize_blank_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator(
        "city",
        "locality",
        "property_type",
        "furnishing",
        "rental_or_purchase",
        "sort",
        mode="before"
    )
    @classmethod
    def convert_null_string(cls, v):
        if v in ("null", "NULL", "", "undefined"):
            return None
        return v

    @field_validator(
        "budget_min",
        "budget_max",
        "bhk",
        "radius_m",
        "sort",
        mode="before"
    )
    @classmethod
    def normalize_numbers(cls, v):
        if v in ("null", "", "undefined"):
            return None
        return v

    @field_validator("amenities", "landmarks", "amenities_near", mode="before")
    @classmethod
    def normalize_list_fields(cls, value: list[str] | str | None) -> list[str]:
        if not value or value in ("null", "NULL", "undefined", "", "none"):
            return []
        if isinstance(value, str):
            return [value]
        return sorted({item.strip().lower() for item in value if item and isinstance(item, str) and item.strip()})

    @model_validator(mode="after")
    def validate_ranges(self) -> "PropertySearchRequest":
        if self.budget_min is not None and self.budget_max is not None and self.budget_min > self.budget_max:
            raise ValueError("budget_min must be less than or equal to budget_max")
        has_lat = self.latitude is not None
        has_lng = self.longitude is not None
        if has_lat != has_lng:
            raise ValueError("latitude and longitude must be provided together")
        if self.sort == PropertySort.distance and not (has_lat and has_lng):
            raise ValueError("distance sorting requires latitude and longitude")
        return self


class PropertySearchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique identifier for the property")
    title: str = Field(description="Headline or title of the property listing")
    property_type: str = Field(description="Type of property")
    bhk: int | None = Field(description="Number of bedrooms")
    price: int = Field(description="Price of the property")
    city: str = Field(description="City where the property is located")
    locality: str | None = Field(description="Neighborhood or locality")
    address: str | None = Field(description="Full address of the property")
    furnishing: str | None = Field(description="Furnishing status")
    amenities: list[str] = Field(description="List of amenities available in the property")
    area_sqft: int | None = Field(description="Carpet area or built-up area in square feet")
    floor: int | None = Field(description="Floor number if in a high-rise")
    total_floors: int | None = Field(description="Total floors in the building")
    rental_or_purchase: str = Field(description="Purpose of listing (rent or sale)")
    listing_status: str | None = Field(description="Current status of the listing (e.g., active, sold)")
    image_urls: list[str] = Field(description="List of image URLs for the property")
    created_at: datetime | None = Field(description="Listing creation timestamp")
    score: float = Field(description="Ranking score assigned by the ranking engine")
    explainable_score: dict | None = Field(default=None, description="Detailed breakdown of how the score was calculated")
    distance_m: float | None = Field(default=None, description="Distance from the search center in meters, if applicable")


class PropertySearchResponse(BaseModel):
    items: list[PropertySearchItem] = Field(description="List of properties matching the search criteria")
    total: int = Field(description="Total number of matching properties across all pages")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items returned in the current page")
    pages: int = Field(description="Total number of pages available")
    applied_fallback: bool = Field(default=False, description="Whether a broader fallback search was used")
    fallback_reason: str | None = Field(default=None, description="Reason for using fallback search, if applicable")


class PropertyRecommendRequest(PropertySearchRequest):
    strategy: str | None = Field(default="hybrid", description="Recommendation strategy (e.g., hybrid, relaxed)")


class PropertyRecommendResponse(BaseModel):
    items: list[PropertySearchItem] = Field(description="List of recommended properties")
    total: int = Field(description="Total number of recommendations")
    strategy_used: str = Field(description="The strategy used to generate these recommendations")

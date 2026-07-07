from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.repositories.property_repository import PropertySearchResult
from app.schemas.property import PropertySearchRequest
from app.services.property_search_service import PropertySearchService
from app.services.ranking.ranker import RankingEngine
from app.services.spatial.place_resolver import PlaceResolverService
from app.services.spatial.query_builder import SpatialQueryBuilder
from app.schemas.spatial import SpatialContext


@dataclass
class FakeProperty:
    id: object
    title: str
    property_type: str
    bhk: int | None
    price: int
    city: str
    locality: str | None
    address: str | None
    furnishing: str | None
    amenities: list[str]
    area_sqft: int | None
    floor: int | None
    total_floors: int | None
    rental_or_purchase: str
    listing_status: str | None
    image_urls: list[str]
    created_at: datetime | None


class FakeRepository:
    def __init__(self) -> None:
        self.requests: list[PropertySearchRequest] = []

    def search(self, request: PropertySearchRequest, spatial_strategies=None) -> PropertySearchResult:
        self.requests.append(request)
        if len(self.requests) == 1:
            return PropertySearchResult(properties=[], total=0, page=request.page, page_size=request.page_size, pages=0)

        property_row = FakeProperty(
            id=uuid4(),
            title="2 BHK near IT park",
            property_type="flat",
            bhk=2,
            price=5500000,
            city="Pune",
            locality="Hinjewadi",
            address="Phase 1",
            furnishing="semi_furnished",
            amenities=["gym", "parking"],
            area_sqft=950,
            floor=7,
            total_floors=14,
            rental_or_purchase="sale",
            listing_status="active",
            image_urls=[],
            created_at=datetime.now(UTC),
        )
        return PropertySearchResult(
            properties=[(property_row, None)],
            total=1,
            page=request.page,
            page_size=request.page_size,
            pages=1,
        )


class FakePlaceResolver(PlaceResolverService):
    def __init__(self): pass
    def resolve(self, *args, **kwargs): return SpatialContext()


def test_search_expands_to_city_when_locality_has_no_matches() -> None:
    repository = FakeRepository()
    place_resolver = FakePlaceResolver()
    query_builder = SpatialQueryBuilder()
    ranking_engine = RankingEngine()
    
    service = PropertySearchService(repository, place_resolver, query_builder, ranking_engine)
    request = PropertySearchRequest(city="Pune", locality="Baner", property_type="flat")

    response = service.search(request)

    assert response.total == 1
    assert response.applied_fallback is True
    assert response.fallback_reason == "No exact locality matches; expanded search to the city."
    assert repository.requests[1].locality is None


def test_score_is_deterministic_and_capped() -> None:
    repository = FakeRepository()
    place_resolver = FakePlaceResolver()
    query_builder = SpatialQueryBuilder()
    ranking_engine = RankingEngine()
    
    service = PropertySearchService(repository, place_resolver, query_builder, ranking_engine)
    request = PropertySearchRequest(
        city="Pune",
        locality="Hinjewadi",
        property_type="flat",
        budget_min=5000000,
        budget_max=6000000,
        bhk=2,
        furnishing="semi_furnished",
        amenities=["gym", "parking"],
    )

    response = service.search(request)

    assert response.items[0].score == 100.0


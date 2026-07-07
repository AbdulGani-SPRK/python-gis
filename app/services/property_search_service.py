from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.property import PropertySearchItem, PropertySearchRequest, PropertySearchResponse

from app.core.osm_mapping import AmenityCategory
from app.schemas.spatial import SpatialContext
from app.services.ranking.ranker import RankingEngine
from app.services.spatial.place_resolver import PlaceResolverService
from app.services.spatial.query_builder import SpatialQueryBuilder

if TYPE_CHECKING:
    from app.repositories.property_repository import PropertyRepository, PropertySearchResult


class PropertySearchService:
    def __init__(
        self,
        repository: "PropertyRepository",
        place_resolver: PlaceResolverService,
        query_builder: SpatialQueryBuilder,
        ranking_engine: RankingEngine,
    ) -> None:
        self.repository = repository
        self.place_resolver = place_resolver
        self.query_builder = query_builder
        self.ranking_engine = ranking_engine

    def search(self, request: PropertySearchRequest) -> PropertySearchResponse:
        spatial_context = None
        spatial_strategies = []

        # 1. Resolve spatial context if spatial filters are provided
        if request.city and (request.landmarks or request.amenities_near):
            amenities = []
            if request.amenities_near:
                for a in request.amenities_near:
                    try:
                        amenities.append(AmenityCategory(a.lower()))
                    except ValueError:
                        pass
            
            spatial_context = self.place_resolver.resolve(
                city=request.city,
                locality=request.locality,
                landmarks=request.landmarks,
                amenities=amenities,
                search_radius_m=request.radius_m
            )
            
            # 2. Build spatial strategies
            spatial_strategies = self.query_builder.build_strategies(spatial_context)

        # 3. Execute search
        result = self.repository.search(request, spatial_strategies=spatial_strategies)
        
        applied_fallback = False
        fallback_reason = None

        if result.total == 0:
            fallback_request, fallback_reason = self._build_fallback_request(request)
            if fallback_request is not None:
                # If we fallback, we might still apply spatial strategies if it's just a budget relaxation.
                # If it's a locality relaxation, we'd ideally re-resolve spatial context without locality,
                # but to keep it simple, we just re-run with existing strategies or ignore them.
                # Let's just re-run with existing for now.
                result = self.repository.search(fallback_request, spatial_strategies=spatial_strategies)
                applied_fallback = result.total > 0

        return self._to_response(result, request, spatial_context, applied_fallback, fallback_reason if applied_fallback else None)

    def _build_fallback_request(self, request: PropertySearchRequest) -> tuple[PropertySearchRequest | None, str | None]:
        if request.locality:
            return request.model_copy(update={"locality": None, "page": 1}), "No exact locality matches; expanded search to the city."
        if request.budget_max is not None:
            relaxed_budget = int(request.budget_max * 1.15)
            return request.model_copy(update={"budget_max": relaxed_budget, "page": 1}), "No budget matches; relaxed maximum budget by 15%."
        return None, None

    def _to_response(
        self,
        result: PropertySearchResult,
        request: PropertySearchRequest,
        spatial_context: SpatialContext | None,
        applied_fallback: bool,
        fallback_reason: str | None,
    ) -> PropertySearchResponse:
        items = []
        for property_row, distance_m in result.properties:
            # Set distance on row for ranking if it was calculated by DB
            if distance_m is not None:
                setattr(property_row, "distance_m", distance_m)
                
            explanation = self.ranking_engine.score(property_row, request, spatial_context)
            
            items.append(
                PropertySearchItem(
                    id=property_row.id,
                    title=property_row.title,
                    property_type=property_row.property_type,
                    bhk=property_row.bhk,
                    price=property_row.price,
                    city=property_row.city,
                    locality=property_row.locality,
                    address=property_row.address,
                    furnishing=property_row.furnishing,
                    amenities=property_row.amenities or [],
                    area_sqft=property_row.area_sqft,
                    floor=property_row.floor,
                    total_floors=property_row.total_floors,
                    rental_or_purchase=property_row.rental_or_purchase,
                    listing_status=property_row.listing_status,
                    image_urls=property_row.image_urls or [],
                    created_at=property_row.created_at,
                    score=explanation.total_score,
                    explainable_score=explanation.factors,
                    distance_m=distance_m,
                )
            )
            
        return PropertySearchResponse(
            items=items,
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            pages=result.pages,
            applied_fallback=applied_fallback,
            fallback_reason=fallback_reason,
        )

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.property import (
    PropertyRecommendRequest,
    PropertyRecommendResponse,
    PropertySearchItem,
)
from app.services.property_search_service import PropertySearchService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.repositories.property_repository import PropertyRepository
    from app.services.spatial.place_resolver import PlaceResolverService
    from app.services.spatial.query_builder import SpatialQueryBuilder
    from app.services.ranking.ranker import RankingEngine


class PropertyRecommendationService:
    def __init__(self, search_service: PropertySearchService) -> None:
        self.search_service = search_service

    def recommend(self, request: PropertyRecommendRequest) -> PropertyRecommendResponse:
        # For recommendations, we might want to relax constraints automatically
        # to ensure we return options.
        
        # We'll use the underlying search service for heavy lifting.
        search_request = request.model_copy()
        
        if request.strategy == "relaxed":
            # Relax budget significantly
            if search_request.budget_max is not None:
                search_request.budget_max = int(search_request.budget_max * 1.30)
            # Remove strict locality requirements for recommendations
            search_request.locality = None
            search_request.radius_m = (search_request.radius_m or 3000) * 2

        # Execute search
        search_response = self.search_service.search(search_request)

        # We might want to re-sort or filter here, but we rely on the RankingEngine
        # which search_service already uses.

        return PropertyRecommendResponse(
            items=search_response.items,
            total=search_response.total,
            strategy_used=request.strategy or "hybrid",
        )

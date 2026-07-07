from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import time

from app.core.database import get_db
from app.schemas.property import (
    PropertySearchRequest,
    PropertySearchResponse,
    PropertyRecommendRequest,
    PropertyRecommendResponse,
)

router = APIRouter(prefix="/properties", tags=["properties"])


def get_property_search_service(db: Session = Depends(get_db)) -> "PropertySearchService":
    from app.repositories.property_repository import PropertyRepository
    from app.repositories.osm_repository import OSMRepository
    from app.services.property_search_service import PropertySearchService
    from app.services.spatial.place_resolver import PlaceResolverService
    from app.services.spatial.query_builder import SpatialQueryBuilder
    from app.services.ranking.ranker import RankingEngine

    repository = PropertyRepository(db)
    osm_repo = OSMRepository(db)
    place_resolver = PlaceResolverService(osm_repo)
    query_builder = SpatialQueryBuilder()
    ranking_engine = RankingEngine()
    
    return PropertySearchService(repository, place_resolver, query_builder, ranking_engine)


def get_property_recommendation_service(
    search_service: "PropertySearchService" = Depends(get_property_search_service)
) -> "PropertyRecommendationService":
    from app.services.property_recommendation_service import PropertyRecommendationService
    return PropertyRecommendationService(search_service)

@router.post(
    "/search",
    response_model=PropertySearchResponse,
    summary="Search for properties",
    description="""
Search for real estate properties using a combination of textual, filter, and spatial criteria. 

This endpoint integrates with OpenStreetMap (OSM) to allow searching for properties near specific landmarks or amenities (e.g., 'properties near hospital in Bandra').
It supports fallback logic if no exact matches are found and returns a ranked list of properties.
    """,
    response_description="A paginated list of properties with their calculated relevance scores."
)
def search_properties(
    request: PropertySearchRequest,
    service: "PropertySearchService" = Depends(get_property_search_service),
) -> PropertySearchResponse:
    return service.search(request)


@router.post(
    "/recommend",
    response_model=PropertyRecommendResponse,
    summary="Get property recommendations",
    description="""
    Get personalized property recommendations based on user preferences.
    Can relax constraints like budget or locality depending on the strategy.
    """,
    response_description="A list of recommended properties."
)
def recommend_properties(
    request: PropertyRecommendRequest,
    service: "PropertyRecommendationService" = Depends(get_property_recommendation_service),
) -> PropertyRecommendResponse:
    return service.recommend(request)


from fastapi.responses import PlainTextResponse

@router.post(
    "/search/agent",
    response_class=PlainTextResponse,
    summary="Search for properties (Agent)",
    description="Returns plain text JSON for LLM agents to bypass n8n httpRequestTool bugs.",
    include_in_schema=False
)
def search_properties_agent(
    request: PropertySearchRequest,
    service: "PropertySearchService" = Depends(get_property_search_service),
) -> PlainTextResponse:
    with open("agent_request.log", "a") as f:
        f.write(f"AGENT SEARCH REQUEST: {request.model_dump_json()}\n")
    print(f"AGENT SEARCH REQUEST: {request.model_dump_json()}")
    res = service.search(request)
    return PlainTextResponse(content=f"<result>\n{res.model_dump_json()}\n</result>")


@router.post(
    "/recommend/agent",
    response_class=PlainTextResponse,
    summary="Get property recommendations (Agent)",
    description="Returns plain text JSON for LLM agents to bypass n8n httpRequestTool bugs.",
    include_in_schema=False
)
def recommend_properties_agent(
    request: PropertyRecommendRequest,
    service: "PropertyRecommendationService" = Depends(get_property_recommendation_service),
) -> PlainTextResponse:
    res = service.recommend(request)
    return PlainTextResponse(content=f"<result>\n{res.model_dump_json()}\n</result>")


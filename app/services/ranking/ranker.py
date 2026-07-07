from typing import Protocol

from app.schemas.property import PropertySearchRequest
from app.schemas.ranking import ScoreExplanation
from app.schemas.spatial import SpatialContext


class Ranker(Protocol):
    def score(self, property_row: object, request: PropertySearchRequest, spatial_context: SpatialContext | None = None) -> dict[str, float]:
        ...


class BaseRanker:
    def score(self, property_row: object, request: PropertySearchRequest, spatial_context: SpatialContext | None = None) -> dict[str, float]:
        factors = {}
        price = getattr(property_row, "price", 0)
        amenities = set(getattr(property_row, "amenities") or [])
        
        if request.budget_min is not None and price >= request.budget_min:
            factors["Base Budget Match (Min)"] = 8.0
        if request.budget_max is not None and price <= request.budget_max:
            factors["Base Budget Match (Max)"] = 12.0
            
        if request.locality and getattr(property_row, "locality", None) and property_row.locality.lower() == request.locality.lower():
            factors["Locality Exact Match"] = 12.0
            
        property_city = getattr(property_row, "city", None)
        if request.city and property_city and property_city.lower() == request.city.lower():
            factors["City Exact Match"] = 8.0
            
        if request.bhk is not None and getattr(property_row, "bhk", None) == request.bhk:
            factors["BHK Match"] = 8.0
            
        if request.furnishing and getattr(property_row, "furnishing", None) == request.furnishing.value:
            factors["Furnishing Match"] = 5.0
            
        if request.amenities:
            matched = len(set(request.amenities).intersection(amenities))
            factors["Property Amenities Match"] = 15.0 * (matched / len(request.amenities))
            
        return factors


class GISRanker:
    def score(self, property_row: object, request: PropertySearchRequest, spatial_context: SpatialContext | None = None) -> dict[str, float]:
        factors = {}
        if not spatial_context or not spatial_context.resolved_places:
            return factors

        # property_row might have a distance_m attribute added during query execution if sorting by distance.
        # But we don't have access to dynamic distance here unless passed.
        # Let's check if distance_m is available on the row.
        distance_m = getattr(property_row, "distance_m", None)
        
        # If we have a generic search, distance_m could be the minimum distance to the requested places.
        if distance_m is not None and spatial_context.search_radius_m:
            score = max(0.0, 15.0 * (1.0 - (distance_m / spatial_context.search_radius_m)))
            factors["Proximity to Resolved Places"] = round(score, 2)
            
        # We can add bonus points for multiple resolved places
        num_places = len(spatial_context.resolved_places)
        if num_places > 1:
            factors["Multiple Amenities Bonus"] = min(10.0, num_places * 2.0)
            
        return factors


class RankingEngine:
    def __init__(self):
        self.rankers: list[Ranker] = [BaseRanker(), GISRanker()]

    def score(self, property_row: object, request: PropertySearchRequest, spatial_context: SpatialContext | None = None) -> ScoreExplanation:
        factors = {}
        total = 50.0  # Base score
        factors["Base Score"] = 50.0
        
        for ranker in self.rankers:
            ranker_factors = ranker.score(property_row, request, spatial_context)
            for k, v in ranker_factors.items():
                factors[k] = v
                total += v
                
        # Cap at 100
        # total = min(total, 100.0) 
        # But explainable scores shouldn't necessarily be capped, or we can cap the total and add an adjustment factor
        if total > 100.0:
            adjustment = 100.0 - total
            factors["Cap Adjustment"] = round(adjustment, 2)
            total = 100.0
            
        return ScoreExplanation(
            total_score=round(total, 2),
            factors=factors
        )

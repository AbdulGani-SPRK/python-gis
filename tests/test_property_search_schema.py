import pytest
from pydantic import ValidationError

from app.schemas.property import PropertySearchRequest, PropertySort


def test_search_request_normalizes_amenities() -> None:
    request = PropertySearchRequest(city=" Pune ", amenities=["Gym", " gym ", "Parking"])

    assert request.city == "Pune"
    assert request.amenities == ["gym", "parking"]


def test_budget_min_cannot_exceed_budget_max() -> None:
    with pytest.raises(ValidationError):
        PropertySearchRequest(budget_min=9000000, budget_max=5000000)


def test_distance_sort_requires_coordinates() -> None:
    with pytest.raises(ValidationError):
        PropertySearchRequest(sort=PropertySort.distance)


def test_latitude_and_longitude_must_be_provided_together() -> None:
    with pytest.raises(ValidationError):
        PropertySearchRequest(latitude=18.5204)


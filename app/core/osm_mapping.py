from enum import StrEnum

class AmenityCategory(StrEnum):
    METRO = "metro"
    RAILWAY = "railway"
    HOSPITAL = "hospital"
    MALL = "mall"
    SCHOOL = "school"
    PARK = "park"
    OFFICE = "office"
    BUS_STOP = "bus_stop"
    AIRPORT = "airport"


OSM_CATEGORY_MAP: dict[AmenityCategory, list[dict[str, str]]] = {
    AmenityCategory.METRO: [{"railway": "station"}, {"public_transport": "station"}],
    AmenityCategory.RAILWAY: [{"railway": "station"}],
    AmenityCategory.HOSPITAL: [{"amenity": "hospital"}, {"amenity": "clinic"}],
    AmenityCategory.MALL: [{"shop": "mall"}],
    AmenityCategory.SCHOOL: [{"amenity": "school"}],
    AmenityCategory.PARK: [{"leisure": "park"}],
    AmenityCategory.OFFICE: [{"office": "yes"}, {"office": "company"}, {"building": "office"}],
    AmenityCategory.BUS_STOP: [{"highway": "bus_stop"}],
    AmenityCategory.AIRPORT: [{"aeroway": "terminal"}, {"aeroway": "aerodrome"}],
}

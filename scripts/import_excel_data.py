import asyncio
import logging
import time
import httpx
import pandas as pd
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_engine
from app.models.property import Property

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Simple in-memory cache to avoid hammering Nominatim for the same locality
GEOCODE_CACHE: dict[str, tuple[float, float] | None] = {}

def geocode_locality(locality: str, city: str) -> tuple[float, float] | None:
    """Fetch coordinates from Nominatim API with caching and polite delays."""
    search_query = f"{locality}, {city}, India"
    
    if search_query in GEOCODE_CACHE:
        return GEOCODE_CACHE[search_query]

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": search_query,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "PropertyConsultantAgent/1.0 (test_geocoding)"
    }
    
    logger.info(f"Geocoding: {search_query}")
    try:
        response = httpx.get(url, params=params, headers=headers, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        # Nominatim asks for 1 second between requests
        time.sleep(1.2)
        
        if data and len(data) > 0:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            GEOCODE_CACHE[search_query] = (lat, lon)
            return lat, lon
        else:
            # Fallback to just city
            logger.warning(f"Could not find exact match for {search_query}, trying just city...")
            fallback_query = f"{city}, India"
            if fallback_query in GEOCODE_CACHE:
                return GEOCODE_CACHE[fallback_query]
                
            response = httpx.get(url, params={"q": fallback_query, "format": "json", "limit": 1}, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            time.sleep(1.2)
            
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                GEOCODE_CACHE[fallback_query] = (lat, lon)
                GEOCODE_CACHE[search_query] = (lat, lon) # Cache fallback for this locality too
                return lat, lon
            
    except Exception as e:
        logger.error(f"Error geocoding {search_query}: {e}")
    
    GEOCODE_CACHE[search_query] = None
    return None


def main():
    logger.info("Loading propertydata.xlsx...")
    try:
        df = pd.read_excel("propertydata.xlsx")
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        return

    # 1. Clean missing prices
    original_count = len(df)
    df = df.dropna(subset=["sale_price_in_INR"])
    logger.info(f"Dropped {original_count - len(df)} rows with missing prices. {len(df)} rows remain.")

    # 2. Iterate and Insert
    inserted_count = 0
    
    with SessionLocal(bind=get_engine()) as db:
        for idx, row in df.iterrows():
            city = str(row.get("city", "Noida")).strip()
            locality = str(row.get("locality", "")).strip()
            if locality == "nan" or not locality:
                locality = city
                
            price = int(float(row["sale_price_in_INR"]))
            
            # Clean area
            area_val = row.get("area_value_in_sqft")
            try:
                area_sqft = int(float(area_val))
            except (ValueError, TypeError):
                area_sqft = None
                
            title = f"{row.get('type', 'Property')} in {locality}"
            
            # Get coordinates
            coords = geocode_locality(locality, city)
            
            geom = None
            if coords:
                lat, lon = coords
                # PostGIS POINT format is "POINT(lon lat)"
                geom = WKTElement(f"POINT({lon} {lat})", srid=4326)
            
            property_obj = Property(
                title=title,
                property_type=str(row.get("type", "apartment")),
                price=price,
                city=city,
                locality=locality,
                area_sqft=area_sqft,
                rental_or_purchase="sale",
                geom=geom,
                # Fill some defaults for missing fields
                bhk=3 if "3" in str(row.get("sub_type", "")) else 2,
                listing_status="active",
            )
            
            db.add(property_obj)
            inserted_count += 1
            
            # Commit every 50 rows
            if inserted_count % 50 == 0:
                db.commit()
                logger.info(f"Inserted {inserted_count} properties...")
                
        # Final commit
        db.commit()
        logger.info(f"Successfully finished importing {inserted_count} properties.")

if __name__ == "__main__":
    main()

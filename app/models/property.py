from datetime import datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)
    bhk: Mapped[int | None] = mapped_column(SmallInteger)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    locality: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    furnishing: Mapped[str | None] = mapped_column(String(50), server_default="unfurnished")
    amenities: Mapped[list[str]] = mapped_column(JSONB, server_default="[]")
    area_sqft: Mapped[int | None] = mapped_column(Integer)
    floor: Mapped[int | None] = mapped_column(SmallInteger)
    total_floors: Mapped[int | None] = mapped_column(SmallInteger)
    rental_or_purchase: Mapped[str] = mapped_column(String(20), nullable=False, server_default="sale")
    listing_status: Mapped[str | None] = mapped_column(String(20), server_default="active")
    geom: Mapped[Any | None] = mapped_column(Geography(geometry_type="POINT", srid=4326))
    image_urls: Mapped[list[str]] = mapped_column(JSONB, server_default="[]")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())


from typing import Any
from geoalchemy2 import Geography, Geometry
from sqlalchemy import BigInteger, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OSMBase(Base):
    __abstract__ = True
    # osm2pgsql uses negative IDs for relations, positive for ways/nodes.
    osm_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    amenity: Mapped[str | None] = mapped_column(Text)
    leisure: Mapped[str | None] = mapped_column(Text)
    building: Mapped[str | None] = mapped_column(Text)
    shop: Mapped[str | None] = mapped_column(Text)
    public_transport: Mapped[str | None] = mapped_column(Text)
    railway: Mapped[str | None] = mapped_column(Text)
    office: Mapped[str | None] = mapped_column(Text)
    boundary: Mapped[str | None] = mapped_column(Text)
    place: Mapped[str | None] = mapped_column(Text)


class OSMPoint(OSMBase):
    __tablename__ = "planet_osm_point"
    __table_args__ = {"schema": "osm"}

    # way is standard in osm2pgsql, but sometimes it's geometry type
    way: Mapped[Any] = mapped_column(Geometry(geometry_type="POINT", srid=3857))


class OSMPolygon(OSMBase):
    __tablename__ = "planet_osm_polygon"
    __table_args__ = {"schema": "osm"}

    way: Mapped[Any] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=3857))
    way_area: Mapped[float | None] = mapped_column(Float)


class OSMLine(OSMBase):
    __tablename__ = "planet_osm_line"
    __table_args__ = {"schema": "osm"}

    highway: Mapped[str | None] = mapped_column(Text)
    way: Mapped[Any] = mapped_column(Geometry(geometry_type="LINESTRING", srid=3857))

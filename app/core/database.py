import logging
from collections.abc import Generator

import sqlparse
from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            str(settings.database_url),
            # Disable SQLAlchemy's default unformatted echo if we are manually formatting
            echo=False, 
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
        )

        if settings.sql_echo:
            # Create a dedicated logger for SQL queries
            sql_logger = logging.getLogger("sqlalchemy.engine.Engine")
            sql_logger.setLevel(logging.INFO)

            @event.listens_for(_engine, "before_cursor_execute")
            def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                formatted_sql = sqlparse.format(
                    statement, reindent=True, keyword_case="upper"
                )
                print(f"\n\033[94m[SQL QUERY]\033[0m\n{formatted_sql}")
                if parameters:
                    print(f"\033[93m[PARAMETERS]\033[0m {parameters}\n")

    return _engine


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal(bind=get_engine())
    try:
        yield db
    finally:
        db.close()


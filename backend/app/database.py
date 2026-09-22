from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Lightweight idempotent column additions for databases created before the
# fragile-isolation feature. create_all() never alters existing tables.
# Maps table -> (column, column DDL fragment).
_EXTRA_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "subscriber_stops": [("fragile", "fragile BOOLEAN NOT NULL DEFAULT FALSE")],
    "pack_bags": [
        ("bag_kind", "bag_kind VARCHAR(16) NOT NULL DEFAULT 'normal'"),
        ("opened_reason", "opened_reason VARCHAR(16) NOT NULL DEFAULT 'first'"),
    ],
    "reject_records": [("kind", "kind VARCHAR(16) NOT NULL DEFAULT 'oversize'")],
}


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    existing = {t: {c["name"] for c in inspector.get_columns(t)}
                for t in _EXTRA_COLUMNS if inspector.has_table(t)}
    with engine.begin() as conn:
        for table, cols in _EXTRA_COLUMNS.items():
            for name, ddl in cols:
                if name not in existing.get(table, set()):
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

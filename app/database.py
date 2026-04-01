import os
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text, create_engine, text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./churchevents.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class ZipLookup(Base):
    __tablename__ = "zip_lookups"

    zip_code = Column(String(10), primary_key=True)
    city = Column(String(200))
    state = Column(String(50))
    churches_updated_at = Column(DateTime, nullable=True)

    churches = relationship("Church", back_populates="zip_lookup", cascade="all, delete-orphan")


class Church(Base):
    __tablename__ = "churches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zip_code = Column(String(10), ForeignKey("zip_lookups.zip_code", ondelete="CASCADE"), nullable=False)
    name = Column(String(500), nullable=False)
    denomination = Column(String(200))
    address = Column(String(500))
    discovered_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)
    links_updated_at = Column(DateTime, nullable=True)

    zip_lookup = relationship("ZipLookup", back_populates="churches")
    links = relationship("ChurchLink", back_populates="church", cascade="all, delete-orphan")
    events = relationship("ChurchEvent", back_populates="church", cascade="all, delete-orphan")


class ChurchLink(Base):
    __tablename__ = "church_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    church_id = Column(Integer, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=False)
    platform = Column(String(50))
    discovered_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)
    events_scraped_at = Column(DateTime, nullable=True)

    church = relationship("Church", back_populates="links")
    events = relationship("ChurchEvent", back_populates="source_link", cascade="all, delete-orphan")


class ChurchEvent(Base):
    __tablename__ = "church_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    church_id = Column(Integer, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False)
    source_link_id = Column(Integer, ForeignKey("church_links.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    event_date = Column(String(20))
    event_time = Column(String(50))
    location = Column(String(500))
    image_url = Column(Text)
    source_url = Column(Text)

    church = relationship("Church", back_populates="events")
    source_link = relationship("ChurchLink", back_populates="events")


def create_tables():
    Base.metadata.create_all(bind=engine)

    _pending_migrations = [
        "ALTER TABLE churches ADD COLUMN discovered_at TIMESTAMP",
        "ALTER TABLE churches ADD COLUMN last_seen_at TIMESTAMP",
        "ALTER TABLE church_links ADD COLUMN discovered_at TIMESTAMP",
        "ALTER TABLE church_links ADD COLUMN last_seen_at TIMESTAMP",
    ]
    with engine.connect() as conn:
        for stmt in _pending_migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

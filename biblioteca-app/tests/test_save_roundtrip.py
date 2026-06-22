"""Test round-trip salvare în SQLite (in-memory)."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base, EvidentaUtilizatori


def test_evidenta_utilizatori_roundtrip():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    row_data = {
        "an": 2025,
        "luna": 3,
        "data": "03.03",
        "adulti": 10,
        "copii_pana_16": 5,
    }

    with SessionLocal() as session:
        session.add(EvidentaUtilizatori(**row_data))
        session.commit()

    with SessionLocal() as session:
        rec = session.scalar(
            select(EvidentaUtilizatori).where(
                EvidentaUtilizatori.an == 2025,
                EvidentaUtilizatori.luna == 3,
                EvidentaUtilizatori.data == "03.03",
            )
        )
        assert rec is not None
        assert rec.adulti == 10
        assert rec.copii_pana_16 == 5

        rec.adulti = 15
        session.commit()

    with SessionLocal() as session:
        rec = session.scalar(select(EvidentaUtilizatori).where(EvidentaUtilizatori.id == 1))
        assert rec.adulti == 15

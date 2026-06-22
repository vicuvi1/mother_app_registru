"""Teste audit registru — luni incomplete."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core import register_audit as audit_mod
from core.register_audit import find_incomplete_months
from database.models import Base, EvidentaUtilizatori


@pytest.fixture
def audit_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def _get_session():
        return Session()

    monkeypatch.setattr(audit_mod, "get_session", _get_session)
    yield Session


def test_find_incomplete_daily_month(audit_session):
    Session = audit_session
    with Session() as session:
        session.add(
            EvidentaUtilizatori(
                an=2026,
                luna=1,
                data="2026-01-02",
                adulti=1,
            )
        )
        session.commit()

    slots = find_incomplete_months(2026)
    part01_jan = [s for s in slots if s.part_id == "part_01" and s.month == 1]
    part01_feb = [s for s in slots if s.part_id == "part_01" and s.month == 2]
    assert part01_jan == []
    assert len(part01_feb) == 1


def test_empty_year_all_daily_incomplete(audit_session):
    slots = find_incomplete_months(2025)
    part01 = [s for s in slots if s.part_id == "part_01"]
    assert len(part01) == 12

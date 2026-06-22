"""Teste agregare SQL pentru totaluri cumulative."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, EvidentaUtilizatori


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        s.add_all([
            EvidentaUtilizatori(an=2025, luna=1, data="02.01", adulti=5),
            EvidentaUtilizatori(an=2025, luna=2, data="03.02", adulti=7),
        ])
        s.commit()
        yield s


def test_prior_months_sum(session):
    from sqlalchemy import and_, case, func, select

    row = session.execute(
        select(func.coalesce(func.sum(EvidentaUtilizatori.adulti), 0)).where(
            and_(EvidentaUtilizatori.an == 2025, EvidentaUtilizatori.luna < 2)
        )
    ).scalar_one()
    assert row == 5

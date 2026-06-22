"""Conexiune SQLite, inițializare schema și operații comune."""

import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from database.models import AppSetting, Base
from database.migrations import run_migrations
from database.seed_defaults import seed_all_defaults

# Calea DB conform SPEC secțiunea 2: app/data/biblioteca.db
APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "biblioteca.db"

_engine = None
_SessionLocal = None
logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    return DB_PATH


def get_engine():
    global _engine
    if _engine is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        with _engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()
        logger.info("Bază de date inițializată (WAL): %s", DB_PATH)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_session() -> Session:
    return get_session_factory()()


def init_database(seed: bool = True) -> None:
    """Creează toate tabelele și populează datele default la prima rulare."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    run_migrations()

    if seed:
        with get_session() as session:
            seed_all_defaults(session)
            session.commit()


def is_first_run() -> bool:
    """True dacă setup-ul inițial nu a fost finalizat."""
    return get_setting("setup_completed") != "1"


def mark_setup_completed() -> None:
    with get_session() as session:
        setting = session.get(AppSetting, "setup_completed")
        if setting:
            setting.valoare = "1"
        else:
            session.add(AppSetting(cheie="setup_completed", valoare="1"))
        session.commit()


def get_setting(cheie: str, default: str | None = None) -> str | None:
    with get_session() as session:
        setting = session.get(AppSetting, cheie)
        return setting.valoare if setting else default


def set_setting(cheie: str, valoare: str) -> None:
    with get_session() as session:
        setting = session.get(AppSetting, cheie)
        if setting:
            setting.valoare = valoare
        else:
            session.add(AppSetting(cheie=cheie, valoare=valoare))
        session.commit()

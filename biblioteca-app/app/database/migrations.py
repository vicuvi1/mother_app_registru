"""Migrări schema SQLite (coloane noi fără pierdere date)."""

from sqlalchemy import inspect, text

from database.models import EtichetaCustom
from database.seed_defaults import DEFAULT_ETICHETE


def _engine():
    from database.db_manager import get_engine
    return get_engine()


def _table_columns(table: str) -> set[str]:
    insp = inspect(_engine())
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _add_column(table: str, column: str, col_type: str) -> None:
    cols = _table_columns(table)
    if column in cols:
        return
    with _engine().connect() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        conn.commit()


def migrate_part05_columns() -> None:
    """Aliniază Partea V la structura registrului fizic."""
    table = "cercetari_bibliografice"
    if table not in inspect(_engine()).get_table_names():
        return

    for col, typ in (
        ("date_despre_solicitant", "TEXT"),
        ("referinta", "TEXT"),
        ("cercetare_bibliografica", "TEXT"),
        ("consultatie", "TEXT"),
        ("referinta_tematica", "TEXT"),
        ("referinta_de_concretizare", "TEXT"),
        ("referinta_de_adresa", "TEXT"),
        ("referinta_factologie", "TEXT"),
        ("limite_cronologice", "TEXT"),
    ):
        _add_column(table, col, typ)

    with _engine().connect() as conn:
        conn.execute(
            text(
                "UPDATE cercetari_bibliografice SET referinta = tema "
                "WHERE (referinta IS NULL OR referinta = '') AND tema IS NOT NULL AND tema != ''"
            )
        )
        conn.execute(
            text(
                "UPDATE cercetari_bibliografice SET referinta_tematica = tip_referinta_grup "
                "WHERE (referinta_tematica IS NULL OR referinta_tematica = '') "
                "AND tip_referinta_grup IS NOT NULL AND tip_referinta_grup != ''"
            )
        )
        conn.execute(
            text(
                "UPDATE cercetari_bibliografice SET cercetare_bibliografica = tip_referinta_bibliografica "
                "WHERE (cercetare_bibliografica IS NULL OR cercetare_bibliografica = '') "
                "AND tip_referinta_bibliografica = 'Cercetare bibliografică'"
            )
        )
        conn.execute(
            text(
                "UPDATE cercetari_bibliografice SET consultatie = tip_referinta_bibliografica "
                "WHERE (consultatie IS NULL OR consultatie = '') "
                "AND tip_referinta_bibliografica = 'Consultație'"
            )
        )
        conn.commit()


def migrate_etichete_for_part(parte: str) -> None:
    """Adaugă etichete lipsă pentru o parte."""
    from sqlalchemy import select

    from database.db_manager import get_session

    for camp, default_label in DEFAULT_ETICHETE.get(parte, []):
        with get_session() as session:
            exists = session.scalar(
                select(EtichetaCustom.id).where(
                    EtichetaCustom.parte == parte,
                    EtichetaCustom.camp == camp,
                ).limit(1)
            )
            if exists is None:
                session.add(
                    EtichetaCustom(
                        parte=parte,
                        camp=camp,
                        eticheta_default=default_label,
                        eticheta_custom=None,
                    )
                )
                session.commit()


def migrate_etichete_part05() -> None:
    migrate_etichete_for_part("part_05")


def migrate_part06_columns() -> None:
    """Aliniază Partea VI — gen activitate pe 3 subcoloane."""
    table = "activitati_informare"
    if table not in inspect(_engine()).get_table_names():
        return

    for col, typ in (
        ("activitate_individuala", "TEXT"),
        ("activitate_grup", "TEXT"),
        ("activitate_public_larg", "TEXT"),
    ):
        _add_column(table, col, typ)

    with _engine().connect() as conn:
        conn.execute(
            text(
                "UPDATE activitati_informare SET data = '_r' || id "
                "WHERE data IS NULL OR data = ''"
            )
        )
        conn.execute(
            text(
                "UPDATE activitati_informare SET activitate_individuala = gen_activitate "
                "WHERE (activitate_individuala IS NULL OR activitate_individuala = '') "
                "AND gen_activitate IS NOT NULL AND gen_activitate != '' "
                "AND (gen_activitate LIKE '%Individual%' OR gen_activitate LIKE '%DSI%')"
            )
        )
        conn.execute(
            text(
                "UPDATE activitati_informare SET activitate_grup = gen_activitate "
                "WHERE (activitate_grup IS NULL OR activitate_grup = '') "
                "AND gen_activitate IS NOT NULL AND gen_activitate != '' "
                "AND gen_activitate LIKE '%grup%'"
            )
        )
        conn.execute(
            text(
                "UPDATE activitati_informare SET activitate_public_larg = gen_activitate "
                "WHERE (activitate_public_larg IS NULL OR activitate_public_larg = '') "
                "AND gen_activitate IS NOT NULL AND gen_activitate != '' "
                "AND (gen_activitate LIKE '%public%' OR gen_activitate LIKE '%Informare%')"
            )
        )
        conn.commit()


def migrate_etichete_part06() -> None:
    migrate_etichete_for_part("part_06")


def run_migrations() -> None:
    migrate_part05_columns()
    migrate_etichete_part05()
    migrate_part06_columns()
    migrate_etichete_part06()

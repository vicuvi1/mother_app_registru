"""Migrări schema SQLite (coloane noi fără pierdere date)."""
from __future__ import annotations

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


def sync_etichete_defaults(parte: str, *, reset_obsolete_custom: bool = False) -> None:
    """Actualizează eticheta_default din seed; opțional resetează custom vechi."""
    from sqlalchemy import select

    from database.db_manager import get_session

    obsolete = {"Feminin", "Masculin", "Femin", "Masculin"}
    for camp, default_label in DEFAULT_ETICHETE.get(parte, []):
        with get_session() as session:
            row = session.scalar(
                select(EtichetaCustom).where(
                    EtichetaCustom.parte == parte,
                    EtichetaCustom.camp == camp,
                )
            )
            if row is None:
                session.add(
                    EtichetaCustom(
                        parte=parte,
                        camp=camp,
                        eticheta_default=default_label,
                        eticheta_custom=None,
                    )
                )
            else:
                old_default = row.eticheta_default
                row.eticheta_default = default_label
                if reset_obsolete_custom:
                    custom = (row.eticheta_custom or "").strip()
                    if custom in obsolete or custom == old_default:
                        row.eticheta_custom = None
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


def migrate_part09_part12_gender_columns() -> None:
    """Coloane masculin/feminin pentru Părțile IX și XII."""
    _add_column("instruiri", "participanti_masculin", "INTEGER DEFAULT 0")
    _add_column("instruiri", "participanti_feminin", "INTEGER DEFAULT 0")
    _add_column("activitati_online", "participanti_masculin", "INTEGER DEFAULT 0")
    _add_column("activitati_online", "participanti_feminin", "INTEGER DEFAULT 0")

    if "instruiri" in inspect(_engine()).get_table_names():
        with _engine().connect() as conn:
            conn.execute(
                text(
                    "UPDATE instruiri SET participanti_masculin = adulti "
                    "WHERE participanti_masculin = 0 AND adulti > 0"
                )
            )
            conn.execute(
                text(
                    "UPDATE instruiri SET participanti_feminin = copii_pana_16 "
                    "WHERE participanti_feminin = 0 AND copii_pana_16 > 0"
                )
            )
            conn.commit()

    if "activitati_online" in inspect(_engine()).get_table_names():
        with _engine().connect() as conn:
            conn.execute(
                text(
                    "UPDATE activitati_online SET participanti_masculin = participanti_adulti "
                    "WHERE participanti_masculin = 0 AND participanti_adulti > 0"
                )
            )
            conn.execute(
                text(
                    "UPDATE activitati_online SET participanti_feminin = participanti_copii "
                    "WHERE participanti_feminin = 0 AND participanti_copii > 0"
                )
            )
            conn.commit()


def migrate_etichete_part09_part12() -> None:
    migrate_etichete_for_part("part_09")
    migrate_etichete_for_part("part_12")


def migrate_part06_part11_gender_columns() -> None:
    """Coloane masculin/feminin pentru Părțile VI și XI."""
    _add_column("activitati_informare", "participanti_masculin", "INTEGER DEFAULT 0")
    _add_column("activitati_informare", "participanti_feminin", "INTEGER DEFAULT 0")
    _add_column("activitati_culturale", "participanti_masculin", "INTEGER DEFAULT 0")
    _add_column("activitati_culturale", "participanti_feminin", "INTEGER DEFAULT 0")

    if "activitati_informare" in inspect(_engine()).get_table_names():
        with _engine().connect() as conn:
            conn.execute(
                text(
                    "UPDATE activitati_informare SET participanti_masculin = numar_participanti "
                    "WHERE participanti_masculin = 0 AND participanti_feminin = 0 "
                    "AND numar_participanti > 0"
                )
            )
            conn.commit()

    if "activitati_culturale" in inspect(_engine()).get_table_names():
        with _engine().connect() as conn:
            conn.execute(
                text(
                    "UPDATE activitati_culturale SET participanti_masculin = total_participanti "
                    "WHERE participanti_masculin = 0 AND participanti_feminin = 0 "
                    "AND total_participanti > 0"
                )
            )
            conn.commit()


def migrate_etichete_part06_part11() -> None:
    migrate_etichete_for_part("part_06")
    migrate_etichete_for_part("part_11")


def migrate_part09_prescolari_elevi() -> None:
    """Preșcolari și elevi în Participanți — Partea IX (conform registrului fizic)."""
    _add_column("instruiri", "prescolari", "INTEGER DEFAULT 0")
    _add_column("instruiri", "elevi", "INTEGER DEFAULT 0")


def migrate_etichete_part09_v5() -> None:
    migrate_etichete_for_part("part_09")


def migrate_etichete_part09_v6() -> None:
    """Reîmprospătează etichetele Părții IX (F/M, grupuri Copii/Maturi)."""
    sync_etichete_defaults("part_09", reset_obsolete_custom=True)


def migrate_text_presets() -> None:
    from database.seed_defaults import seed_text_presets

    seed_text_presets()


# Tabele cu coloane an/luna — index pentru încărcare rapidă lună/an
_INDEXED_TABLES: list[tuple[str, bool]] = [
    ("evidenta_utilizatori", False),
    ("evidenta_utilizatori_copii_adulti", True),
    ("documente_inregistrate", True),
    ("documente_continut_czu", True),
    ("cercetari_bibliografice", False),
    ("activitati_informare", True),
    ("documente_electronice", False),
    ("instruiri", True),
    ("activitati_culturale", True),
    ("activitati_online", True),
]


def _create_index_if_missing(name: str, table: str, columns: str) -> None:
    insp = inspect(_engine())
    if table not in insp.get_table_names():
        return
    with _engine().connect() as conn:
        existing = conn.execute(text(f"PRAGMA index_list({table})")).fetchall()
        if any(row[1] == name for row in existing):
            return
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})"))
        conn.commit()


def migrate_indexes() -> None:
    for table, has_cat in _INDEXED_TABLES:
        _create_index_if_missing(f"ix_{table}_an_luna", table, "an, luna")
        if has_cat:
            _create_index_if_missing(
                f"ix_{table}_an_luna_cat", table, "an, luna, categorie_varsta"
            )


def migrate_part09_copii_adulti() -> None:
    """Partea IX — tab-uri Copii/Adulți cu coloane distincte (conform registrului fizic)."""
    _add_column("instruiri", "categorie_varsta", "TEXT DEFAULT 'copii'")
    for col in (
        "studenti",
        "intelectuali",
        "pensionari",
        "someri",
        "muncitori",
        "alte_categorii",
        "tineri_17_34",
        "adulti_35_64",
        "varstnici_65_plus",
    ):
        _add_column("instruiri", col, "INTEGER DEFAULT 0")

    if "instruiri" not in inspect(_engine()).get_table_names():
        return

    with _engine().connect() as conn:
        conn.execute(
            text(
                "UPDATE instruiri SET categorie_varsta = 'copii' "
                "WHERE categorie_varsta IS NULL OR categorie_varsta = '' "
                "OR prescolari > 0 OR elevi > 0 OR copii_pana_16 > 0"
            )
        )
        conn.execute(
            text(
                "UPDATE instruiri SET categorie_varsta = 'adulti' "
                "WHERE (categorie_varsta IS NULL OR categorie_varsta = '') "
                "AND (adulti > 0 OR participanti_masculin > 0 OR participanti_feminin > 0) "
                "AND prescolari = 0 AND elevi = 0"
            )
        )
        conn.execute(
            text(
                "UPDATE instruiri SET categorie_varsta = 'copii' "
                "WHERE categorie_varsta IS NULL OR categorie_varsta = ''"
            )
        )
        conn.execute(
            text(
                "UPDATE instruiri SET studenti = 0, intelectuali = 0, pensionari = 0, "
                "someri = 0, muncitori = 0, alte_categorii = 0, "
                "tineri_17_34 = 0, adulti_35_64 = 0, varstnici_65_plus = 0 "
                "WHERE categorie_varsta = 'copii'"
            )
        )
        conn.execute(
            text(
                "UPDATE instruiri SET prescolari = 0, elevi = 0 "
                "WHERE categorie_varsta = 'adulti'"
            )
        )
        conn.commit()


def migrate_etichete_part09_v7() -> None:
    migrate_etichete_for_part("part_09")
    sync_etichete_defaults("part_09", reset_obsolete_custom=True)


def migrate_part09_forma_bifaje() -> None:
    """Bifă formală / non-formală / informală + ore academice (registru fizic)."""
    for col in ("forma_formala", "forma_non_formala", "forma_informala"):
        _add_column("instruiri", col, "INTEGER DEFAULT 0")

    if "instruiri" not in inspect(_engine()).get_table_names():
        return

    with _engine().connect() as conn:
        conn.execute(
            text(
                "UPDATE instruiri SET forma_formala = 1 "
                "WHERE ore_formala > 0 AND forma_formala = 0"
            )
        )
        conn.execute(
            text(
                "UPDATE instruiri SET forma_non_formala = 1 "
                "WHERE ore_non_formala > 0 AND forma_non_formala = 0"
            )
        )
        conn.execute(
            text(
                "UPDATE instruiri SET forma_informala = 1 "
                "WHERE ore_informala > 0 AND forma_informala = 0"
            )
        )
        conn.commit()


def migrate_etichete_part09_v8() -> None:
    migrate_etichete_for_part("part_09")
    sync_etichete_defaults("part_09", reset_obsolete_custom=True)


SCHEMA_VERSION = 9


def migrate_schema_version() -> None:
    from database.db_manager import get_setting, set_setting

    current = get_setting("schema_version")
    if current is None:
        migrate_indexes()
        set_setting("schema_version", str(SCHEMA_VERSION))
        return
    try:
        ver = int(current)
    except ValueError:
        ver = 0
    if ver < SCHEMA_VERSION:
        if ver < 3:
            migrate_part09_part12_gender_columns()
            migrate_etichete_part09_part12()
            migrate_text_presets()
        if ver < 4:
            migrate_part06_part11_gender_columns()
            migrate_etichete_part06_part11()
        if ver < 5:
            migrate_part09_prescolari_elevi()
            migrate_etichete_part09_v5()
        if ver < 6:
            migrate_etichete_part09_v6()
        if ver < 8:
            migrate_part09_copii_adulti()
            migrate_etichete_part09_v7()
        if ver < 9:
            migrate_part09_forma_bifaje()
            migrate_etichete_part09_v8()
        migrate_indexes()
        set_setting("schema_version", str(SCHEMA_VERSION))


def run_migrations() -> None:
    migrate_part05_columns()
    migrate_etichete_part05()
    migrate_part06_columns()
    migrate_etichete_part06()
    migrate_part09_part12_gender_columns()
    migrate_etichete_part09_part12()
    migrate_part06_part11_gender_columns()
    migrate_etichete_part06_part11()
    migrate_part09_prescolari_elevi()
    migrate_etichete_part09_v5()
    migrate_etichete_part09_v6()
    migrate_part09_copii_adulti()
    migrate_etichete_part09_v7()
    migrate_part09_forma_bifaje()
    migrate_etichete_part09_v8()
    migrate_text_presets()
    migrate_schema_version()

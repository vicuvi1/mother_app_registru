"""Gestionare personal, etichete custom, range-uri și setări."""

from sqlalchemy import delete, select

from database.db_manager import get_session, set_setting, get_setting
from database.models import EtichetaCustom, Personal, RangeConfig, TextPreset

LUNI_RO = [
    "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
    "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie",
]


APP_AUTHOR = "Victor Bărbuță"
APP_CREDIT = f"Realizat de {APP_AUTHOR}"
DEFAULT_EXPORT_FORMAT = "word"


def get_personal_names(active_only: bool = True) -> list[str]:
    with get_session() as session:
        q = select(Personal.nume_prenume).order_by(Personal.nume_prenume)
        if active_only:
            q = q.where(Personal.activ.is_(True))
        return list(session.scalars(q))


def add_personal(nume: str) -> None:
    nume = nume.strip()
    if not nume:
        return
    with get_session() as session:
        existing = session.scalar(
            select(Personal).where(Personal.nume_prenume == nume)
        )
        if existing:
            existing.activ = True
        else:
            session.add(Personal(nume_prenume=nume, activ=True))
        session.commit()


def update_personal(old_name: str, new_name: str) -> None:
    new_name = new_name.strip()
    if not new_name:
        return
    with get_session() as session:
        person = session.scalar(
            select(Personal).where(Personal.nume_prenume == old_name)
        )
        if person:
            person.nume_prenume = new_name
            session.commit()


def delete_personal(nume: str) -> None:
    with get_session() as session:
        person = session.scalar(
            select(Personal).where(Personal.nume_prenume == nume)
        )
        if person:
            person.activ = False
            session.commit()


def get_eticheta(parte: str, camp: str) -> str:
    with get_session() as session:
        row = session.scalar(
            select(EtichetaCustom).where(
                EtichetaCustom.parte == parte,
                EtichetaCustom.camp == camp,
            )
        )
        if row is None:
            return camp
        return row.eticheta_custom or row.eticheta_default


def set_eticheta_custom(parte: str, camp: str, eticheta: str) -> None:
    with get_session() as session:
        row = session.scalar(
            select(EtichetaCustom).where(
                EtichetaCustom.parte == parte,
                EtichetaCustom.camp == camp,
            )
        )
        if row:
            row.eticheta_custom = eticheta.strip() or None
            session.commit()


def get_all_etichete(parte: str) -> dict[str, str]:
    with get_session() as session:
        rows = session.scalars(
            select(EtichetaCustom).where(EtichetaCustom.parte == parte)
        ).all()
        return {r.camp: (r.eticheta_custom or r.eticheta_default) for r in rows}


def get_range_config(parte: str) -> dict[str, tuple[int, int]]:
    with get_session() as session:
        rows = session.scalars(
            select(RangeConfig).where(RangeConfig.parte == parte)
        ).all()
        return {r.coloana: (r.valoare_min, r.valoare_max) for r in rows}


def get_range(parte: str, coloana: str, default: tuple[int, int] = (0, 30)) -> tuple[int, int]:
    with get_session() as session:
        row = session.scalar(
            select(RangeConfig).where(
                RangeConfig.parte == parte,
                RangeConfig.coloana == coloana,
            )
        )
        if row is None:
            return default
        return (row.valoare_min, row.valoare_max)


def set_range(parte: str, coloana: str, min_val: int, max_val: int) -> None:
    with get_session() as session:
        row = session.scalar(
            select(RangeConfig).where(
                RangeConfig.parte == parte,
                RangeConfig.coloana == coloana,
            )
        )
        if row:
            row.valoare_min = min_val
            row.valoare_max = max_val
        else:
            session.add(
                RangeConfig(
                    parte=parte,
                    coloana=coloana,
                    valoare_min=min_val,
                    valoare_max=max_val,
                )
            )
        session.commit()


def apply_global_ranges(persoane_max: int, activitati_max: int) -> None:
    """Aplică range-uri globale tuturor coloanelor numerice existente."""
    from database.seed_defaults import ACTIVITATI_ZI_PARTS, PERSOANE_ZI_COLS

    with get_session() as session:
        for parte, coloane in PERSOANE_ZI_COLS.items():
            max_val = activitati_max if parte in ACTIVITATI_ZI_PARTS else persoane_max
            for coloana in coloane:
                row = session.scalar(
                    select(RangeConfig).where(
                        RangeConfig.parte == parte,
                        RangeConfig.coloana == coloana,
                    )
                )
                if row:
                    row.valoare_min = 0
                    row.valoare_max = max_val
                else:
                    session.add(
                        RangeConfig(
                            parte=parte,
                            coloana=coloana,
                            valoare_min=0,
                            valoare_max=max_val,
                        )
                    )
        session.commit()


def get_biblioteca_info() -> tuple[str, str]:
    return (
        get_setting("nume_biblioteca", "") or "",
        get_setting("localitate", "") or "",
    )


def set_biblioteca_info(nume: str, localitate: str) -> None:
    set_setting("nume_biblioteca", nume.strip())
    set_setting("localitate", localitate.strip())


def ensure_personal_in_list(nume: str) -> None:
    """Adaugă nume nou în Personal dacă e introdus manual într-un dropdown."""
    if nume and nume.strip():
        add_personal(nume.strip())


COVER_DEFAULTS = {
    "institutie_1": "Ministerul Culturii al Republicii Moldova",
    "institutie_2": "Consiliul Biblioteconomic Național",
    "titlu": "Registru de evidență a activității",
    "biblioteca": "",
    "localitate": "",
    "an": "",
}

_COVER_KEYS = list(COVER_DEFAULTS.keys())


def get_cover_page() -> dict[str, str]:
    """Returnează câmpurile paginii de titlu (copertă), cu valori implicite rezonabile."""
    nume_bib, loc = get_biblioteca_info()
    result = {}
    for key in _COVER_KEYS:
        val = get_setting(f"cover_{key}", None)
        if val is None:
            if key == "biblioteca" and nume_bib:
                val = nume_bib
            elif key == "localitate" and loc:
                val = loc
            else:
                val = COVER_DEFAULTS[key]
        result[key] = val
    return result


def set_cover_page(data: dict[str, str]) -> None:
    for key in _COVER_KEYS:
        if key in data:
            set_setting(f"cover_{key}", (data[key] or "").strip())


def get_text_presets(parte: str, camp: str) -> list[str]:
    with get_session() as session:
        rows = session.scalars(
            select(TextPreset.valoare)
            .where(TextPreset.parte == parte, TextPreset.camp == camp)
            .order_by(TextPreset.valoare)
        ).all()
        presets = list(rows)
    if parte == "part_09" and camp == "formator":
        return sorted({*presets, *get_personal_names(active_only=True)})
    return presets


def set_text_presets(parte: str, camp: str, values: list[str]) -> None:
    cleaned = sorted({v.strip() for v in values if v and v.strip()})
    with get_session() as session:
        session.execute(
            delete(TextPreset).where(TextPreset.parte == parte, TextPreset.camp == camp)
        )
        for val in cleaned:
            session.add(TextPreset(parte=parte, camp=camp, valoare=val))
        session.commit()
    if parte == "part_09" and camp == "formator":
        for val in cleaned:
            ensure_personal_in_list(val)


def ensure_text_preset(parte: str, camp: str, valoare: str) -> None:
    valoare = valoare.strip()
    if not valoare:
        return
    with get_session() as session:
        existing = session.scalar(
            select(TextPreset).where(
                TextPreset.parte == parte,
                TextPreset.camp == camp,
                TextPreset.valoare == valoare,
            )
        )
        if not existing:
            session.add(TextPreset(parte=parte, camp=camp, valoare=valoare))
            session.commit()
    if parte == "part_09" and camp == "formator":
        ensure_personal_in_list(valoare)


def _excluded_days_key(year: int) -> str:
    return f"excluded_days_{year}"


def get_excluded_days_for_year(year: int) -> dict[int, list[str]]:
    """Returnează {luna: [DD.MM, ...]} pentru anul dat."""
    import json

    raw = get_setting(_excluded_days_key(year), "{}")
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        data = {}
    result: dict[int, list[str]] = {}
    for m in range(1, 13):
        vals = data.get(str(m), data.get(m, []))
        if isinstance(vals, list):
            result[m] = sorted({str(v).strip() for v in vals if str(v).strip()})
        else:
            result[m] = []
    return result


def get_excluded_days(year: int, month: int) -> list[str]:
    return get_excluded_days_for_year(year).get(month, [])


def set_excluded_days_for_year(year: int, by_month: dict[int, list[str]]) -> None:
    import json

    payload = {str(m): sorted({d.strip() for d in by_month.get(m, []) if d.strip()}) for m in range(1, 13)}
    set_setting(_excluded_days_key(year), json.dumps(payload, ensure_ascii=False))

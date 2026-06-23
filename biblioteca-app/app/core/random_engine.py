"""Generare automată cu range-uri și validare sume (reguli A/B/C)."""

import random
from typing import Any

from core.constants_manager import get_excluded_days, get_personal_names, get_range_config
from core.date_engine import get_working_days
from database.db_manager import get_session
from database.models import (
    ActivitatiCulturale,
    ActivitatiInformare,
    ActivitatiOnline,
    CercetariBibliografice,
    DocumenteContinutCZU,
    DocumenteElectronice,
    DocumenteInregistrate,
    EvidentaUtilizatori,
    EvidentaUtilizatoriCopiiAdulti,
    Instruiri,
    Parteneri,
    Voluntariat,
)

DEFAULT_TEME_INSTRUIRI = [
    "Clubul de dame - pe table și online",
    "Engleza este amuzantă cu jocuri și cântece",
    "Informare utilizatori noi",
    "Workshop digital literacy",
]

DEFAULT_TIPURI_ACTIVITATE = [
    "Expoziție",
    "Activitate literar-culturală",
    "Oră educativă",
    "Oră de lectură",
    "Oră de desen",
    "Excursie",
]


def generate_random_in_range(min_val: int, max_val: int) -> int:
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    return random.randint(min_val, max_val)


def generate_split_sum(
    total: int,
    n_categories: int,
    mins: list[int],
    maxs: list[int],
) -> list[int]:
    """
    Distribuie total în n_categories valori respectând [min_i, max_i].
    Relaxează proporțional dacă constrângerile sunt imposibile.
    """
    if n_categories == 0:
        return []
    if len(mins) != n_categories or len(maxs) != n_categories:
        raise ValueError("mins/maxs length must match n_categories")

    mins = list(mins)
    maxs = list(maxs)
    min_sum = sum(mins)
    max_sum = sum(maxs)

    if total < min_sum:
        total = min_sum
    if total > max_sum:
        total = max_sum

    remaining = total - min_sum
    values = list(mins)
    caps = [maxs[i] - mins[i] for i in range(n_categories)]

    for _ in range(n_categories * 50):
        if remaining <= 0:
            break
        idx = random.randrange(n_categories)
        if caps[idx] <= 0:
            continue
        add = random.randint(1, min(remaining, caps[idx]))
        values[idx] += add
        caps[idx] -= add
        remaining -= add

    if remaining > 0:
        for i in range(n_categories):
            add = min(remaining, caps[i])
            values[i] += add
            remaining -= add
            if remaining <= 0:
                break

    return values


def _rng(parte: str, coloana: str, ranges: dict[str, tuple[int, int]]) -> int:
    lo, hi = ranges.get(coloana, (0, 30))
    return generate_random_in_range(lo, hi)


def _gen_type_a_row(
    ranges: dict[str, tuple[int, int]],
    sources: list[str],
    total_col: str | None = None,
) -> dict[str, int]:
    row = {c: _rng("", c, ranges) for c in sources}
    if total_col:
        row[total_col] = sum(row[c] for c in sources)
    return row


def _gen_part01_row(ranges: dict[str, tuple[int, int]]) -> dict[str, int]:
    statut_cols = [
        "adulti", "copii_pana_16", "prescolari", "elevi", "studenti",
        "intelectuali", "muncitori", "pensionari", "someri", "alte_categorii",
    ]
    varsta_cols = ["tineri_17_34", "adulti_35_64", "varstnici_65_plus"]
    sex_cols = ["sex_copii_f", "sex_copii_m", "sex_adulti_f", "sex_adulti_m"]

    lo, hi = ranges.get("adulti", (2, 20))
    total = generate_random_in_range(max(lo, 5), hi + 10)

    statut = generate_split_sum(
        total, len(statut_cols),
        [ranges.get(c, (0, 30))[0] for c in statut_cols],
        [ranges.get(c, (0, 30))[1] for c in statut_cols],
    )
    varsta = generate_split_sum(
        total, len(varsta_cols),
        [ranges.get(c, (0, 30))[0] for c in varsta_cols],
        [ranges.get(c, (0, 30))[1] for c in varsta_cols],
    )
    sex = generate_split_sum(
        total, len(sex_cols),
        [ranges.get(c, (0, 30))[0] for c in sex_cols],
        [ranges.get(c, (0, 30))[1] for c in sex_cols],
    )

    row: dict[str, int] = {}
    for c, v in zip(statut_cols, statut):
        row[c] = v
    for c, v in zip(varsta_cols, varsta):
        row[c] = v
    for c, v in zip(sex_cols, sex):
        row[c] = v
    return row


def _gen_part02_row(ranges: dict[str, tuple[int, int]]) -> dict[str, Any]:
    sub = [
        "imprumut_carti", "sedinte_calculatoare", "activitati_culturale_stiintifice",
        "instruiri", "alte_scopuri_excursii",
    ]
    sub_vals = _gen_type_a_row(ranges, sub)
    row = dict(sub_vals)
    row["intrari_total_zi"] = sum(sub_vals[c] for c in sub)

    vv = _gen_type_a_row(
        ranges,
        ["vizite_virtuale_pagina_web", "vizite_virtuale_blog"],
        "vizite_virtuale_total",
    )
    row.update(vv)
    vvr = _gen_type_a_row(
        ranges,
        ["vizitatori_virtuali_pagina_web", "vizitatori_virtuali_blog"],
        "vizitatori_virtuali_total",
    )
    row.update(vvr)

    for prefix in ("facebook", "instagram", "twitter"):
        for suffix in ("vizualizari", "impact", "interactiuni"):
            col = f"{prefix}_{suffix}"
            row[col] = _rng("part_02", col, ranges)
    return row


def _gen_part03_row(ranges: dict[str, tuple[int, int]]) -> dict[str, Any]:
    din_care = [
        "consultare_pe_loc", "imprumut_pe_loc",
        "imprumut_la_domiciliu", "imprumut_inter_bibliotecar",
    ]
    row = _gen_type_a_row(ranges, din_care, "total_imprumuturi")
    cats = [
        "carti", "publicatii_seriale", "documente_muzica", "documente_audiovizuale",
        "documente_electronice_cd_dvd", "alte_documente",
    ]
    for c in cats:
        row[c] = _rng("part_03", c, ranges)
    row["limba_romana"] = _rng("part_03", "limba_romana", ranges)
    row["alte_limbi"] = _rng("part_03", "alte_limbi", ranges)
    return row


def _gen_part04_row(ranges: dict[str, tuple[int, int]]) -> dict[str, Any]:
    czu = [
        "czu_0_generalitati", "czu_1_filozofie", "czu_2_religie", "czu_3_stiinte_sociale",
        "czu_5_matematica", "czu_6_stiinte_aplicate", "czu_7_arte", "czu_8_limbi",
        "czu_9_geografie",
    ]
    return _gen_type_a_row(ranges, czu, "total_imprumuturi")


def _gen_part07_row(ranges: dict[str, tuple[int, int]]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    row["total_documente_electronice"] = _rng("part_07", "total_documente_electronice", ranges)
    row["mediu_email"] = _rng("part_07", "mediu_email", ranges)
    row["mediu_skype_retele_sociale"] = _rng("part_07", "mediu_skype_retele_sociale", ranges)
    for c in (
        "carti", "publicatii_seriale", "documente_muzica", "documente_audiovizuale",
        "documente_electronice_cd_dvd", "alte_documente", "limba_romana", "alte_limbi",
    ):
        row[c] = _rng("part_07", c, ranges)
    return row


def _gen_part09_row(ranges: dict[str, tuple[int, int]], data: str, personal: list[str]) -> dict[str, Any]:
    total = _rng("part_09", "total_participanti", ranges)
    feminin = min(_rng("part_09", "participanti_feminin", ranges), total)
    masculin = max(0, total - feminin)
    return {
        "data": data,
        "format_online": random.choice([True, False]),
        "format_offline": random.choice([True, False]),
        "ore_formala": _rng("part_09", "ore_formala", ranges),
        "ore_non_formala": _rng("part_09", "ore_non_formala", ranges),
        "ore_informala": _rng("part_09", "ore_informala", ranges),
        "tema_instruirii": random.choice(DEFAULT_TEME_INSTRUIRI),
        "formator": random.choice(personal) if personal else "",
        "total_participanti": total,
        "participanti_masculin": masculin,
        "participanti_feminin": feminin,
    }


GENERATORS = {
    "part_01": _gen_part01_row,
    "part_02": _gen_part02_row,
    "part_03": _gen_part03_row,
    "part_04": _gen_part04_row,
    "part_07": _gen_part07_row,
}


def generate_month_data(
    parte: str,
    an: int,
    luna: int,
    range_config: dict[str, tuple[int, int]] | None = None,
    categorie_varsta: str | None = None,
) -> list[dict[str, Any]]:
    """Generează date pentru o lună întreagă (zile lucrătoare sau evenimente)."""
    ranges = range_config or get_range_config(parte)
    personal = get_personal_names()
    days = get_working_days(an, luna, get_excluded_days(an, luna))
    rows: list[dict[str, Any]] = []

    if parte == "part_01":
        for d in days:
            row = _gen_part01_row(ranges)
            row["data"] = d
            rows.append(row)
    elif parte in ("part_02", "part_03", "part_04"):
        gen = GENERATORS[parte]
        for d in days:
            row = gen(ranges)
            row["data"] = d
            rows.append(row)
    elif parte == "part_05":
        n = max(1, len(days) // 3)
        solicitanti = [
            "Comerzan Sebastian", "Burlacu Damian", "Dumitrașcu Svetlana",
            "Bărbuță Oliviu", "Prișibilovici Artiom", "Darii Elena",
        ]
        referinte = [
            "Legenda mărțișor", "Povești crengiene", "Poezii Filip",
            "Fabule", "Anexarea Basarabiei", "Tradiții și obiceiuri",
        ]
        for d in random.sample(days, min(n, len(days))):
            rows.append({
                "data_primirii_cererii": d,
                "total_referinte": _rng(parte, "total_referinte", ranges),
                "date_despre_solicitant": random.choice(solicitanti),
                "statut_socio_profesional": random.choice(
                    ["elev", "student", "pensionar", "casnică", "coordonatoare", "cl.2"]
                ),
                "referinta": random.choice(referinte),
                "cercetare_bibliografica": random.choice(["", "X", "✓"]),
                "consultatie": random.choice(["", "X", "✓"]),
                "referinta_tematica": random.choice(["", "X", "tematică"]),
                "referinta_de_concretizare": "",
                "referinta_de_adresa": "",
                "referinta_factologie": random.choice(["", "factologie"]),
                "limite_cronologice": "",
                "surse_consultatie": _rng(parte, "surse_consultatie", ranges),
                "numar_descrieri_bibliografice": _rng(
                    parte, "numar_descrieri_bibliografice", ranges
                ),
                "surse_recomandate": _rng(parte, "surse_recomandate", ranges),
                "data_finalizarii_cererii": d,
                "responsabil": random.choice(personal) if personal else "",
            })
    elif parte == "part_06":
        n = max(1, len(days) // 4)
        subiecte = [
            "Ziua informării",
            "Fapte bune ca sămânța ce crește în grădină",
            "Ziua păsărilor",
        ]
        for i, d in enumerate(random.sample(days, min(n, len(days)))):
            kind = i % 3
            rows.append({
                "data": f"_r{i + 1}",
                "grup_tinta_subiect": random.choice(subiecte),
                "activitate_individuala": "DSI" if kind == 0 else "",
                "activitate_grup": "Ziua specialistului" if kind == 1 else "",
                "activitate_public_larg": "Ziua de informare" if kind == 2 else "",
                "numar_participanti": _rng(parte, "numar_participanti", ranges),
                "documente_consultate": _rng(parte, "documente_consultate", ranges),
                "responsabil": random.choice(personal) if personal else "",
            })
    elif parte == "part_07":
        row = _gen_part07_row(ranges)
        row["luna"] = luna
        rows.append(row)
    elif parte == "part_09":
        for d in days:
            n_instr = random.randint(0, 2)
            for _ in range(n_instr):
                rows.append(_gen_part09_row(ranges, d, personal))
    elif parte == "part_11":
        n = max(1, len(days) // 5)
        for _ in range(n):
            rows.append({
                "data": random.choice(days),
                "total_activitati": 1,
                "din_care_expozitii": random.choice([0, 1]),
                "tipul_activitatii": random.choice(DEFAULT_TIPURI_ACTIVITATE),
                "denumirea_activitatii": "Activitate culturală",
                "total_participanti": _rng(parte, "total_participanti", ranges),
            })
    elif parte == "part_12":
        n = max(1, len(days) // 4)
        for d in random.sample(days, min(n, len(days))):
            total = _rng(parte, "participanti_total", ranges)
            feminin = min(_rng(parte, "participanti_feminin", ranges), total)
            rows.append({
                "data": d,
                "denumirea_activitatii": "Activitate online",
                "tipul_activitatii": random.choice(DEFAULT_TIPURI_ACTIVITATE),
                "platforma": random.choice(["Facebook", "Zoom", "Instagram"]),
                "vizualizari": _rng(parte, "vizualizari", ranges),
                "impact": _rng(parte, "impact", ranges),
                "participanti_total": total,
                "participanti_masculin": max(0, total - feminin),
                "participanti_feminin": feminin,
            })

    if categorie_varsta:
        for r in rows:
            r["categorie_varsta"] = categorie_varsta
    return rows


def generate_year_monthly_data(
    parte: str,
    an: int,
    range_config: dict[str, tuple[int, int]] | None = None,
    categorie_varsta: str | None = None,
) -> list[dict[str, Any]]:
    """Partea VII: 12 rânduri (lunile anului)."""
    ranges = range_config or get_range_config(parte)
    rows = []
    for luna in range(1, 13):
        row = _gen_part07_row(ranges)
        row["luna"] = luna
        if categorie_varsta:
            row["categorie_varsta"] = categorie_varsta
        rows.append(row)
    return rows

"""Placeholder-uri default: personal, etichete coloane, range-uri inițiale."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import EtichetaCustom, Personal, RangeConfig, TextPreset

DEFAULT_PERSONAL = [
    "Bărbuță O.",
    "Poleșciuc T.",
    "Darii Elena",
    "Poleșciuc Valeriu",
]

# Identificatori interni Părți (conform fișierelor din SPEC secțiunea 2)
PARTE_IDS = [
    "part_01",
    "part_02",
    "part_03",
    "part_04",
    "part_05",
    "part_06",
    "part_07",
    "part_09",
    "part_11",
    "part_12",
    "part_13",
    "part_14",
]

# Etichete default per Parte — câmp = identificator intern coloană
DEFAULT_ETICHETE: dict[str, list[tuple[str, str]]] = {
    "part_01": [
        ("data", "Data"),
        ("adulti", "Adulți"),
        ("copii_pana_16", "Copii până la 16 ani"),
        ("prescolari", "Preșcolari"),
        ("elevi", "Elevi"),
        ("studenti", "Studenți"),
        ("intelectuali", "Intelectuali"),
        ("muncitori", "Muncitori"),
        ("pensionari", "Pensionari"),
        ("someri", "Șomeri"),
        ("alte_categorii", "Alte categorii"),
        ("tineri_17_34", "Tineri (17-34 ani)"),
        ("adulti_35_64", "Adulți (35-64 ani)"),
        ("varstnici_65_plus", "Vârstnici după 65 ani"),
        ("sex_copii_f", "F (copii)"),
        ("sex_copii_m", "M (copii)"),
        ("sex_adulti_f", "F (adulți)"),
        ("sex_adulti_m", "M (adulți)"),
    ],
    "part_02": [
        ("data", "Data"),
        ("intrari_total_zi", "Intrări total zi"),
        ("imprumut_carti", "Împrumut cărți"),
        ("sedinte_calculatoare", "Ședințe Calculatoare"),
        ("activitati_culturale_stiintifice", "Activități Culturale/Științifice și altele"),
        ("instruiri", "Instruiri"),
        ("alte_scopuri_excursii", "Alte scopuri/excursii"),
        ("vizite_virtuale_total", "Total vizite virtuale"),
        ("vizite_virtuale_pagina_web", "Pagină web"),
        ("vizite_virtuale_blog", "Blog"),
        ("vizitatori_virtuali_total", "Total vizitatori virtuali"),
        ("vizitatori_virtuali_pagina_web", "Pagină web"),
        ("vizitatori_virtuali_blog", "Blog"),
        ("facebook_vizualizari", "Facebook — Vizualizări"),
        ("facebook_impact", "Facebook — Impact"),
        ("facebook_interactiuni", "Facebook — Interacționări"),
        ("instagram_vizualizari", "Instagram — Vizualizări"),
        ("instagram_impact", "Instagram — Impact"),
        ("instagram_interactiuni", "Instagram — Interacționări"),
        ("twitter_vizualizari", "Twitter — Vizualizări"),
        ("twitter_impact", "Twitter — Impact"),
        ("twitter_interactiuni", "Twitter — Interacționări"),
    ],
    "part_03": [
        ("data", "Data"),
        ("total_imprumuturi", "Total împrumuturi"),
        ("consultare_pe_loc", "Consultare pe loc"),
        ("imprumut_pe_loc", "Împrumut pe loc"),
        ("imprumut_la_domiciliu", "Împrumut la domiciliu"),
        ("imprumut_inter_bibliotecar", "Împrumut inter-bibliotecar"),
        ("carti", "Cărți"),
        ("publicatii_seriale", "Publicații seriale"),
        ("documente_muzica", "Documente de muzică tipărită"),
        ("documente_audiovizuale", "Documente audiovizuale"),
        ("documente_electronice_cd_dvd", "Documente electronice (CDROM/DVD)"),
        ("alte_documente", "Alte documente"),
        ("limba_romana", "În limba română"),
        ("alte_limbi", "Alte limbi"),
    ],
    "part_04": [
        ("data", "Data"),
        ("total_imprumuturi", "Total împrumuturi"),
        ("czu_0_generalitati", "0-Generalități"),
        ("czu_1_filozofie", "1-Filozofie/Psihologie"),
        ("czu_2_religie", "2-Religie/Teologie"),
        ("czu_3_stiinte_sociale", "3-Științe sociale"),
        ("czu_5_matematica", "5-Matematică/Științe sociale"),
        ("czu_6_stiinte_aplicate", "6-Științe aplicate/Medicină/Tehnologie"),
        ("czu_7_arte", "7-Arte/Recreație/Sport"),
        ("czu_8_limbi", "8-Limbi/Lingvistică/Literatură"),
        ("czu_9_geografie", "9-Geografie/Biografie/Istorie"),
    ],
    "part_05": [
        ("data_primirii_cererii", "Data primirii cererii"),
        ("total_referinte", "Total referințe"),
        ("date_despre_solicitant", "Date despre solicitant"),
        ("statut_socio_profesional", "Statutul socio-profesional"),
        ("referinta", "Referință"),
        ("cercetare_bibliografica", "Cercetare bibliografică"),
        ("consultatie", "Consultație"),
        ("referinta_tematica", "tematică"),
        ("referinta_de_concretizare", "de concretizare"),
        ("referinta_de_adresa", "de adresă"),
        ("referinta_factologie", "factologie"),
        ("limite_cronologice", "Limite cronologice"),
        ("surse_consultatie", "Surse consultație"),
        ("numar_descrieri_bibliografice", "Număr de descrieri bibliografice"),
        ("surse_recomandate", "Surse recomandate"),
        ("data_finalizarii_cererii", "Data finalizării cererii"),
        ("responsabil", "Responsabil"),
    ],
    "part_06": [
        ("grup_tinta_subiect", "Grup țintă/Subiect"),
        ("activitate_individuala", "Individuală (DSI, etc.)"),
        ("activitate_grup", "Pentru un grup (Ziua specialistului, Ziua Catedrei, etc.)"),
        ("activitate_public_larg", "Pentru publicul larg (Ziua de Informare, Expoziții de informare)"),
        ("numar_participanti", "Total participanți"),
        ("participanti_masculin", "Masculin"),
        ("participanti_feminin", "Feminin"),
        ("documente_consultate", "Documente consultate"),
        ("responsabil", "Responsabil"),
    ],
    "part_07": [
        ("total_documente_electronice", "Total documente electronice furnizate"),
        ("mediu_email", "E-mail"),
        ("mediu_skype_retele_sociale", "Skype/rețele sociale"),
        ("carti", "Cărți"),
        ("publicatii_seriale", "Publicații seriale"),
        ("documente_muzica", "Documente de muzică tipărită"),
        ("documente_audiovizuale", "Documente audiovizuale"),
        ("documente_electronice_cd_dvd", "Documente Electronice (CD/DVD)"),
        ("alte_documente", "Alte documente"),
        ("limba_romana", "În limba română"),
        ("alte_limbi", "Alte limbi"),
    ],
    "part_09": [
        ("data", "Data"),
        ("format_online", "online"),
        ("format_offline", "offline"),
        ("forma_formala", "formală"),
        ("ore_formala", "Nr. de ore academice"),
        ("forma_non_formala", "Non-formală"),
        ("ore_non_formala", "Nr. de ore academice"),
        ("forma_informala", "informală"),
        ("tema_instruirii", "Tema instruirii"),
        ("formator", "Formator (numele, prenumele)"),
        ("total_participanti", "Total participanți"),
        ("prescolari", "Preșcolari"),
        ("elevi", "Elevi"),
        ("studenti", "studenți"),
        ("intelectuali", "intelectuali"),
        ("pensionari", "pensionari"),
        ("someri", "șomeri"),
        ("muncitori", "muncitori"),
        ("alte_categorii", "alte categorii"),
        ("tineri_17_34", "Tinerii (17-34)"),
        ("adulti_35_64", "Adulți (35-64)"),
        ("varstnici_65_plus", "Vârstnici după 65"),
        ("participanti_feminin", "Feminin"),
        ("participanti_masculin", "Masculin"),
    ],
    "part_11": [
        ("data", "Data"),
        ("total_activitati", "Activități cultural științifice"),
        ("din_care_expozitii", "Din care expoziții"),
        ("tipul_activitatii", "Tipul activității"),
        ("denumirea_activitatii", "Denumirea activității"),
        ("total_participanti", "Total participanți"),
        ("participanti_masculin", "Masculin"),
        ("participanti_feminin", "Feminin"),
    ],
    "part_12": [
        ("data", "Data"),
        ("denumirea_activitatii", "Denumirea activității"),
        ("tipul_activitatii", "Tipul activității"),
        ("platforma", "Platforma"),
        ("vizualizari", "Vizualizări"),
        ("impact", "Impact"),
        ("participanti_total", "Total participanți"),
        ("participanti_masculin", "Masculin"),
        ("participanti_feminin", "Feminin"),
    ],
    "part_13": [
        ("partener", "Partener"),
        ("scope_local", "Local"),
        ("scope_national", "Național"),
        ("scope_international", "Internațional"),
        ("date_contact", "Date de contact"),
        ("tip_contract", "Tip de contract"),
        ("data_semnarii", "Data semnării"),
        ("termen_realizare", "Termenul de realizare"),
        ("modalitati_realizare", "Modalități de realizare a parteneriatului"),
        ("participanti_total", "Total participanți"),
        ("participanti_adulti", "Adulți"),
        ("participanti_copii", "Copii până la 16 ani"),
        ("impact", "Impact"),
    ],
    "part_14": [
        ("nume_prenume", "Numele, prenumele"),
        ("nr_contract", "Nr. contractului"),
        ("data_inceperii", "Data începerii"),
        ("data_incheierii", "Data încheierii"),
        ("numar_ore", "Numărul de ore de voluntariat"),
        ("activitati_realizate", "Activități realizate"),
        ("coordonator", "Semnătura coordonatorului de voluntari"),
    ],
}

# Coloane numerice cu range default: persoane/zi = 0-30, activități/zi = 0-5
PERSOANE_ZI_COLS = {
    "part_01": [
        "adulti", "copii_pana_16", "prescolari", "elevi", "studenti",
        "intelectuali", "muncitori", "pensionari", "someri", "alte_categorii",
        "tineri_17_34", "adulti_35_64", "varstnici_65_plus",
        "sex_copii_f", "sex_copii_m", "sex_adulti_f", "sex_adulti_m",
    ],
    "part_02": [
        "intrari_total_zi", "imprumut_carti", "sedinte_calculatoare",
        "activitati_culturale_stiintifice", "instruiri", "alte_scopuri_excursii",
        "vizite_virtuale_total", "vizite_virtuale_pagina_web", "vizite_virtuale_blog",
        "vizitatori_virtuali_total", "vizitatori_virtuali_pagina_web", "vizitatori_virtuali_blog",
        "facebook_vizualizari", "facebook_impact", "facebook_interactiuni",
        "instagram_vizualizari", "instagram_impact", "instagram_interactiuni",
        "twitter_vizualizari", "twitter_impact", "twitter_interactiuni",
    ],
    "part_03": [
        "total_imprumuturi", "consultare_pe_loc", "imprumut_pe_loc",
        "imprumut_la_domiciliu", "imprumut_inter_bibliotecar",
        "carti", "publicatii_seriale", "documente_muzica", "documente_audiovizuale",
        "documente_electronice_cd_dvd", "alte_documente", "limba_romana", "alte_limbi",
    ],
    "part_04": [
        "total_imprumuturi", "czu_0_generalitati", "czu_1_filozofie", "czu_2_religie",
        "czu_3_stiinte_sociale", "czu_5_matematica", "czu_6_stiinte_aplicate",
        "czu_7_arte", "czu_8_limbi", "czu_9_geografie",
    ],
    "part_05": [
        "total_referinte", "surse_consultatie", "numar_descrieri_bibliografice", "surse_recomandate",
    ],
    "part_06": [
        "numar_participanti", "participanti_masculin", "participanti_feminin", "documente_consultate",
    ],
    "part_07": [
        "total_documente_electronice", "mediu_email", "mediu_skype_retele_sociale",
        "carti", "publicatii_seriale", "documente_muzica", "documente_audiovizuale",
        "documente_electronice_cd_dvd", "alte_documente", "limba_romana", "alte_limbi",
    ],
    "part_09": [
        "ore_formala", "ore_non_formala", "ore_informala",
        "total_participanti", "prescolari", "elevi",
        "studenti", "intelectuali", "pensionari", "someri", "muncitori", "alte_categorii",
        "tineri_17_34", "adulti_35_64", "varstnici_65_plus",
        "participanti_feminin", "participanti_masculin",
    ],
    "part_11": [
        "total_activitati", "din_care_expozitii", "total_participanti",
        "participanti_masculin", "participanti_feminin",
    ],
    "part_12": [
        "vizualizari", "impact", "participanti_total", "participanti_masculin", "participanti_feminin",
    ],
    "part_13": ["participanti_total", "participanti_adulti", "participanti_copii", "impact"],
    "part_14": ["numar_ore"],
}

ACTIVITATI_ZI_PARTS = {"part_05", "part_06", "part_09", "part_11", "part_12"}

DEFAULT_TEXT_PRESETS: dict[tuple[str, str], list[str]] = {
    ("part_05", "statut_socio_profesional"): [
        "Elev",
        "Student",
        "Profesor",
        "Pensionar",
        "Muncitor",
        "Intelectual",
        "Casnică",
        "Șomer",
        "Coordonator",
    ],
    ("part_09", "tema_instruirii"): [
        "Clubul de dame - pe table și online",
        "Engleza este amuzantă cu jocuri și cântece",
        "Informare utilizatori noi",
        "Workshop digital literacy",
        "Utilizarea catalogului online",
        "Reguli de comportament în bibliotecă",
        "Cum găsim informația rapid",
    ],
    ("part_09", "formator"): [],
    ("part_11", "tipul_activitatii"): [
        "Expoziție",
        "Activitate literar-culturală",
        "Oră educativă",
        "Activitate/Expoziție",
        "Oră de lectură",
        "Oră de desen",
        "Oră de poezie",
        "Competiție joc de dame",
        "Excursie",
    ],
    ("part_11", "denumirea_activitatii"): [
        "Activitate culturală",
        "Mihai Eminescu - Lumina Poeziei Românești",
        "Expoziție de artă plastică",
        "Oră de lectură pentru copii",
        "Clubul seniorilor activi",
    ],
    ("part_12", "tipul_activitatii"): [
        "Expoziție",
        "Activitate literar-culturală",
        "Oră educativă",
        "Oră de lectură",
        "Oră de desen",
        "Excursie",
    ],
    ("part_12", "platforma"): [
        "Facebook",
        "Instagram",
        "Zoom",
        "YouTube",
        "TikTok",
    ],
}


def seed_text_presets() -> None:
    """Liste preset text — adaugă valori lipsă fără a șterge personalizările."""
    from database.db_manager import get_session

    with get_session() as session:
        for (parte, camp), values in DEFAULT_TEXT_PRESETS.items():
            for valoare in values:
                exists = session.scalar(
                    select(TextPreset.id).where(
                        TextPreset.parte == parte,
                        TextPreset.camp == camp,
                        TextPreset.valoare == valoare,
                    ).limit(1)
                )
                if exists is None:
                    session.add(TextPreset(parte=parte, camp=camp, valoare=valoare))
        session.commit()


def seed_personal(session: Session) -> None:
    existing = session.scalar(select(Personal.id).limit(1))
    if existing is not None:
        return
    for nume in DEFAULT_PERSONAL:
        session.add(Personal(nume_prenume=nume, activ=True))


def seed_etichete(session: Session) -> None:
    for parte, etichete in DEFAULT_ETICHETE.items():
        for camp, default_label in etichete:
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


def seed_range_configs(session: Session) -> None:
    for parte, coloane in PERSOANE_ZI_COLS.items():
        is_activitate = parte in ACTIVITATI_ZI_PARTS
        for coloana in coloane:
            exists = session.scalar(
                select(RangeConfig.id).where(
                    RangeConfig.parte == parte,
                    RangeConfig.coloana == coloana,
                ).limit(1)
            )
            if exists is None:
                session.add(
                    RangeConfig(
                        parte=parte,
                        coloana=coloana,
                        valoare_min=0,
                        valoare_max=5 if is_activitate else 30,
                    )
                )


def seed_all_defaults(session: Session) -> None:
    seed_personal(session)
    seed_etichete(session)
    seed_range_configs(session)
    seed_text_presets()

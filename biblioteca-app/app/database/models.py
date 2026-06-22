"""Scheme SQLite (SQLAlchemy) pentru toate Părțile I–VII, IX, XI–XIV."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Tabele suport globale
# ---------------------------------------------------------------------------


class Personal(Base):
    __tablename__ = "personal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nume_prenume: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    activ: Mapped[bool] = mapped_column(Boolean, default=True)


class RangeConfig(Base):
    __tablename__ = "range_config"
    __table_args__ = (UniqueConstraint("parte", "coloana", name="uq_range_parte_coloana"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parte: Mapped[str] = mapped_column(String, nullable=False)
    coloana: Mapped[str] = mapped_column(String, nullable=False)
    valoare_min: Mapped[int] = mapped_column(Integer, default=0)
    valoare_max: Mapped[int] = mapped_column(Integer, default=20)


class EtichetaCustom(Base):
    __tablename__ = "etichete_custom"
    __table_args__ = (UniqueConstraint("parte", "camp", name="uq_eticheta_parte_camp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parte: Mapped[str] = mapped_column(String, nullable=False)
    camp: Mapped[str] = mapped_column(String, nullable=False)
    eticheta_default: Mapped[str] = mapped_column(String, nullable=False)
    eticheta_custom: Mapped[str | None] = mapped_column(String, nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    cheie: Mapped[str] = mapped_column(String, primary_key=True)
    valoare: Mapped[str | None] = mapped_column(String, nullable=True)


class TextPreset(Base):
    """Valori predefinite pentru câmpuri text (Părțile V+) — select rapid din celulă."""

    __tablename__ = "text_presets"
    __table_args__ = (
        UniqueConstraint("parte", "camp", "valoare", name="uq_text_preset_parte_camp_val"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parte: Mapped[str] = mapped_column(String, nullable=False)
    camp: Mapped[str] = mapped_column(String, nullable=False)
    valoare: Mapped[str] = mapped_column(String, nullable=False)


# ---------------------------------------------------------------------------
# PARTEA I — Evidența utilizatorilor (Copii + Adulți împreună)
# ---------------------------------------------------------------------------


class EvidentaUtilizatori(Base):
    __tablename__ = "evidenta_utilizatori"
    __table_args__ = (UniqueConstraint("an", "luna", "data", name="uq_part01_an_luna_data"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[str] = mapped_column(String, nullable=False)

    adulti: Mapped[int] = mapped_column(Integer, default=0)
    copii_pana_16: Mapped[int] = mapped_column(Integer, default=0)
    prescolari: Mapped[int] = mapped_column(Integer, default=0)
    elevi: Mapped[int] = mapped_column(Integer, default=0)
    studenti: Mapped[int] = mapped_column(Integer, default=0)
    intelectuali: Mapped[int] = mapped_column(Integer, default=0)
    muncitori: Mapped[int] = mapped_column(Integer, default=0)
    pensionari: Mapped[int] = mapped_column(Integer, default=0)
    someri: Mapped[int] = mapped_column(Integer, default=0)
    alte_categorii: Mapped[int] = mapped_column(Integer, default=0)

    tineri_17_34: Mapped[int] = mapped_column(Integer, default=0)
    adulti_35_64: Mapped[int] = mapped_column(Integer, default=0)
    varstnici_65_plus: Mapped[int] = mapped_column(Integer, default=0)

    sex_copii_f: Mapped[int] = mapped_column(Integer, default=0)
    sex_copii_m: Mapped[int] = mapped_column(Integer, default=0)
    sex_adulti_f: Mapped[int] = mapped_column(Integer, default=0)
    sex_adulti_m: Mapped[int] = mapped_column(Integer, default=0)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA II — Evidența utilizatorilor (Copii / Adulți separat)
# ---------------------------------------------------------------------------


class EvidentaUtilizatoriCopiiAdulti(Base):
    __tablename__ = "evidenta_utilizatori_copii_adulti"
    __table_args__ = (
        UniqueConstraint(
            "an", "luna", "data", "categorie_varsta", name="uq_part02_an_luna_data_cat"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[str] = mapped_column(String, nullable=False)
    categorie_varsta: Mapped[str] = mapped_column(String, nullable=False)  # 'copii' | 'adulti'

    intrari_total_zi: Mapped[int] = mapped_column(Integer, default=0)
    imprumut_carti: Mapped[int] = mapped_column(Integer, default=0)
    sedinte_calculatoare: Mapped[int] = mapped_column(Integer, default=0)
    activitati_culturale_stiintifice: Mapped[int] = mapped_column(Integer, default=0)
    instruiri: Mapped[int] = mapped_column(Integer, default=0)
    alte_scopuri_excursii: Mapped[int] = mapped_column(Integer, default=0)

    vizite_virtuale_total: Mapped[int] = mapped_column(Integer, default=0)
    vizite_virtuale_pagina_web: Mapped[int] = mapped_column(Integer, default=0)
    vizite_virtuale_blog: Mapped[int] = mapped_column(Integer, default=0)

    vizitatori_virtuali_total: Mapped[int] = mapped_column(Integer, default=0)
    vizitatori_virtuali_pagina_web: Mapped[int] = mapped_column(Integer, default=0)
    vizitatori_virtuali_blog: Mapped[int] = mapped_column(Integer, default=0)

    facebook_vizualizari: Mapped[int] = mapped_column(Integer, default=0)
    facebook_impact: Mapped[int] = mapped_column(Integer, default=0)
    facebook_interactiuni: Mapped[int] = mapped_column(Integer, default=0)
    instagram_vizualizari: Mapped[int] = mapped_column(Integer, default=0)
    instagram_impact: Mapped[int] = mapped_column(Integer, default=0)
    instagram_interactiuni: Mapped[int] = mapped_column(Integer, default=0)
    twitter_vizualizari: Mapped[int] = mapped_column(Integer, default=0)
    twitter_impact: Mapped[int] = mapped_column(Integer, default=0)
    twitter_interactiuni: Mapped[int] = mapped_column(Integer, default=0)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA III — Documente înregistrate (Copii / Adulți)
# ---------------------------------------------------------------------------


class DocumenteInregistrate(Base):
    __tablename__ = "documente_inregistrate"
    __table_args__ = (
        UniqueConstraint(
            "an", "luna", "data", "categorie_varsta", name="uq_part03_an_luna_data_cat"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[str] = mapped_column(String, nullable=False)
    categorie_varsta: Mapped[str] = mapped_column(String, nullable=False)

    total_imprumuturi: Mapped[int] = mapped_column(Integer, default=0)
    consultare_pe_loc: Mapped[int] = mapped_column(Integer, default=0)
    imprumut_pe_loc: Mapped[int] = mapped_column(Integer, default=0)
    imprumut_la_domiciliu: Mapped[int] = mapped_column(Integer, default=0)
    imprumut_inter_bibliotecar: Mapped[int] = mapped_column(Integer, default=0)

    carti: Mapped[int] = mapped_column(Integer, default=0)
    publicatii_seriale: Mapped[int] = mapped_column(Integer, default=0)
    documente_muzica: Mapped[int] = mapped_column(Integer, default=0)
    documente_audiovizuale: Mapped[int] = mapped_column(Integer, default=0)
    documente_electronice_cd_dvd: Mapped[int] = mapped_column(Integer, default=0)
    alte_documente: Mapped[int] = mapped_column(Integer, default=0)

    limba_romana: Mapped[int] = mapped_column(Integer, default=0)
    alte_limbi: Mapped[int] = mapped_column(Integer, default=0)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA IV — Documente după conținut CZU (Copii / Adulți)
# ---------------------------------------------------------------------------


class DocumenteContinutCZU(Base):
    __tablename__ = "documente_continut_czu"
    __table_args__ = (
        UniqueConstraint(
            "an", "luna", "data", "categorie_varsta", name="uq_part04_an_luna_data_cat"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[str] = mapped_column(String, nullable=False)
    categorie_varsta: Mapped[str] = mapped_column(String, nullable=False)

    total_imprumuturi: Mapped[int] = mapped_column(Integer, default=0)
    czu_0_generalitati: Mapped[int] = mapped_column(Integer, default=0)
    czu_1_filozofie: Mapped[int] = mapped_column(Integer, default=0)
    czu_2_religie: Mapped[int] = mapped_column(Integer, default=0)
    czu_3_stiinte_sociale: Mapped[int] = mapped_column(Integer, default=0)
    czu_5_matematica: Mapped[int] = mapped_column(Integer, default=0)
    czu_6_stiinte_aplicate: Mapped[int] = mapped_column(Integer, default=0)
    czu_7_arte: Mapped[int] = mapped_column(Integer, default=0)
    czu_8_limbi: Mapped[int] = mapped_column(Integer, default=0)
    czu_9_geografie: Mapped[int] = mapped_column(Integer, default=0)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA V — Cercetări bibliografice (Copii / Adulți, rânduri pe cereri)
# ---------------------------------------------------------------------------


class CercetariBibliografice(Base):
    __tablename__ = "cercetari_bibliografice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)
    categorie_varsta: Mapped[str] = mapped_column(String, nullable=False)

    data_primirii_cererii: Mapped[str] = mapped_column(String, nullable=False)
    total_referinte: Mapped[int] = mapped_column(Integer, default=0)
    date_despre_solicitant: Mapped[str | None] = mapped_column(String, nullable=True)
    statut_socio_profesional: Mapped[str | None] = mapped_column(String, nullable=True)
    referinta: Mapped[str | None] = mapped_column(Text, nullable=True)
    cercetare_bibliografica: Mapped[str | None] = mapped_column(String, nullable=True)
    consultatie: Mapped[str | None] = mapped_column(String, nullable=True)
    referinta_tematica: Mapped[str | None] = mapped_column(String, nullable=True)
    referinta_de_concretizare: Mapped[str | None] = mapped_column(String, nullable=True)
    referinta_de_adresa: Mapped[str | None] = mapped_column(String, nullable=True)
    referinta_factologie: Mapped[str | None] = mapped_column(String, nullable=True)
    limite_cronologice: Mapped[str | None] = mapped_column(String, nullable=True)
    surse_consultatie: Mapped[int] = mapped_column(Integer, default=0)
    numar_descrieri_bibliografice: Mapped[int] = mapped_column(Integer, default=0)
    surse_recomandate: Mapped[int] = mapped_column(Integer, default=0)
    data_finalizarii_cererii: Mapped[str | None] = mapped_column(String, nullable=True)
    responsabil: Mapped[str | None] = mapped_column(String, nullable=True)
    # Câmpuri vechi — păstrate pentru migrare date
    tema: Mapped[str | None] = mapped_column(Text, nullable=True)
    tip_referinta_bibliografica: Mapped[str | None] = mapped_column(String, nullable=True)
    tip_referinta_grup: Mapped[str | None] = mapped_column(String, nullable=True)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA VI — Activități de informare (Copii / Adulți, evenimente)
# ---------------------------------------------------------------------------


class ActivitatiInformare(Base):
    __tablename__ = "activitati_informare"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)
    categorie_varsta: Mapped[str] = mapped_column(String, nullable=False)

    data: Mapped[str] = mapped_column(String, nullable=False)
    grup_tinta_subiect: Mapped[str | None] = mapped_column(String, nullable=True)
    activitate_individuala: Mapped[str | None] = mapped_column(String, nullable=True)
    activitate_grup: Mapped[str | None] = mapped_column(String, nullable=True)
    activitate_public_larg: Mapped[str | None] = mapped_column(String, nullable=True)
    numar_participanti: Mapped[int] = mapped_column(Integer, default=0)
    documente_consultate: Mapped[int] = mapped_column(Integer, default=0)
    responsabil: Mapped[str | None] = mapped_column(String, nullable=True)
    gen_activitate: Mapped[str | None] = mapped_column(String, nullable=True)  # vechi — migrare

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA VII — Documente electronice online (Copii / Adulți, pe luni)
# ---------------------------------------------------------------------------


class DocumenteElectronice(Base):
    __tablename__ = "documente_electronice"
    __table_args__ = (
        UniqueConstraint("an", "luna", "categorie_varsta", name="uq_part07_an_luna_cat"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–12
    categorie_varsta: Mapped[str] = mapped_column(String, nullable=False)

    total_documente_electronice: Mapped[int] = mapped_column(Integer, default=0)
    mediu_email: Mapped[int] = mapped_column(Integer, default=0)
    mediu_skype_retele_sociale: Mapped[int] = mapped_column(Integer, default=0)

    carti: Mapped[int] = mapped_column(Integer, default=0)
    publicatii_seriale: Mapped[int] = mapped_column(Integer, default=0)
    documente_muzica: Mapped[int] = mapped_column(Integer, default=0)
    documente_audiovizuale: Mapped[int] = mapped_column(Integer, default=0)
    documente_electronice_cd_dvd: Mapped[int] = mapped_column(Integer, default=0)
    alte_documente: Mapped[int] = mapped_column(Integer, default=0)

    limba_romana: Mapped[int] = mapped_column(Integer, default=0)
    alte_limbi: Mapped[int] = mapped_column(Integer, default=0)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA IX — Instruiri (tabel comun, multiple rânduri/zi)
# ---------------------------------------------------------------------------


class Instruiri(Base):
    __tablename__ = "instruiri"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)

    data: Mapped[str] = mapped_column(String, nullable=False)
    format_online: Mapped[bool] = mapped_column(Boolean, default=False)
    format_offline: Mapped[bool] = mapped_column(Boolean, default=False)

    ore_formala: Mapped[int] = mapped_column(Integer, default=0)
    ore_non_formala: Mapped[int] = mapped_column(Integer, default=0)
    ore_informala: Mapped[int] = mapped_column(Integer, default=0)

    tema_instruirii: Mapped[str | None] = mapped_column(Text, nullable=True)
    formator: Mapped[str | None] = mapped_column(String, nullable=True)
    total_participanti: Mapped[int] = mapped_column(Integer, default=0)
    adulti: Mapped[int] = mapped_column(Integer, default=0)
    copii_pana_16: Mapped[int] = mapped_column(Integer, default=0)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA XI — Activități culturale și științifice (Copii / Adulți)
# ---------------------------------------------------------------------------


class ActivitatiCulturale(Base):
    __tablename__ = "activitati_culturale"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)
    categorie_varsta: Mapped[str] = mapped_column(String, nullable=False)

    data: Mapped[str | None] = mapped_column(String, nullable=True)
    total_activitati: Mapped[int] = mapped_column(Integer, default=0)
    din_care_expozitii: Mapped[int] = mapped_column(Integer, default=0)
    tipul_activitatii: Mapped[str | None] = mapped_column(String, nullable=True)
    denumirea_activitatii: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_participanti: Mapped[int] = mapped_column(Integer, default=0)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA XII — Activități culturale ONLINE (Copii / Adulți)
# ---------------------------------------------------------------------------


class ActivitatiOnline(Base):
    __tablename__ = "activitati_online"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    an: Mapped[int] = mapped_column(Integer, nullable=False)
    luna: Mapped[int] = mapped_column(Integer, nullable=False)
    categorie_varsta: Mapped[str] = mapped_column(String, nullable=False)

    data: Mapped[str] = mapped_column(String, nullable=False)
    denumirea_activitatii: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipul_activitatii: Mapped[str | None] = mapped_column(String, nullable=True)
    platforma: Mapped[str | None] = mapped_column(String, nullable=True)
    vizualizari: Mapped[int] = mapped_column(Integer, default=0)
    impact: Mapped[int] = mapped_column(Integer, default=0)
    participanti_total: Mapped[int] = mapped_column(Integer, default=0)
    participanti_adulti: Mapped[int] = mapped_column(Integer, default=0)
    participanti_copii: Mapped[int] = mapped_column(Integer, default=0)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA XIII — Parteneri (CRUD listă, fără calendar)
# ---------------------------------------------------------------------------


class Parteneri(Base):
    __tablename__ = "parteneri"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partener: Mapped[str] = mapped_column(String, nullable=False)
    scope_local: Mapped[bool] = mapped_column(Boolean, default=False)
    scope_national: Mapped[bool] = mapped_column(Boolean, default=False)
    scope_international: Mapped[bool] = mapped_column(Boolean, default=False)
    date_contact: Mapped[str | None] = mapped_column(String, nullable=True)
    tip_contract: Mapped[str | None] = mapped_column(String, nullable=True)
    data_semnarii: Mapped[str | None] = mapped_column(String, nullable=True)
    termen_realizare: Mapped[str | None] = mapped_column(String, nullable=True)
    modalitati_realizare: Mapped[str | None] = mapped_column(Text, nullable=True)
    participanti_total: Mapped[int] = mapped_column(Integer, default=0)
    participanti_adulti: Mapped[int] = mapped_column(Integer, default=0)
    participanti_copii: Mapped[int] = mapped_column(Integer, default=0)
    impact: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# PARTEA XIV — Voluntariat (CRUD simplu)
# ---------------------------------------------------------------------------


class Voluntariat(Base):
    __tablename__ = "voluntariat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nume_prenume: Mapped[str] = mapped_column(String, nullable=False)
    nr_contract: Mapped[str | None] = mapped_column(String, nullable=True)
    data_inceperii: Mapped[str | None] = mapped_column(String, nullable=True)
    data_incheierii: Mapped[str | None] = mapped_column(String, nullable=True)
    numar_ore: Mapped[int] = mapped_column(Integer, default=0)
    activitati_realizate: Mapped[str | None] = mapped_column(Text, nullable=True)
    coordonator: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Toate modelele pentru creare automată a tabelelor
ALL_MODELS = [
    Personal,
    RangeConfig,
    EtichetaCustom,
    AppSetting,
    EvidentaUtilizatori,
    EvidentaUtilizatoriCopiiAdulti,
    DocumenteInregistrate,
    DocumenteContinutCZU,
    CercetariBibliografice,
    ActivitatiInformare,
    DocumenteElectronice,
    Instruiri,
    ActivitatiCulturale,
    ActivitatiOnline,
    Parteneri,
    Voluntariat,
]

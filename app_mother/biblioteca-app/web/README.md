# Registru Digital — versiune web (Supabase)

Versiune web, multi-user, a aplicației desktop. Mai mulți bibliotecari, mai multe
calculatoare (inclusiv Windows 7 cu un browser modern — Firefox ESR / Chrome ≤109),
toți lucrează pe **același registru**, în timp real.

Aceasta este o **dovadă de concept (POC)**: autentificare + Partea I editabilă +
sincronizare live între utilizatori. Restul părților și exporturile urmează (vezi roadmap).

---

## Arhitectură

```
   Browser (orice PC)                Supabase (free tier, în cloud)
  ┌───────────────────┐            ┌──────────────────────────────┐
  │ index.html        │  HTTPS     │ Auth  (login bibliotecari)   │
  │ + supabase-js CDN │ ─────────▶ │ PostgreSQL (datele registru) │
  │ (fără build/tool) │  WebSocket │ RLS   (securitate pe rânduri)│
  └───────────────────┘ ◀───────── │ Realtime (sincronizare live) │
                                    └──────────────────────────────┘
```

- **Fără server propriu de întreținut.** Supabase găzduiește baza de date, autentificarea
  și API-ul auto-generat. Pagina web e statică — poate sta pe Supabase, Netlify, GitHub
  Pages sau chiar deschisă direct de pe disc.
- **Free tier Supabase**: 500 MB bază de date (mai mult decât suficient pentru un registru),
  autentificare inclusă. ⚠ Proiectul gratuit se **suspendă după ~1 săptămână de inactivitate**
  — se reactivează dintr-un click din dashboard.

---

## Configurare Supabase (o singură dată, ~10 minute)

1. Creați cont pe [supabase.com](https://supabase.com) → **New project** (alegeți o regiune
   din Europa; notați parola bazei de date).
2. **SQL Editor** → New query → lipiți conținutul din
   [`supabase/schema.sql`](supabase/schema.sql) → **Run**. Creează cele 16 tabele + RLS.
3. **Authentication → Providers → Email**: activat. Pentru început, dezactivați
   „Confirm email" (Authentication → Providers → Email → *Confirm email* off) ca să puteți
   crea rapid utilizatori de test.
4. **Authentication → Users → Add user**: creați câte un cont pentru fiecare bibliotecar.
5. **Project Settings → API**: copiați **Project URL** și cheia **anon / public**.

## Rularea paginii

1. În folderul `web/`, copiați `config.example.js` în **`config.js`** și puneți `URL` + cheia `anon`.
2. Deschideți `index.html` în browser (dublu-click). Pentru distribuție, urcați folderul `web/`
   pe orice găzduire statică gratuită.
3. Autentificați-vă cu un cont creat la pasul 4. Ca să vedeți sincronizarea live: deschideți
   pagina în **două ferestre** și editați într-una — cealaltă se actualizează singură.

> `config.js` este ignorat de git (`.gitignore`). Cheia `anon` este publică prin design —
> securitatea reală vine din autentificare + politicile RLS din `schema.sql`.

---

## Ce reutilizăm din aplicația desktop

Logica de business e independentă de interfață și se poate refolosi într-un backend Python
(FastAPI) mai târziu — mai ales pentru **exporturi Word/PDF/Excel** (deja pur-Python în
`app/ui/export/`) și regulile de sincronizare/calcul (`app/core/`). POC-ul de acum vorbește
însă direct cu Supabase din browser, fără backend.

## Backup local („local + cloud")

Supabase e copia vie, partajată. Butonul **⬇ Backup local** descarcă pe PC o copie
completă a tuturor datelor, în două formate:

- **Excel (.xlsx)** — o foaie per parte; ușor de deschis și citit.
- **SQLite (.sqlite)** — aceeași bază de date pe care o folosește aplicația desktop.

Aplicația arată de cât timp nu s-a mai făcut backup și evidențiază butonul dacă au trecut
peste 24h. Astfel aveți mereu o copie locală, deținută de bibliotecă, pe lângă cea din cloud.
(Generarea rulează în browser, prin SheetJS + sql.js din CDN — fără server.)

## Roadmap

- [x] **Faza 0** — schema Supabase + POC Partea I editabilă + realtime multi-user
- [x] **Backup local** — descărcare Excel + SQLite, cu memento la 24h
- [ ] **Faza 1** — autentificare cu roluri, listă utilizatori (tabelul `personal`)
- [ ] **Faza 2** — restul părților editabile (II–VII, IX, XI–XIV) cu totaluri automate
- [ ] **Faza 3** — validări (range_config), etichete custom, text presets, istoric/audit
- [ ] **Faza 4** — backend Python (FastAPI) pentru export Word/PDF/Excel, refolosind codul existent
- [ ] **Faza 5** — migrarea datelor din bazele SQLite existente în Supabase

## Note despre concurență (multi-user)

RLS actual: orice utilizator autentificat poate citi/scrie tot (un singur registru comun).
La editări simultane pe aceeași celulă se aplică „ultima scriere câștigă"; Realtime împinge
imediat schimbările către ceilalți. Un istoric „cine/ce a modificat" (există deja
`register_audit` în desktop) se poate adăuga în Faza 3.

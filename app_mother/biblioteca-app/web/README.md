# Registru Digital — versiune web (Supabase)

Versiune web, multi-user, a aplicației desktop. Mai mulți bibliotecari, mai multe
calculatoare (inclusiv Windows 7 cu un browser modern — Firefox ESR / Chrome ≤109),
toți lucrează pe **același registru**, în timp real.

> ### 🔒 IMPORTANT — ca datele să NU se piardă (plan gratuit)
> Citește ghidul complet: **[docs/SIGURANTA-DATELOR.md](docs/SIGURANTA-DATELOR.md)**
> Pe scurt: proiectul gratuit Supabase intră în pauză după 7 zile de inactivitate
> și se șterge după 90 de zile în pauză. **Backup-ul nocturn** din repo-ul privat
> `vicuvi1/registru-backups` copiază toată baza în fiecare noapte, verifică restaurarea
> și ține proiectul activ. În plus: salvare sigură în aplicație, istoric modificări,
> folder local „registru mother" + copii în cloud.

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

## Rularea local (pe PC)

`config.js` conține deja URL-ul + cheia publică a proiectului, deci:

1. Deschideți `index.html` în browser (dublu-click).
2. Autentificați-vă cu un cont creat la pasul 4 de mai sus. Pentru a vedea sincronizarea live:
   deschideți pagina în **două ferestre** și editați într-una — cealaltă se actualizează singură.

> Cheia din `config.js` este cea PUBLICĂ (publishable) — sigură în browser cât timp RLS
> este activat (`schema.sql`). Cheia secretă (`sb_secret_...`) NU se pune niciodată aici.

## Deploy pe Vercel (deploy automat la fiecare push)

Site static — Vercel doar servește folderul, fără build.

1. [vercel.com](https://vercel.com) → **Add New… → Project** → importați repo-ul GitHub
   `mother_app_registru`.
2. **Root Directory** → apăsați *Edit* → alegeți `app_mother/biblioteca-app/web`.
3. Framework Preset: **Other** (se detectează din `vercel.json`). Fără build command.
4. **Deploy**. Primiți un URL de forma `https://<proiect>.vercel.app`.
5. **Settings → Git → Production Branch** → setați `web-supabase` (acolo trăiește codul web).

De acum, fiecare push pe `web-supabase` redeployează automat — nu mai trebuie să publicați manual.
Deschideți URL-ul Vercel pe orice PC (inclusiv Windows 7 cu Firefox ESR).

---

## Ce reutilizăm din aplicația desktop

Logica de business e independentă de interfață și se poate refolosi într-un backend Python
(FastAPI) mai târziu — mai ales pentru **exporturi Word/PDF/Excel** (deja pur-Python în
`app/ui/export/`) și regulile de sincronizare/calcul (`app/core/`). POC-ul de acum vorbește
însă direct cu Supabase din browser, fără backend.

## Salvarea datelor (nimic nu se pierde)

Fiecare modificare trece printr-o **coadă de salvare** (`outbox.js`):

1. Se salvează **în timp ce scrieți**, nu doar la ieșirea din celulă. Data e excepția: ea se salvează la ieșire.
2. Modificarea e scrisă întâi în `localStorage`, pe calculator, apoi trimisă la Supabase.
3. Iese din coadă **doar** după ce serverul confirmă că rândul s-a modificat. Un răspuns cu „0 rânduri”,
   adică sesiunea pierdută, **nu** mai trece drept „salvat”.
4. Dacă fila se închide, internetul cade sau sesiunea expiră, coada rămâne. Se retrimite automat:
   la revenirea internetului, după reconectare (apare o fereastră de login peste aplicație)
   sau la următoarea pornire.
5. Indicatorul din antet arată starea reală: **✔ Toate salvate** / **⏳ Se salvează** /
   **⚠ N în așteptare — păstrate pe calculator** / **🔒 reconectați-vă**. Click pe el încearcă din nou.
6. Lipirea din Excel, „Auto valori” și „Copiază luna trecută” trec tot prin coadă și se anulează cu un singur **Ctrl+Z**.

Teste: `node outbox.test.js` (coada) și `node logic.test.js` (calcule).

**Testare locală fără Supabase:** serviți folderul (ex. `npx http-server . -p 8095`) și deschideți
`index.html?mock=1`. Se încarcă `dev/mock-supabase.js`, o bază falsă păstrată în browser. Ea imită RLS, erorile
de rețea și sesiunea expirată. Din consolă: `__mock.offline = true`, `__mock.loggedOut = true`, `__mock.rows("instruiri")`.

## Migrări ale bazei de date (rulați o singură dată, în ordine)

După `schema.sql`, rulați în **Supabase → SQL Editor** fiecare fișier din `supabase/migrations/`.
Fișierele se pot rula de mai multe ori fără probleme.

**`001_istoric_acces_restaurare.sql`** aduce:
- **Acces doar pentru conturi aprobate** (tabelul `utilizatori_permisi`). La prima rulare sunt aprobate
  conturile care există deja. Rezultatul afișat la final = cine are acces. Dacă vedeți un email necunoscut:
  `delete from public.utilizatori_permisi where email = '...';`. Pentru un cont nou, creați-l întâi în
  Authentication → Users, apoi: `insert into public.utilizatori_permisi (email) values ('nume@exemplu.com');`.
  Recomandat și: **Authentication → Sign In / Providers → dezactivați „Allow new users to sign up”**.
- **Istoric modificări** (pagina 🕘 din aplicație). Se înregistrează orice adăugare, modificare sau ștergere,
  cu cine și când. „↶ Revino” readuce valorile sau rândul șters. Istoricul se păstrează 2 ani; jobul nocturn
  din `registru-backups` îl curăță.
- **Restaurare totul-sau-nimic** (`restore_tables`). Alegeți ce părți se restaurează. Dacă ceva eșuează,
  nu se schimbă nimic. Înainte se face automat o copie „înainte de restaurare”.

Aplicația funcționează și **înainte** de migrare: nu blochează pe nimeni, restaurează cu metoda veche,
iar pagina Istoric arată un mesaj. Testele SQL (`supabase/tests/`) rulează în CI pe Postgres 15 și 17.

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
- [x] **Faza 1** — toate cele 12 părți editabile (I–VII, IX, XI–XIV), navigație, autosave,
  realtime, ștergere rânduri, export Excel per parte, gestiune Personal (responsabili)
- [x] **Faza 2** — totaluri automate (coloane calculate + rânduri „Total" / „Total de la început"),
  antete grupate + super-grupuri (Partea IX), validare min/max
- [x] **Faza 3** — sincronizare între părți (III→IV, IX/XI→II), etichete custom (dublu-clic pe antet),
  text-presets (autocomplete), reguli intra-rând (split copii, oglindă III, split gen)
- [x] **Faza 4** — export **Word și PDF** în browser (fără backend)
- [x] **Faza 5** — import Excel + migrare din baza SQLite a aplicației desktop

### Rămâne pentru mai târziu (nice-to-have)
- Auto-generarea zilelor lucrătoare ale lunii (calendar) în părțile zilnice
- Sincronizare inversă II→IX/XI (acum e unidirecțională: IX/XI → II, read-only în II)
- Istoric „cine/ce a modificat" (audit vizibil)

## Note despre concurență (multi-user)

RLS actual: orice utilizator autentificat poate citi/scrie tot (un singur registru comun).
La editări simultane pe aceeași celulă se aplică „ultima scriere câștigă"; Realtime împinge
imediat schimbările către ceilalți. Un istoric „cine/ce a modificat" (există deja
`register_audit` în desktop) se poate adăuga în Faza 3.

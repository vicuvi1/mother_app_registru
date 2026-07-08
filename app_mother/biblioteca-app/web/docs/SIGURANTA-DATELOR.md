# 🔒 Siguranța datelor — cum NU pierdem datele registrului

> Ghid complet pentru administratorul aplicației **Registru Digital** (versiunea web).
> Obiectiv: datele să fie în siguranță **ani de zile**, pe planul **gratuit** Supabase,
> **fără să plătești** nimic.

---

## Cuprins
1. [Pe scurt (ce trebuie să faci)](#1-pe-scurt)
2. [De ce s-ar putea pierde datele](#2-de-ce-s-ar-putea-pierde-datele)
3. [Protecțiile deja incluse în aplicație](#3-protectiile-deja-incluse)
4. [Cum previi „pauza" (pas cu pas)](#4-cum-previi-pauza)
5. [Ping extern cu cron-job.org (recomandat) — valori gata de copiat](#5-ping-extern-recomandat)
6. [Backup și restaurare](#6-backup-si-restaurare)
7. [Rutina recomandată (bifează)](#7-rutina-recomandata)
8. [Depanare: dacă proiectul e în pauză sau lipsesc date](#8-depanare)
9. [Când (dacă vreodată) merită să plătești](#9-cand-merita-sa-platesti)

---

## 1. Pe scurt

- **Planul gratuit Supabase este suficient** pentru un registru de bibliotecă — datele sunt foarte mici (mult sub limita de 0,5 GB), chiar și pe 3–5 ani.
- **Singurul risc real** NU e spațiul, ci **inactivitatea**:
  - proiectul gratuit se **pune în pauză după 7 zile** fără activitate;
  - un proiect rămas în pauză **90 de zile** se **șterge definitiv**.
- **Ce trebuie să faci** ca să fii liniștit:
  1. ✅ **Ping automat zilnic** — deja pornit (GitHub Actions). Vezi §4.2.
  2. ✅ **(Recomandat) Ping extern** pe cron-job.org — 5 minute de configurare, apoi merge singur ani de zile. Vezi §5.
  3. ✅ **Folder local „registru mother"** pe calculator — copie completă a datelor. Vezi §6.1.
  4. ✅ **O descărcare pe lună** (Excel/SQLite) ținută pe stick/email/Drive. Vezi §6.3.

Dacă faci pașii 1–4, este **practic imposibil** să pierzi datele fără să plătești.

---

## 2. De ce s-ar putea pierde datele

Aplicația web ține datele în **Supabase** (o bază de date online, plan gratuit). Pe planul gratuit există trei lucruri de știut:

| Aspect | Plan gratuit | Impact pentru noi |
|---|---|---|
| **Spațiu bază de date** | 0,5 GB | Uriaș față de nevoile noastre. Un registru pe 3 ani ocupă ~5–20 MB. **Nu e o problemă.** |
| **Backup automat Supabase** | ❌ Nu există / nu se poate descărca | Supabase **nu** ne salvează dacă datele se șterg/corup. De aceea facem copii proprii (folder local, cloud, descărcări). |
| **Pauză la inactivitate** | ⏸️ După **7 zile** fără activitate | Proiectul „adoarme". Datele **rămân**, dar trebuie apăsat „Resume" în panoul Supabase. |
| **Ștergere după pauză** | 🗑️ După **90 de zile** în pauză | Aici e pericolul real: dacă nimeni nu deschide aplicația luni de zile (vacanță etc.), proiectul se poate șterge. |

👉 **Concluzie:** trebuie doar să ne asigurăm că proiectul **nu stă în pauză 90 de zile** și că avem **copii proprii** ale datelor. Ambele sunt rezolvate mai jos, gratuit.

Surse oficiale:
- Prețuri și limite: <https://supabase.com/pricing>
- Pauza proiectelor gratuite: <https://supabase.com/docs/guides/platform/free-project-pausing>
- Dimensiunea bazei de date: <https://supabase.com/docs/guides/platform/database-size>

---

## 3. Protecțiile deja incluse

Aplicația are deja, fără nimic de configurat:

1. **Ping automat zilnic (GitHub Actions)** — un „semnal de viață" trimis bazei de date de două ori pe zi, ca proiectul să nu intre în pauză. Fișier: `.github/workflows/keepalive.yml`.
2. **Folder local „registru mother"** — la prima pornire (în Chrome/Edge) aplicația creează pe calculator un folder unde salvează automat o copie completă a datelor (JSON), la fiecare backup, la 5 minute după modificări și când închizi fila.
3. **Backup în cloud (Supabase Storage)** — o copie completă (JSON) în bucket-ul `backups`, automat (implicit la 7 zile) și la cerere; se păstrează ultimele 15.
4. **Descărcare locală** — buton care descarcă tot registrul ca **Excel** + **SQLite**.
5. **RLS activat** — doar utilizatorii autentificați pot citi/scrie.

> ⚠️ Copiile din **folderul local** și **descărcările** sunt „în afara" Supabase — ele te salvează chiar dacă proiectul Supabase ar dispărea complet. Copia „cloud" e utilă, dar stă tot în proiectul Supabase.

---

## 4. Cum previi „pauza"

### 4.1 Cel mai simplu: folosește aplicația regulat
Dacă biblioteca **deschide aplicația măcar o dată la câteva zile**, proiectul nu intră niciodată în pauză. Utilizarea normală (completarea zilnică a registrului) e mai mult decât suficientă.

### 4.2 Ping automat prin GitHub Actions (deja pornit)
În acest repository există `.github/workflows/keepalive.yml`, care „ciocănește" baza de date **zilnic**.

**Cum verifici că merge:**
1. Intră pe pagina GitHub a proiectului → tab-ul **Actions**.
2. Alege workflow-ul **keepalive** din stânga.
3. Ar trebui să vezi rulări zilnice (verzi = succes). Poți apăsa **Run workflow** ca să-l rulezi manual.

**⚠️ Limită importantă a GitHub:** GitHub **dezactivează** un workflow programat dacă **nu se face nicio modificare (commit) în repository timp de 60 de zile**. Adică, dacă nimeni nu atinge codul 2 luni, ping-ul se poate opri.
- **Soluție sigură:** configurează în plus **ping extern** pe cron-job.org (§5) — acela nu depinde de GitHub și merge la nesfârșit.
- Alternativ: e suficient ca aplicația să fie folosită săptămânal (§4.1).

### 4.3 Emailurile de avertizare de la Supabase
Supabase trimite **un email de avertizare cu ~1 săptămână înainte** de a pune proiectul în pauză, și un al doilea când l-a pus. Dacă primești un astfel de email:
- **Deschide aplicația** (sau panoul Supabase) — orice activitate anulează pauza.

### 4.4 Cum reactivezi un proiect pus în pauză
Dacă proiectul a intrat totuși în pauză (datele sunt încă acolo timp de 90 de zile):
1. Intră pe <https://supabase.com/dashboard> și autentifică-te.
2. Alege organizația și proiectul pus în pauză.
3. Apasă **Resume project** și confirmă.
4. După câteva minute proiectul revine cu toate datele.

---

## 5. Ping extern (recomandat)

Aceasta este **cea mai sigură** metodă: un serviciu gratuit sună baza de date în fiecare zi, independent de GitHub și de faptul că cineva deschide sau nu aplicația.

### Varianta A — cron-job.org (gratuit, ~5 minute)

1. Creează un cont gratuit pe **<https://cron-job.org>**.
2. Apasă **Create cronjob** (Creează job).
3. Completează:
   - **Title / Titlu:** `Keep-alive Registru`
   - **URL / Address:**
     ```
     https://wmtmsbbqhjyxctvwaggz.supabase.co/rest/v1/app_settings?select=cheie&limit=1
     ```
   - **Schedule / Program:** o dată pe zi (ex. în fiecare zi la ora 08:00). *(Chiar și „la fiecare 6 ore" e ok.)*
4. Deschide secțiunea **Advanced / Headers** (Anteturi) și adaugă **două** anteturi:

   | Header (Nume) | Value (Valoare) |
   |---|---|
   | `apikey` | `sb_publishable_k0eI5YWQXBtz8Dkya1mfng_gn5iAsGS` |
   | `Authorization` | `Bearer sb_publishable_k0eI5YWQXBtz8Dkya1mfng_gn5iAsGS` |

5. Salvează. Gata — de acum baza de date primește o cerere zilnic, **automat, ani de zile**.

> 🔐 Cheia de mai sus este **cheia publică** (publishable) — e sigură de folosit (protecția reală o dă RLS). Nu este parola/cheia secretă.

### Varianta B — UptimeRobot (alternativă gratuită)
1. Cont gratuit pe **<https://uptimerobot.com>**.
2. **Add New Monitor** → tip **HTTP(s)**.
3. **URL:** `https://wmtmsbbqhjyxctvwaggz.supabase.co/rest/v1/app_settings?select=cheie&limit=1`
4. La **Custom HTTP Headers** adaugă aceleași două anteturi ca mai sus (`apikey` și `Authorization`).
5. Interval de verificare: 5–30 minute (implicit e ok). Salvează.

> Notă: UptimeRobot fără anteturi poate primi „401" — proiectul tot rămâne activ (a primit o cerere), dar cu anteturile de mai sus vei vedea „200 OK", mai curat.

### Test rapid (opțional, din linia de comandă)
```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://wmtmsbbqhjyxctvwaggz.supabase.co/rest/v1/app_settings?select=cheie&limit=1" \
  -H "apikey: sb_publishable_k0eI5YWQXBtz8Dkya1mfng_gn5iAsGS" \
  -H "Authorization: Bearer sb_publishable_k0eI5YWQXBtz8Dkya1mfng_gn5iAsGS"
```
Dacă afișează `200` sau `206`, totul e în regulă.

---

## 6. Backup și restaurare

### 6.1 Folder local „registru mother" (Chrome / Edge)
- La **prima pornire** aplicația te întreabă unde salvezi — alege **Desktop**; se creează automat folderul **`registru mother`**.
- Aplicația salvează acolo `registru_backup.json` (copia curentă) + copii datate.
- **Pe fiecare sesiune**, din motive de securitate ale browserului, apasă o dată butonul **„📁 Salvează în folderul registru mother"** de pe pagina **Acasă** — asta reactivează salvarea automată pentru sesiunea respectivă.
- Funcționează în **Chrome/Edge** (inclusiv pe Windows 7). În **Firefox** nu există această funcție — folosește descărcarea (§6.3).

### 6.2 Backup în cloud
- Automat: implicit la 7 zile (setabil în **⚙ Setări → Backup automat**).
- Manual: **Acasă → „⬇ Salvează copie"**.
- Restaurare: **Acasă → „☁ Restaurează din cloud"** (poți și descărca orice copie pe PC).

### 6.3 Descărcare lunară (recomandat)
- **Acasă → „⬇ Salvează copie"** descarcă **Excel + SQLite**.
- **Păstrează o copie pe lună** în afara calculatorului: pe un **stick USB**, pe **email** (trimite-ți-o ție) sau pe **Google Drive/OneDrive**.
- Aceasta este plasa de siguranță supremă: chiar dacă totul din online ar dispărea, ai datele.

### 6.4 Cum restaurezi datele
- **Din folderul local:** Acasă → **„📂 Restaurează din folderul local"**.
- **Din cloud:** Acasă → **„☁ Restaurează din cloud"** → alege copia.
- **Dintr-un fișier (SQLite/Excel):** meniul **⬆ Import / Migrare** → alege fișierul.
  - Bifează **„Înlocuiește datele existente"** pentru o restaurare curată (șterge înainte);
  - fără bifă, importul e sigur și **nu dublează** datele.

---

## 7. Rutina recomandată

| Cât de des | Ce faci | De ce |
|---|---|---|
| **Zilnic** | *(automat)* ping keep-alive + salvare în folderul local | Proiectul nu intră în pauză; ai copie locală la zi |
| **La fiecare sesiune** | Un clic pe „📁 Salvează în folderul registru mother" | Reactivează salvarea automată în folder |
| **Săptămânal** | Deschide aplicația (oricum se folosește) | Garantează activitate |
| **Lunar** | „⬇ Salvează copie" → pune Excel/SQLite pe USB/email/Drive | Copie în afara calculatorului |
| **Anual** | La final de an: **Registru final → Export Word/PDF** + o descărcare arhivată | Arhivă oficială pe an |
| **O singură dată** | Configurează ping extern pe cron-job.org (§5) | Protecție „pentru totdeauna", independentă de GitHub |

---

## 8. Depanare

**„Aplicația nu se încarcă / eroare de conectare."**
→ Proiectul poate fi în pauză. Intră pe <https://supabase.com/dashboard> și apasă **Resume** (§4.4). Apoi configurează ping-ul extern (§5) ca să nu se mai repete.

**„Am primit email că proiectul va fi pus în pauză."**
→ Deschide aplicația o dată. Gata. (Și configurează §5.)

**„Lipsesc date / cineva a șters din greșeală."**
→ Ai mai multe variante, în ordine:
1. **Ctrl+Z** în aplicație (anulează ultimele modificări, inclusiv adăugări/ștergeri de rânduri).
2. **Restaurează din folderul local** (Acasă) — copia de pe calculator.
3. **Restaurează din cloud** (Acasă).
4. **Import** dintr-o descărcare Excel/SQLite mai veche.

**„Backup-ul cloud spune «eșuat»."**
→ Probabil nu s-a rulat încă blocul SQL care creează bucket-ul `backups`. Rulează o dată `web/supabase/schema.sql` în Supabase (SQL Editor). Folderul local și descărcările funcționează oricum.

**„Ping-ul GitHub s-a oprit."**
→ GitHub dezactivează workflow-urile programate după 60 de zile fără commit. Fie faci orice mică modificare în repo, fie (mai bine) te bazezi pe ping-ul extern din §5.

---

## 9. Când (dacă vreodată) merită să plătești

Planul **Pro** (~25 $/lună) aduce: **fără pauză niciodată**, **backup zilnic automat** (7 zile, descărcabile) și spațiu mai mare. Pentru o singură bibliotecă mică, **nu este necesar** — pașii din acest ghid oferă siguranță echivalentă gratuit. Ia în calcul Pro doar dacă:
- vrei backup automat gestionat de Supabase, fără griji, sau
- ai mai multe biblioteci/foarte multe date.

---

### Rezumat
Free tier = suficient. Riscul e doar inactivitatea. Îl elimini cu **ping-ul automat** (deja pornit) + **un ping extern** (5 minute pe cron-job.org) și îți garantezi datele cu **folderul local** + **o descărcare lunară**. Cu acestea, datele registrului sunt în siguranță ani de zile, fără niciun cost. 🔒

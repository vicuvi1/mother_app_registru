# 🔒 Siguranța datelor — cum NU pierdem datele registrului

> Ghid pentru administratorul aplicației **Registru Digital** (versiunea web).
> Obiectiv: datele să fie în siguranță **ani de zile**, pe planul **gratuit** Supabase.
> Actualizat: octombrie 2026.

---

## 1. Pe scurt

Datele stau în **Supabase** (bază de date online, plan gratuit). Ce le protejează, de la cel mai important:

| # | Protecție | Unde | Ce face |
|---|---|---|---|
| 1 | **Backup zilnic în afara Supabase** | repo privat GitHub `vicuvi1/registru-backups` | În fiecare noapte (~04:30) copiază **toată** baza de date (SQL + un CSV pe tabel). Verifică dacă copia se poate restaura. Păstrează **fiecare zi, pentru totdeauna**. Tot el ține proiectul Supabase activ. |
| 2 | **Salvare sigură în aplicație** | browser | Fiecare modificare e păstrată întâi pe calculator și trimisă până când serverul confirmă. Merge și dacă se închide fila, cade internetul sau expiră sesiunea. |
| 3 | **Istoric modificări** | pagina 🕘 din aplicație | Cine, când, ce valoare a schimbat. „↶ Revino” readuce valoarea sau rândul șters. |
| 4 | **Copii din aplicație** | folder local „registru mother” + cloud | Copii complete: ultimele 24, una pe zi pe o lună, una pe lună pentru totdeauna. |
| 5 | **Acces doar pentru conturi aprobate** | Supabase | Tabelul `utilizatori_permisi`. Înregistrarea conturilor noi e oprită. |

Dacă GitHub trimite un email că jobul **backup** a eșuat, citiți §5.

---

## 2. De ce s-ar putea pierde datele (și ce am făcut)

| Risc | Plan gratuit Supabase | Ce ne protejează |
|---|---|---|
| **Pauză la inactivitate** | după 7 zile fără activitate | Backup-ul nocturn se conectează la bază în fiecare noapte. Asta e activitate reală, deci proiectul nu mai intră în pauză. |
| **Ștergere după 90 de zile în pauză** | proiectul dispare | Nu mai ajunge în pauză. Chiar dacă ar dispărea, backup-ul zilnic e în GitHub, în afara Supabase. |
| **Fără backup Supabase** | planul gratuit nu are copii descărcabile | Backup-ul nocturn + copiile din aplicație |
| **Modificări pierdute la închiderea filei** | — | Coada de salvare a aplicației (vezi §4) |
| **O greșeală / ștergere din neatenție** | — | Ctrl+Z, Istoric → „↶ Revino”, restaurare din copie |
| **Acces străin** | înregistrarea era deschisă | Înregistrare oprită + doar conturi aprobate |

> Vechiul ping `keepalive.yml` din repo-ul public rămâne ca rezervă. GitHub îl oprește singur după 60 de zile
> fără modificări în repo. Nu mai contează: backup-ul nocturn din repo-ul **privat** face și treaba asta.

---

## 3. Backup-ul nocturn (repo `registru-backups`)

- **Unde:** https://github.com/vicuvi1/registru-backups, folderul `data/`.
  - `registru.sql` = copia completă (refacere totală).
  - `csv/<tabel>.csv` = un fișier pe parte, se deschide în Excel.
  - `counts.txt` = câte rânduri are fiecare tabel.
- **Când:** zilnic ~04:30. Fiecare noapte = un commit „backup AAAA-LL-ZZ”, deci istoricul repo-ului are **fiecare zi**.
- **Verificare automată:** copia e restaurată într-o bază goală și se compară numărul de rânduri.
- **Alertă pe email (de la GitHub)** dacă:
  - backup-ul sau verificarea eșuează;
  - lipsește parola (secretul);
  - au dispărut peste 20% din rânduri sau un tabel plin s-a golit.
- **Parola bazei:** stă doar în secretul `SUPABASE_DB_URL` al repo-ului (Settings → Secrets and variables → Actions).
  Dacă resetați parola în Supabase, actualizați și secretul (✏️ lângă nume).
- **Rulare manuală:** repo → Actions → **backup** → Run workflow.
- Tot acest job curăță istoricul modificărilor mai vechi de 2 ani din bază. Rămâne oricum în copiile zilnice.

Instrucțiuni de restaurare (un tabel / tot proiectul): `README.md` din repo-ul `registru-backups`.

---

## 4. Salvarea în aplicație

- Valorile se salvează **în timp ce scrieți**, nu doar la ieșirea din celulă. Data e excepția: ea se salvează la ieșire și trebuie scrisă `ZZ.LL`.
- Indicatorul din antet arată starea reală:
  **✔ Toate salvate** · **⏳ Se salvează** · **⚠ N în așteptare — păstrate pe calculator** · **🔒 reconectați-vă**.
- Dacă scrie **⚠** sau **🔒**, modificările **nu sunt pierdute**. Sunt pe acest calculator și se trimit singure
  când revine internetul, după reconectare sau la următoarea deschidere a aplicației, **pe același calculator și browser**.
- Dacă închideți fila cu ceva netrimis, browserul întreabă „Părăsiți pagina?”. Alegeți **Rămâneți** și așteptați „✔ Toate salvate”.

---

## 5. Ce faceți dacă…

**…ați greșit o valoare sau ați șters un rând?**
1. **Ctrl+Z** imediat (pe aceeași pagină).
2. **🕘 Istoric modificări** → găsiți linia → **↶ Revino**.
3. **Acasă → ☁ Restaurează din cloud** (sau 📂 din folderul local) → alegeți copia → **bifați doar partea afectată**.
   Înainte de restaurare se face automat o copie „înainte de restaurare”, deci și restaurarea se poate anula.

**…GitHub a trimis email „backup failed”?**
Deschideți linkul din email și citiți pasul roșu:
- *Stop if the database secret is missing* → secretul `SUPABASE_DB_URL` lipsește sau a fost șters.
- *Back up the live database* → parola s-a schimbat (actualizați secretul) sau proiectul e în pauză (vezi mai jos).
- *Alert - many rows disappeared* → verificați aplicația. Ziua precedentă e intactă în istoricul repo-ului (§3).

**…aplicația nu se încarcă / „eroare de conectare”?**
Proiectul ar putea fi în pauză. Intrați pe https://supabase.com/dashboard → proiectul → **Resume project**.
Datele rămân acolo 90 de zile și sunt oricum în backup-ul nocturn.

**…un bibliotecar nou are nevoie de acces?**
1. Supabase → Authentication → Users → **Add user**.
2. SQL Editor: `insert into public.utilizatori_permisi (email) values ('nume@exemplu.com');`

Pentru a scoate pe cineva: `delete from public.utilizatori_permisi where email = '...';`

**…schimbați calculatorul?**
Totul e online, deci doar vă autentificați. Pentru copia locală, apăsați o dată „📁 Salvează în folderul registru mother”.

---

## 6. Rutina recomandată

| Cât de des | Ce | Cine |
|---|---|---|
| Zilnic | backup complet + verificare + menținere activă | **automat** (GitHub) |
| Orar, cât e deschisă aplicația | copie în folderul local / cloud | **automat** (aplicația) |
| Lunar | aruncați o privire în repo-ul `registru-backups` → Actions: rulări verzi | administrator |
| Anual | **Registru final → Export Word/PDF** pentru arhivă | bibliotecar |

---

## 7. Când (dacă vreodată) merită plătit

Planul **Pro** Supabase (~25 $/lună) aduce fără pauză + backup zilnic gestionat. Pentru o bibliotecă **nu e necesar**:
backup-ul nocturn de mai sus oferă același lucru gratuit, plus istoric nelimitat al copiilor.

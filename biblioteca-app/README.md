# Registru Digital Bibliotecă

Aplicație desktop offline pentru evidența activității bibliotecii (înlocuiește registrul fizic).

## Cerințe

- Windows 10/11
- Python 3.11+ (doar pentru dezvoltare; utilizatorii pot folosi `RegistruDigital.exe`)

## Pornire rapidă (dezvoltare)

```bat
cd biblioteca-app
run.bat
```

Prima rulare creează mediul virtual și instalează dependențele.

## Utilizare

1. **Prima pornire** — parcurgeți asistentul de configurare (nume bibliotecă, personal, range-uri).
2. **Părți** — selectați o parte din meniul stâng (I–XIV).
3. **Luni** — folosiți tab-urile de lună pentru părțile zilnice.
4. **Salvare** — automată la 60s; manual: **Ctrl+S** sau butonul Salvează.
5. **Export** — **Ctrl+E** sau meniul Export; formate Word, PDF, Excel.
6. **Backup** — Fișier → *Salvează copie registru*; copiile sunt în `app/data/backups/`.
7. **Restaurare** — Fișier → *Restaurează din copie* (necesită repornirea aplicației).

La fiecare pornire se creează automat o copie de rezervă (ultimele 5 păstrate).

## Scurtături

| Tastă | Acțiune |
|-------|---------|
| Ctrl+S | Salvează |
| Ctrl+E | Export pagină curentă |
| Ctrl+R | Registru complet |
| Ctrl+Z | Anulează ultima editare (celulă) |
| F1 | Ajutor |
| Ctrl+Q | Ieșire |

## Construire .exe (PyInstaller)

```bat
cd biblioteca-app
build.bat
```

Executabilul apare în `dist/RegistruDigital/`.

## Date locale

- Bază de date: `app/data/biblioteca.db`
- Jurnal: `app/data/biblioteca.log`
- Backup-uri: `app/data/backups/`

**Nu ștergeți** `biblioteca.db` — conține tot registrul.

## Teste

```bat
venv\Scripts\python.exe -m pytest tests\ -v
```

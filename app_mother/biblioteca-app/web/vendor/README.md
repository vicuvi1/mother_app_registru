# vendor/ — biblioteci externe, cu versiune fixă

Aceste fișiere stau în aplicație, nu se mai iau de pe CDN (jsdelivr). Așa aplicația:
- nu se poate strica peste noapte când apare o versiune nouă (înainte se încărca `supabase-js@2`, adică „ultima 2.x”);
- merge și dacă CDN-ul e picat sau blocat în rețeaua bibliotecii.

| Fișier | Pachet npm | Versiune | Licență |
|---|---|---|---|
| `supabase-js-2.117.2.js` | `@supabase/supabase-js` (`dist/umd/supabase.js`) | 2.117.2 | MIT |
| `xlsx-0.18.5.full.min.js` | `xlsx` (`dist/xlsx.full.min.js`) | 0.18.5 | Apache-2.0 |
| `sql-wasm.js`, `sql-wasm.wasm` | `sql.js` (`dist/`) | 1.10.3 | MIT |
| `pdfmake-0.2.7.min.js`, `pdfmake-0.2.7-vfs_fonts.js` | `pdfmake` (`build/`) | 0.2.7 | MIT |

**Actualizare:** `npm pack <pachet>@<versiune>`, copiați fișierul din tabel, schimbați numele/versiunea aici
și în `index.html`, apoi testați (`index.html?mock=1` + o autentificare reală). Alegeți o versiune
publicată de cel puțin 2 săptămâni.

Deschis direct de pe disc (`file://`), browserul nu permite încărcarea `sql-wasm.wasm`. În acest caz
`backup.js` / `import.js` îl iau de pe CDN (doar pentru export/import SQLite).

// ============================================================================
// Folder local de siguranță „registru mother" — copie completă a datelor pe
// acest calculator, independentă de cloud. Folosește File System Access API
// (Chrome/Edge). Handle-ul folderului e păstrat în IndexedDB între sesiuni.
// La prima alegere, se CREEAZĂ automat subfolderul „registru mother" în locul
// ales (recomandat: Desktop). Pe alt PC, se alege din nou o dată.
// ============================================================================
(function () {
  const supported = typeof window !== "undefined" && "showDirectoryPicker" in window;
  const DBN = "registruFS", STORE = "h", KEY = "folder";

  function openDB() {
    return new Promise((res, rej) => {
      const r = indexedDB.open(DBN, 1);
      r.onupgradeneeded = () => { try { r.result.createObjectStore(STORE); } catch (e) {} };
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
  }
  async function idbGet(k) { const db = await openDB(); return new Promise((res) => { const t = db.transaction(STORE, "readonly").objectStore(STORE).get(k); t.onsuccess = () => res(t.result); t.onerror = () => res(null); }); }
  async function idbSet(k, v) { const db = await openDB(); return new Promise((res) => { const tx = db.transaction(STORE, "readwrite"); tx.objectStore(STORE).put(v, k); tx.oncomplete = () => res(); tx.onerror = () => res(); }); }
  async function idbDel(k) { const db = await openDB(); return new Promise((res) => { const tx = db.transaction(STORE, "readwrite"); tx.objectStore(STORE).delete(k); tx.oncomplete = () => res(); tx.onerror = () => res(); }); }

  async function perm(h, request) {
    if (!h.queryPermission) return true;
    const o = { mode: "readwrite" };
    if ((await h.queryPermission(o)) === "granted") return true;
    if (request) return (await h.requestPermission(o)) === "granted";
    return false;
  }

  // Alege un părinte (Desktop) → creează/deschide „registru mother" în el.
  async function pickFolder() {
    if (!supported) throw new Error("Folosiți Chrome sau Edge pentru salvarea în folder local.");
    const parent = await window.showDirectoryPicker({ id: "registru-mother", mode: "readwrite", startIn: "desktop" });
    const folder = await parent.getDirectoryHandle("registru mother", { create: true });
    await idbSet(KEY, folder);
    return folder;
  }
  async function getFolder(request) {
    if (!supported) return null;
    const h = await idbGet(KEY); if (!h) return null;
    if (!(await perm(h, request))) return null;
    return h;
  }
  async function hasFolder() { if (!supported) return false; return !!(await idbGet(KEY)); }
  async function forget() { await idbDel(KEY); }

  async function writeText(folder, name, text) { const fh = await folder.getFileHandle(name, { create: true }); const w = await fh.createWritable(); await w.write(text); await w.close(); }
  async function readText(folder, name) { const fh = await folder.getFileHandle(name); const f = await fh.getFile(); return await f.text(); }

  async function pruneDated(folder, keep) {
    const names = [];
    for await (const [name, h] of folder.entries()) { if (h.kind === "file" && /^registru_\d/.test(name)) names.push(name); }
    names.sort();
    if (names.length > keep) for (const n of names.slice(0, names.length - keep)) { try { await folder.removeEntry(n); } catch (e) {} }
  }

  // Scrie copia „vie" (registru_backup.json) + o copie datată; păstrează ultimele 30.
  async function saveSnapshot(folder, obj, stamp) {
    const json = JSON.stringify(obj);
    await writeText(folder, "registru_backup.json", json);
    if (stamp) { try { await writeText(folder, `registru_${stamp}.json`, json); await pruneDated(folder, 30); } catch (e) {} }
  }
  async function readSnapshot(folder) { return JSON.parse(await readText(folder, "registru_backup.json")); }

  window.RegistruLocalFolder = { supported, pickFolder, getFolder, hasFolder, forget, saveSnapshot, readSnapshot };
})();

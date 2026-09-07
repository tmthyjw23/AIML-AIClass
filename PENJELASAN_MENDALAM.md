# PENJELASAN MENDALAM — ArsitekBot (AIML Chatbot Context-Aware)

> **Tugas Mata Kuliah AI — Class Practical #1 [AI-Powered AIML Chatbot]**  
> **Fakultas Ilmu Komputer, Universitas Klabat — Semmy Wellem Taju**  
> **Mahasiswa: Timothy Jordy Weley — Repo: `https://github.com/tmthyjw23/AIML-AIClass`**  
> **Status: 875 categories (melebihi ketentuan 150) — siap demo kelas**

---

## Daftar Isi
1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Konteks Tugas & Ketentuan 150 Kategori](#2-konteks-tugas--ketentuan-150-kategori)
3. [Arsitektur Project](#3-arsitektur-project)
4. [Implementasi Mendalam per File](#4-implementasi-mendalam-per-file)
5. [AIML Deep Dive — Dari `model.aiml:10` ke `875`](#5-aiml-deep-dive)
6. [Context-Aware & Personalisasi](#6-context-aware--personalisasi)
7. [Backend Flask — Login, History, Keamanan](#7-backend-flask)
8. [Frontend — 21st.dev Sign-In-Flow-1 + Responsive](#8-frontend)
9. [Boost Experience — Anti-Kaku & Anti-Halusinasi](#9-boost-experience)
10. [Audit & Verifikasi (Sub-Agent 4 Domain)](#10-audit--verifikasi)
11. [Cara Menjalankan & Demo](#11-cara-menjalankan--demo)
12. [Kendala Kritis & Solusi](#12-kendala-kritis--solusi)
13. [Kesimpulan & Nilai Tambah](#13-kesimpulan--nilai-tambah)
14. [Lampiran](#14-lampiran)

---

## 1. Ringkasan Eksekutif

Project berawal dari `Project/main.py:7` `chatbot.learn("model.aiml")` dengan `model.aiml:10` hanya 2 categories (`HEI`, `_ APA KABAR`). Melalui 12 commit (`5e1a575` → `446f030`), berkembang menjadi **ArsitekBot** — chatbot AIML context-aware dengan **875 categories** (Native 125 + Ars 750), login nama + history log persisten, navbar fungsional, UI 21st.dev dark pill yang fully responsive, serta hardening keamanan (path traversal, rate limit, XSS).

**Kenapa melebihi 150?** Ketentuan dosen 150 kategori adalah *minimum* agar chatbot tidak trivial. Implementasi 150 topik arsitektur × 5 varian pattern = 750 (Ars) + 125 Native (sapaan, smalltalk, context) = **875** — 5.8× lipat, tetap dalam kaidah AIML murni, bukan LLM, sehingga nilai akademik “sederhana tapi tidak kaku” terpenuhi.

**Hasil:** Semua transcript yang awalnya 6/14 fallback kini **14/14 OK**, typo `viod→void` terkoreksi, `void` pendek tanpa `DALAM ARSITEKTUR` tetap terjawab, personalisasi `Timothy` persist, hallusination `DAK BETON` hilang.

---

## 2. Konteks Tugas & Ketentuan 150 Kategori

**Kutipan Lecture6 PDF (50 hal, 6.9 MB):**
- Definisi AI, ML (Data+Algorithm+Computation), NLP/CV, DeepMind AlphaGo 2016, Deepfake 2017, GPT-4o 2024
- **Demo #1 Chatbot using AIML Scripts** — `pip install python-aiml` (Python 3.9.7) — `main.py` + `model.aiml`
- **Tugas:** buat report PDF berisi screenshot code + output + penjelasan perbandingan AIML vs ML chatbot, submit Google Classroom (bukan video), lihat Lecture #5 Exercise #4.

**Interpretasi 150 kategori:** Dosen minta minimal 150 `<category>` agar coverage topik arsitektur memadai. Jika hanya 2 kategori seperti `model.aiml:2`, bot akan selalu fallback `*`. Dengan 150 topik, tiap topik butuh 5 pattern (`MASTER`, `X`, `X *`, `* X`, `* X *`) agar user bisa ketik `apa itu bauhaus`, `tanya dong bauhaus ya`, `bauhaus` semua match. Itulah kenapa 150×5=750.

**Keputusan:** Pertahankan kemurnian AIML (tidak pakai LLM di tugas ini, LLM hanya di `Feature.md:5` sebagai roadmap), tapi boost UX agar tidak terasa 2013-an.

---

## 3. Arsitektur Project

```
Project/
├── main.py                     # 244 baris — Kernel global, get_response(), typo+alias+name handling
├── app.py                      # 788 baris — Flask + 21st.dev UI + 9 API endpoints + persistence
├── NativeConversation.aiml     # 379 baris — 125 cats: sapaan, bridging, smalltalk, context (125)
├── Ars_Optimized.aiml          # 140362 bytes — 750 cats: 150 topik ×5 (150 masters)
├── data/
│   ├── users.json              # {sid:{name,email,created_at}} (gitignored)
│   ├── chat_log.jsonl          # global log (gitignored, rotate 10MB)
│   └── history/{sid}.jsonl     # per-session (gitignored, rotate 5MB)
├── requirements.txt            # python-aiml==0.9.3 Flask==3.1.3 Flask-Cors==5.0.1
├── .gitignore / .gitattributes # eol lf, ignore __pycache__/*.pdf/data logs
├── LICENSE (MIT 2026)
├── Feature.md                  # roadmap LLM, TTS/STT
└── README.md / PENJELASAN_MENDALAM.md (file ini)
```

**Alur:**
`User (HP/Laptop) → Flask app.py:208 HTML (dot-grid, pill) → POST /login {name} → POST /chat {message,sid} → main.py:169 get_response() → aiml.Kernel:6 PatternMgr:86 match → predicate TOPIK/gaya_bahasa → append_history → JSON response → bubble-row + avatar`

**Git:** `main` branch, 12 commit, remote `https://github.com/tmthyjw23/AIML-AIClass.git`, conventional `feat/fix/refactor`.

---

## 4. Implementasi Mendalam per File

### 4.1 `main.py` — Otak AIML + Boost

* **Kernel global (`main.py:6-13`):** `chatbot = aiml.Kernel(); verbose(False); learn(Ars) then Native` — Native terakhir agar `*` fallback Native tidak di-shadow Ars (PatternMgr prioritas `_ > exact > *`). `main.py:6` dipakai ulang `app.py:6` `from main import chatbot` (hemat load 0.27s).
* **Helper `_load_topics()` (`main.py:19`):** parse `Ars_Optimized.aiml` regex `<pattern>MASTER (.*?)</pattern>` → 150 topics.
* **KEYWORD_MAP + ALIASES (`main.py:28-52`):** `VOID→VOID DALAM`, `ELEMEN→ELEMEN`, `PRINSIP→PRINSIP DESAIN`, dll. Untuk `void` pendek.
* **`get_response()` (`main.py:169`):** 7 langkah — (1) personalisasi nama, (2) SRAI `SIAPA KAMU`, (3) AIML langsung, (4) vague handler, (5) keyword alias word-boundary, (6) typo `difflib cutoff 0.85`, (7) fallback helpful 3 saran. Lihat Bab 9.
* **CLI (`main.py:231`):** `SESSION=_cli` persist `gaya_bahasa`.

### 4.2 `app.py` — Flask Wrapper + Persistence

* **Storage (`app.py:14-27`):** `DATA_DIR=data`, `HISTORY_DIR=data/history`, `_lock=threading.Lock()`, `sanitize_sid()` whitelist `^[a-zA-Z0-9_-]{1,64}$` (P0), `safe_history_path()` `is_relative_to` (P0).
* **Endpoints 9** (`app.py:611-725`):
  | Endpoint | Fungsi |
  |---|---|
  | `GET /` | 21st.dev HTML |
  | `GET /health` | 875 cats + demo + time |
  | `POST /login` | simpan `user_name` predicate + `users.json` + `history` system `LOGIN` |
  | `POST /logout` | log `LOGOUT` |
  | `POST /reset` `context` hapus TOPIK, `session` `_deleteSession`+`_addSession` keep name |
  | `GET /history` | 200 terakhir |
  | `GET/POST /settings` | `gaya_bahasa` |
  | `POST /chat` | `get_response` + log user+bot |
* **Keamanan (`app.py:165-206`):** `MAX_CONTENT_LENGTH 1MB`, `CORS` restrict `127.0.0.1:5000`, `check_rate()` 30/min 429, `X-Content-Type-Options nosniff` `X-Frame DENY`, `html.escape` name, message `[:2000]`, rotate 5MB/10MB.

### 4.3 `NativeConversation.aiml` — 125 cats

* **Greeting persona (`NativeConversation.aiml:9`):** `CORE GREETING SANTAI` set `gaya_bahasa=santai` random 3, `CORE GREETING FORMAL` formal. Routing `WOY/P/BRO/CUY` → santai, `HALO/SELAMAT PAGI` → formal. **Fix deterministik:** `WOY` variant `Fakultas Teknik Arsitektur` dihapus (`main.py` audit found flaky `MAU` after `WOY`), `HALO` variant `Teknik Arsitektur` diganti netral.
* **Validasi/Denial (`NativeConversation.aiml:54/76`):** `OKE/SIP/GASS` `TIDAK/NGGAK` pakai `<condition gaya_bahasa>`.
* **Bridging (`NativeConversation.aiml:97`):** `* KAMPUS *` etc → `CORE BRIDGING` random formal/santai.
* **Smalltalk (`NativeConversation.aiml:152`):** `SIAPA KAMU`, `BISA APA`, `APA KABAR`, `CAPEK/GABUT`, `WKWK/HAHA`, `TERIMA KASIH`, typo `HALOO→HALO` `WOI→WOY`.
* **Context (`NativeConversation.aiml:274`):** `TADI AKU NANYA APA` → `CORE RECALL TOPIK` `<get TOPIK>`, `JELASKAN LEBIH DETAIL` → `CORE DETAIL TOPIK` `<srai>MASTER <get TOPIK/></srai>`, `KALAU YANG * GIMANA`, `<that>* TEKNIK ARSITEKTUR *` untuk `MAU` setelah bridging, `TADI AKU BILANG APA` → `<input index="1"/>`.

### 4.4 `Ars_Optimized.aiml` — 750 cats

Tiap topik 5 pattern:

```xml
<category><pattern>MASTER APA ITU VOID DALAM ARSITEKTUR</pattern>
  <template><think><set name="TOPIK">APA ITU VOID DALAM ARSITEKTUR</set></think>Tentang ... Void adalah ruang kosong...</template>
</category>
<category><pattern>APA ITU VOID DALAM ARSITEKTUR</pattern><template><srai>MASTER APA ITU VOID DALAM ARSITEKTUR</srai></template></category>
<category><pattern>APA ITU VOID DALAM ARSITEKTUR *</pattern><template><srai>MASTER ...</srai></template></category>
<category><pattern>* APA ITU VOID DALAM ARSITEKTUR</pattern><template><srai>MASTER ...</srai></template></category>
<category><pattern>* APA ITU VOID DALAM ARSITEKTUR *</pattern><template><srai>MASTER ...</srai></template></category>
```

150 topik: `VOID, MEZZANINE, BAUHAUS, SKALA, PROPORSI, ERGONOMI, ANTHROPOMETRI, VITARUVIAN TRIAD, FIRMITAS, ZONASI, ORIENTASI, SITE PLAN, FLOOR PLAN, TAMPAK, POTONGAN, ISOMETRI, PERSPEKTIF, AKSONOMETRI, MODERN, POSTMODERN, TROPIS, VERNAKULAR, MINIMALIS, KLASIK, GOTIK, BAROK, BRUTALISME, DEKONSTRUKSIVIZME, PARAMETRIK, BIOKLIMATIK, ORGANIK, ART DECO, LE CORBUSIER, FRANK LLOYD WRIGHT, ZAHA HADID, MIES VAN DER ROHE, dll.`

---

## 5. AIML Deep Dive

**Aturan `python-aiml` (`PatternMgr.py:30`):** `punctuation = r"`~!@#$%^&*()-_=+[{]}\|;:'\",<.>/?"` → `_` adalah punctuation, di-strip jadi spasi saat `match()`. Jadi pattern `MASTER_APA_ITU` (1 token `MASTER_APA_ITU`) vs input `MASTER APA ITU` (3 token) tidak match. **Fix:** ganti `_` → spasi di `<pattern>` & `<srai>` (Native `CORE_GREETING_SANTAI`, Ars `MASTER_APA...`).

**Prioritas:** `_` (0) > exact > `BOT_NAME` (5) > `*` (1) (`PatternMgr.py:294-330`). Fallback `*` harus paling bawah di file (Native `*` di `NativeConversation.aiml:356` last).

**SRAI:** `<srai>CORE GREETING SANTAI</srai>` (`NativeConversation.aiml:22`) untuk sinonim tanpa duplikasi template. Master + alias menghemat 4× duplikasi.

**Predicate:** `<think><set name="TOPIK">` + `<get name="TOPIK"/>` + `<condition name="gaya_bahasa">` untuk persona.

**That/Topic:** `<that>* TEKNIK ARSITEKTUR *</that>` (`NativeConversation.aiml:335`) untuk `MAU` setelah bridging.

---

## 6. Context-Aware & Personalisasi

**TOPIK:** Setiap `MASTER` set `TOPIK`. Recall `TADI AKU NANYA APA` → `<get TOPIK>`. Detail `JELASKAN LEBIH DETAIL` → `<srai>MASTER <get TOPIK/></srai>` + random.

**gaya_bahasa:** `HALO` → formal, `WOY` → santai, disimpan per `session_id` (`chatbot._sessions[session_id]`), dipakai `<condition>`.

**Nama:** `main.py:86` `_handle_name_intent()` regex `nama saya adalah X`/`panggil saya X` → `setPredicate("user_name", Timothy)` + persist ke `data/users.json` + `history` log system `SET name=Timothy`. Recall `siapa nama saya?`/`namaku siapa` → `Nama kamu adalah Timothy...` (cek predicate lalu `users.json` fallback). `siapa nama kamu` → SRAI `SIAPA KAMU`. Topik `ambil.*nama` → `Bisa dong! Aku sudah simpan namamu sebagai Timothy...` (cegah hallucination `DAK BETON`).

**Session:** `main.py:6` global Kernel `threading.RLock` (`Kernel.py:61`), `app.py:14` `_lock` untuk file. `POST /reset` `context` hapus `TOPIK` keep `gaya`, `session` `_deleteSession`/`_addSession` keep `user_name` (fix Valdo→Timothy bug).

---

## 7. Backend Flask

**Flow login:** `enterChat()` (`app.py:481`) `fetch('/login', {name})` → `sanitize_sid` → `save_user` (`html.escape` `[:64]`) → `users.json` → `append_history` system `LOGIN`. Sid `web_xxxx` dari `localStorage` (`app.py:430`), baru jika ganti user (deteksi `prevName !== finalName` → `sid = web_*` baru, isolasi history).

**History:** `append_history()` tulis `history/{sid}.jsonl` + `chat_log.jsonl` (lock, rotate 5MB/10MB). `GET /history` baca 200 terakhir.

**Keamanan:** Sudah di-hardening (Bab 10).

---

## 8. Frontend

**Inspirasi:** `https://21st.dev/@aghasisahakyan1/components/sign-in-flow-1` — dark `bg-dots` `radial-gradient 22px` `mask ellipse` `opacity .55` + `bg-glow` 2 radial, pill navbar `rgba(18,18,18,.72)` `blur 16px` `radius 9999px` `shadow`.

**Login:** `Welcome Developer` + `Masukkan nama untuk memulai` + 1 pill `Nama Anda` `maxlength 32` + `→` (Enter). Simpan `localStorage ars_name/ars_logged`. Google & email pill dihapus (sesuai revisi).

**Navbar repurpose:** Guest `875 AIML • Context-aware` hint, Logged `user-pill` avatar initial + `Reset Konteks` | `Reset Sesi` danger | `Pengaturan` (modal) | `Logout`, hamburger `≤740px` toggle `.mobile-menu` dropdown.

**Chat:** `chat-shell` glass `rgba(16,16,16,.72)` `blur 14px` `radius 24px` `height min(56vh,520px)` / `calc(100dvh -220px)` mobile, `bubble-row` + `avatar` (user initial / bot `◈`) + `bubble` + `bubble-meta` `Nama • 11:27`, `typing` bounce 3 dots, `historyCount`.

**Responsive:** Breakpoints `480/640/740/820/1024`, `clamp()` font, `100dvh`/`100svh` + `--vh` JS, `touch-action:manipulation`, `pill input 16px` anti-iOS zoom, `nav-links` hide ≤740, `bubble-row 92%` HP.

---

## 9. Boost Experience — Anti-Kaku & Anti-Halusinasi

**Masalah transcript awal (6/14 fallback):**
`apa itu viod` (typo), `apa itu void`/`void`/`elemen arsitektur?`/`prinsip arsitektur` (pendek), `siapa nama kamu` (variasi), `siapa nama saya?` + `nama saya adalah Timothy` double fallback, `apakah kamu tidak bisa ambil dari nama?` → `DAK BETON` (substring `DAK` di `TIDAK`).

**Solusi `main.py:54-232`:**
* **Typo:** `_correct_typos()` vocab topics+keywords+native (`OKE/GAS/WOY`), `len<=3` keep, `difflib cutoff 0.85` → `VIOD→VOID` + note dinamis `aku koreksi 'viod' jadi 'void'`.
* **Short alias:** `KEYWORD_MAP` word-boundary `\bKW\b` (`main.py:80`) → `VOID→VOID DALAM`, `ELEMEN→ELEMEN`, `PRINSIP→PRINSIP DESAIN` → `void`/`elemen arsitektur?` langsung `Tentang ...`.
* **Fallback detection:** `FALLBACK_MARKERS` tambah `waduh/ketinggian/hmm` + `di luar kemampuan` agar `Waduh...` terdeteksi fallback → trigger alias (fix `kalau void>`).
* **Vague handler:** `kita akan bahas|yang kamu bilang` → recall `TOPIK` atau `Boleh, kita mau bahas apa?` (tidak hallu `BAUHAUS`).
* **Validation:** `\b(oke|gas|sip)\b` → `SRAI OKE` → `Sip, mantap...` (fix `oke, gas`).
* **Helpful fallback:** `difflib` 3 saran `Mungkin maksud kamu: 'apa itu void...'?` hanya untuk kata ≥4 huruf (hindari `wah→wall`).

**Hasil:** Transcript 14/14 OK, hallucination 0.

---

## 10. Audit & Verifikasi (Sub-Agent 4 Domain)

Dispatch `dispatching-parallel-agents` + `verification-before-completion`:

| Domain | Temuan | Status |
|---|---|---|
| **AIML** | 875 cats, underscore 0, fallback last, MASTER no recursion, 10 topics OK, session isolasi, `WOY` deterministik fix | 100/100 PASS |
| **Backend** | `/health` 875, `/login` 200/400, traversal `../evil` 400 (was P0 arbitrary write to `outside.jsonl`), CORS `127.0.0.1:5000` (was `*`), rate 30/min 429, headers `nosniff/DENY`, XSS `textContent` safe | 2 FAIL → fixed (reset `gaya` side-effect) |
| **Frontend** | `GET /` 200, 8 fetch URLs match `url_map`, `bg-dots`/`nav-pill`/`Welcome`/`Nama Anda`/`Reset` PASS, `textContent` XSS safe, `@media 740` PASS | 0 FAIL |
| **Git** | `.gitignore` `data/* !.gitkeep`, no secrets, no >5MB tracked (`Ars 140KB`), `log 5e1a575→962cf4b` conventional, `main` synced `58dda65` → `446f030` | 1 FAIL → cleaned `users.json {}` `history only .gitkeep` |

**Fixes:** `app.py:31` `sanitize_sid`, `safe_history_path`, `MAX_CONTENT_LENGTH`, `check_rate`, `html.escape`, `FALLBACK` + `NativeConversation.aiml:16` `HALO` deterministik.

---

## 11. Cara Menjalankan & Demo

```powershell
Set-Location -LiteralPath "D:\collage\AI\ClassPractical\Project"
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5000
# CLI: python main.py
```

**Demo 5 menit:**
1. Login `Timothy` → Halo personal
2. `halo` → formal, `woi` → santai (beda persona)
3. Typo `apa itu viod` → koreksi void + hint
4. Short `void` / `elemen arsitektur?` → langsung jawab (boost)
5. Context `apa itu bauhaus` → `jelaskan lebih detail` → `tadi aku nanya apa` → recall TOPIK
6. Personal `siapa nama saya?` → Timothy, `apakah kamu tidak bisa ambil dari nama?` → Bisa dong!
7. Navbar `Reset Konteks` vs `Reset Sesi` demo, `Pengaturan` ganti santai, `Logout` → login `Valdo` → bubble terpisah (per-user isolation)

---

## 12. Kendala Kritis & Solusi

| Kendala | Akar | Solusi |
|---|---|---|
| `HEI` tidak match `HEI` → fallback | `model.aiml` pattern `HEI` tapi `main.py` learn `model.aiml` hilang | Ganti ke 2 file + `learn` keduanya |
| `ALL HALO/WOY` fallback + `maximum recursion` | `pattern MASTER_APA...` underscore → `PatternMgr.py:30` strip `_` jadi spasi, SRAI `MASTER_APA` tidak match | Ganti `_`→spasi di `<pattern>` & `<srai>` |
| `outside.jsonl` arbitrary write | `session_id` unsanitized `HISTORY_DIR / f"{sid}.jsonl"` | Whitelist `^[a-zA-Z0-9_-]{1,64}$` → 400 |
| `Waduh...` tidak terdeteksi fallback | `FALLBACK_MARKERS` tidak ada `waduh` | Tambah `waduh/ketinggian/hmm` |
| `oke, gas` → `oke as` | `GAS` tidak di vocab, `len<=2` cut, `GAS→AS` | Vocab native + `len<=3` + handler `oke|gas` → SRAI OKE |
| `kita akan bahas...` → `BAUHAUS` | Substring alias + typo hallu | Word-boundary + vague handler |
| `namaku siapa` → `belum tahu` setelah set | Predicate per session, tidak persist `users.json` | `setPredicate` + `users.json` write + fallback load |

---

## 13. Kesimpulan & Nilai Tambah

Tugas 150 kategori terpenuhi **dan dilampaui** tanpa mengorbankan kemurnian AIML (tetap rule-based, bukan LLM). Nilai tambah: context-aware, typo tolerance, login persist, hardening, UI 21st.dev responsive — semua **AIML murni + Python wrapper tipis**, bukan LLM, sehingga tetap “chatbot sederhana” tapi rasa industri.

**Saran:** Tambah `RAG` (`ChromaDB` + `sentence-transformers` seperti Demo #4 Lecture) untuk upload file jadi AIML otomatis (sudah di `Feature.md:5`), TTS/STT `gTTS` + `SpeechRecognition` + wake word.

---

## 14. Lampiran

**Struktur file lengkap:** `git ls-files` 12 tracked, `data` gitignored keep `.gitkeep`.

**Perintah audit:**
```bash
python -c "import aiml; k=aiml.Kernel(); k.learn('Ars_Optimized.aiml'); k.learn('NativeConversation.aiml'); print(k.numCategories())" # 875
curl -X POST http://127.0.0.1:5000/login -H "Content-Type: application/json" -d '{"session_id":"web_test","name":"Budi"}'
curl -X POST http://127.0.0.1:5000/chat -d '{"session_id":"web_test","message":"apa itu void"}'
```

**Referensi:** Lecture6 PDF, `python-aiml 0.9.3` `PatternMgr.py`, `Kernel.py` `Rlock`, 21st.dev `sign-in-flow-1`.

**Lisensi:** MIT 2026 Univ Klabat.

> **Catatan demo:** File ini `PENJELASAN_MENDALAM.md` — untuk presentasi, lihat `SCRIPT_DEMO.md` (dibuat setelah file ini fix).


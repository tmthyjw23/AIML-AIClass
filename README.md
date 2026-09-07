# Arsitek Chatbot — AIML + Context-Aware

Chatbot AIML berbasis `python-aiml` untuk layanan informasi **Fakultas Teknik Arsitektur**. Terdiri dari 2 knowledge base terpisah + fitur context-aware, login persistent, history log, dan UI dark pill ala 21st.dev.

> Project: `Lecture6 - Class Practical #1 [AI-Powered AIML Chatbot]` — Universitas Klabat

---

## Struktur Project

```
Project/
├── main.py                     # CLI + Kernel loader + get_response() untuk web
├── app.py                      # Flask web server + UI 21st.dev (port 5000) + API login/history
├── NativeConversation.aiml     # Sapaan, validasi, bridging, smalltalk, CONTEXT (125+ cats)
├── Ars_Optimized.aiml          # Knowledge arsitektur (750 cats) — TOPIK-aware
├── data/
│   ├── users.json              # (gitignored) mapping session_id -> {name,email}
│   ├── chat_log.jsonl          # (gitignored) global log
│   └── history/{sid}.jsonl     # (gitignored) per-session history
├── requirements.txt
├── LICENSE (MIT)
├── Feature.md                  # Roadmap fitur (LLM, TTS/STT, callword)
└── README.md
```

* `Ars_Optimized.aiml` — 150+ topik arsitektur (`APA ITU ARSITEKTUR`, `BAUHAUS`, `FRANK LLOYD WRIGHT`, `VOID`, `MEZZANINE`, `BETON BERTULANG`, dll). Master pattern `MASTER <TOPIK>` menyimpan predicate `TOPIK`.
* `NativeConversation.aiml` — Persona santai/formal (`gaya_bahasa`), bridging, smalltalk, dan **context recall**.

---

## Prasyarat

* Python 3.9+ (tested 3.11.9)
* `pip install -r requirements.txt` → `python-aiml Flask Flask-Cors`

```bash
pip install -r requirements.txt
# atau minimal
pip install python-aiml flask flask-cors
```

---

## Cara Pakai

### 1. CLI (debug cepat)

```bash
python main.py
# Bot ready | categories=875
# Kamu: HALO
# Bot: Halo, selamat datang...
# Kamu: apa itu bauhaus
# Bot: Tentang APA ITU BAUHAUS: Bauhaus adalah aliran ...
# Kamu: jelaskan lebih detail  # context via TOPIK
# Bot: Tentang APA ITU BAUHAUS: ... (ambil <get name="TOPIK">)
```

`main.py:18` `get_response(pesan, session_id)` menyimpan `gaya_bahasa` & `TOPIK` per `session_id`.

### 2. Web (Flask) — UI 21st.dev Sign-In-Flow-1

```bash
python app.py
# [app] categories=875 http://127.0.0.1:5000  data dir: .../data
```

Buka `http://127.0.0.1:5000`:

* **Auth view** (Welcome Developer): pill `G Sign in with Google` (mock) + `Nama Anda` + `info@gmail.com` + arrow → . Nama disimpan ke `data/users.json` & predicate `user_name`, history log ke `data/history/{sid}.jsonl` dan `data/chat_log.jsonl`. Email opsional, nama auto jadi `Tamu` jika kosong.
* **Navbar** (pill dark, dot-grid bg): 
  * Guest: `Manifesto / Careers / Discover` + `LogIn / Signup`
  * Logged-in: avatar + nama + sid + `Reset Konteks` | `Reset Sesi` | `Pengaturan` | `Logout`
* **Chat view:** glass `chat-log`, bubble user putih / bot glass, input pill. Coba `apa itu bauhaus` → `jelaskan lebih detail` → `tadi aku nanya apa` (context).

**API:**

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/` | - | HTML UI |
| GET | `/health` | - | `{status, categories, demo}` |
| POST | `/login` | `{session_id, name, email}` | `{ok, user}` — simpan `user_name` predicate & `users.json` |
| POST | `/logout` | `{session_id}` | `{ok}` — log event, hapus `localStorage` flag |
| POST | `/reset` | `{session_id, mode: context|session}` | `{ok, predicate}` — `context` hapus TOPIK, `session` hapus semua + re-add |
| GET | `/history?session_id=xxx` | - | `{history: [{ts,role,message,name}], count}` |
| GET/POST | `/settings?session_id` / `{gaya_bahasa}` | - | `{gaya_bahasa, TOPIK, user}` |
| POST | `/chat` | `{message, session_id}` | `{response, predicate, session_id}` — log user+bot |

Contoh:

```bash
curl -X POST http://127.0.0.1:5000/login -H "Content-Type: application/json" -d '{"session_id":"web_abc","name":"Budi","email":"budi@gmail.com"}'
curl -X POST http://127.0.0.1:5000/chat -H "Content-Type: application/json" -d '{"session_id":"web_abc","message":"apa itu void dalam arsitektur"}'
curl http://127.0.0.1:5000/history?session_id=web_abc
curl -X POST http://127.0.0.1:5000/reset -H "Content-Type: application/json" -d '{"session_id":"web_abc","mode":"context"}'
```

---

## Model AIML

### Pattern rules (`python-aiml`)

* Pattern **UPPERCASE** tanpa tanda baca. `_` dan `*` hanya token terpisah. Jangan `MASTER_APA_ITU` — harus `MASTER APA ITU` (fixed `PatternMgr.py:30` punctuation strip).
* Prioritas: `_` > exact > `BOT_NAME` > `*`. Fallback `*` paling bawah.

### NativeConversation.aiml (125 cats)

* **Greeting persona:** `WOY/P/BRO/CUY` -> santai, `HALO/SELAMAT PAGI` -> formal (random 3 variasi).
* **Validasi/Denial:** `OKE/SIP` & `TIDAK/NGGAK`.
* **Bridging:** `* KAMPUS *`, `* KULIAH *`, `JURUSAN`, `FAKULTAS`, `DOSEN`.
* **Smalltalk:** `SIAPA KAMU`, `BISA APA`, `HELP`, `CAPE/GABUT/WKWK/MAKASIH`, typo `HALOO->HALO`, `WOI->WOY`.
* **Context:** `TADI AKU NANYA APA`, `JELASKAN LEBIH DETAIL`, `CONTOHNYA`, `KALAU YANG * GIMANA`, `YANG TADI`, plus `<that>` untuk `MAU` setelah bridging (`* ARSITEKTUR *`) dan `<input index="2">` untuk history.

### Ars_Optimized.aiml (750 cats)

```xml
<category><pattern>MASTER APA ITU ARSITEKTUR</pattern>
  <template><think><set name="TOPIK">APA ITU ARSITEKTUR</set></think>Tentang ...</template>
</category>
<category><pattern>APA ITU ARSITEKTUR</pattern><template><srai>MASTER APA ITU ARSITEKTUR</srai></template></category>
```

Routing `* TOPIK *` tersedia, typo-tolerant via `srai`.

---

## Fitur Login & History

* **Login:** `POST /login` → `data/users.json` + `chatbot.setPredicate("user_name", sid)` + `append_history(..., role=system, "LOGIN...")`. Frontend `localStorage` `ars_sid`, `ars_name`, `ars_email`, `ars_logged` → navbar pill avatar + nama. Auto-login jika `ars_logged`.
* **History log:** Setiap `POST /chat` append 2 baris (user+bot) ke `data/history/{sid}.jsonl` & `data/chat_log.jsonl` (thread-locked). `GET /history` load 200 terakhir untuk UI. Data di-`.gitignore` (keep `.gitkeep` saja).
* **Navbar repurpose:**
  * `Reset Konteks` → `POST /reset {mode:context}` hapus `TOPIK` (predicate), keep `gaya_bahasa`/`user_name`.
  * `Reset Sesi` → `POST /reset {mode:session}` `_deleteSession` + re-add, demo `HALO`.
  * `Pengaturan` → modal (nama, email, `gaya_bahasa` santai/formal → `POST /settings`), session ID read-only.
  * `Logout` → `POST /logout` + `localStorage.removeItem('ars_logged')` → balik ke authView (history file tetap untuk audit).

---

## Troubleshooting

* `WARNING: No match found` — pattern pakai underscore/lowercase; harus spasi & uppercase.
* `maximum recursion depth exceeded` — SRAI loop `A->B->A`; cek `MASTER` tidak self-srai.
* `ModuleNotFoundError: main` — `app.py:3` `sys.path.insert(0, ...)`, jalankan dari `Project`.
* Port 5000 terpakai — `app.run(port=5001)`.

---

## Roadmap (Feature.md)

* [x] AIML native + arsitektur terpisah
* [x] Context-aware (TOPIK + that)
* [x] Login (nama) + history log + navbar Reset/Logout/Settings
* [x] UI 21st.dev sign-in-flow-1 (dark dot-grid, pill nav)
* [ ] LLM generate AIML dari file upload (RAG)
* [ ] TTS (`gTTS`) & STT (`SpeechRecognition`) + wake word `callword`
* [ ] History pagination & admin view

---

## Referensi

* Lecture6 PDF (50 hal) — `python-aiml 0.9.3`, `PatternMgr.py` `puncStripRE`
* 21st.dev — `sign-in-flow-1` by Erik (Next, Three, framer-motion)
* Mitsuku (AIML, 5× Loebner winner)

## Lisensi

MIT — 2026 Timothy Jordy Weley — Universitas Klabat.

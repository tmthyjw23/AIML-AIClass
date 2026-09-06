# Arsitek Chatbot — AIML + Context-Aware

Chatbot AIML berbasis `python-aiml` untuk layanan informasi **Fakultas Teknik Arsitektur**. Terdiri dari 2 knowledge base terpisah + fitur context-aware agar percakapan tidak kaku dan tetap nyambung.

> Project: `Lecture6 - Class Practical #1 [AI-Powered AIML Chatbot]` — Universitas Klabat

---

## Struktur Project

```
Project/
├── main.py                     # CLI + Kernel loader + get_response() untuk web
├── app.py                      # Flask web server + UI debug (port 5000)
├── NativeConversation.aiml     # Sapaan, validasi, bridging, smalltalk, CONTEXT (130+ categories)
├── Ars_Optimized.aiml          # Knowledge arsitektur (750 categories) — TOPIK-aware
├── Feature.md                  # Roadmap fitur (LLM, TTS/STT, callword)
└── README.md                   # Dokumentasi ini
```

* `Ars_Optimized.aiml` — 150+ topik arsitektur (`APA ITU ARSITEKTUR`, `BAUHAUS`, `FRANK LLOYD WRIGHT`, `VOID`, `MEZZANINE`, `BETON BERTULANG`, dll). Tiap topik pakai master pattern `MASTER <TOPIK>` yang menyimpan predicate `TOPIK` untuk context.
* `NativeConversation.aiml` — Persona santai/formal (`gaya_bahasa`), bridging ke arsitektur, smalltalk, emotion, help, dan **context recall**.

---

## Prasyarat

* Python 3.9+ (tested 3.11.9)
* `pip install python-aiml flask flask-cors`  
  Optional untuk roadmap: `SpeechRecognition gTTS pygame openai chromadb sentence-transformers`

```bash
pip install python-aiml flask flask-cors
```

---

## Cara Pakai

### 1. CLI (debug cepat)

```bash
python main.py
# Bot ready | categories=792
# Kamu: HALO
# Bot: Halo, selamat datang...
# Kamu: apa itu bauhaus
# Bot: Tentang APA ITU BAUHAUS: Bauhaus adalah aliran ...
# Kamu: jelaskan lebih detail
# Bot: Tentang APA ITU BAUHAUS: ... (context aware via TOPIK)
# Kamu: keluar
```

`main.py:18` `get_response(pesan, session_id)` menyimpan `gaya_bahasa` & `TOPIK` per `session_id` (persisten selama CLI).

### 2. Web (Flask)

```bash
python app.py
# [app] categories=~880 http://127.0.0.1:5000
```

Buka `http://127.0.0.1:5000` — UI minimal untuk test percakapan. Session ID random per tab, sehingga `HALO -> OKE` tetap `formal`.

**API:**

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/health` | - | `{status, categories, demo}` |
| POST | `/chat` | `{message: "...", session_id: "user123"}` | `{response, session_id, predicate: {gaya_bahasa, TOPIK}}` |
| GET | `/` | - | HTML debug UI |

Contoh `curl`:

```bash
curl -X POST http://127.0.0.1:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"apa itu void dalam arsitektur","session_id":"test1"}'
```

**Catatan:** `main.py:6` Kernel global dipakai ulang di `app.py:6`, jadi tidak perlu load ulang. Thread-safe (`Kernel.py:61` RLock).

---

## Model AIML

### Pattern rules (`python-aiml`)

* Pattern **UPPERCASE** tanpa tanda baca. `_` dan `*` hanya sebagai token terpisah (wildcard). Jangan gunakan `MASTER_APA_ITU` — harus `MASTER APA ITU` (sudah di-fix).
* Matching prioritas: `_` > exact > `BOT_NAME` > `*`. Fallback `*` harus paling bawah di file.

### NativeConversation.aiml

* **Greeting persona:** `WOY/P/BRO/CUY` -> `CORE GREETING SANTAI` (set `gaya_bahasa=santai`), `HALO/SELAMAT PAGI` -> `formal`. Semua sapaan random 3 variasi.
* **Validasi & Denial:** `OKE/SIP/IO/GASS` & `TIDAK/NGGAK/NDA/SKIP` merespon sesuai persona.
* **Bridging:** `* KAMPUS *`, `* KULIAH *`, `JURUSAN`, `FAKULTAS`, `DOSEN`, `TUGAS` mengarahkan ke topik arsitektur.
* **Smalltalk (baru):** `SIAPA KAMU`, `KAMU SIAPA`, `BISA APA`, `HELP`, `CAPE/GABUT/BOSAN/WKWK/HAHA` — tidak kaku, random.
* **Context (baru):** lihat bagian bawah.

### Ars_Optimized.aiml

Tiap blok:

```xml
<category><pattern>MASTER APA ITU ARSITEKTUR</pattern>
  <template><think><set name="TOPIK">APA ITU ARSITEKTUR</set></think>Tentang ...</template>
</category>
<category><pattern>APA ITU ARSITEKTUR</pattern><template><srai>MASTER APA ITU ARSITEKTUR</srai></template></category>
<category><pattern>* APA ITU ARSITEKTUR *</pattern><template><srai>MASTER APA ITU ARSITEKTUR</srai></template></category>
```

Semua routing `* TOPIK *` dan `TOPIK *` sudah ada, sehingga `tanya dong apa itu bauhaus ya` tetap match.

---

## Fitur Context

Bot sebelumnya tidak ingat chat terakhir karena AIML stateless per `respond()` call. Sekarang:

### 1. Predicate `TOPIK` & `gaya_bahasa` per session

`Ars_Optimized.aiml` menyimpan `TOPIK` tiap jawaban arsitektur. `NativeConversation.aiml` menyimpan `gaya_bahasa`. Keduanya disimpan di `chatbot._sessions[session_id]` dan dipakai di kondisi `<condition name="TOPIK">`.

### 2. Recall topik terakhir

```
User: apa itu bauhaus
Bot: Tentang APA ITU BAUHAUS: Bauhaus adalah aliran ...
User: jelaskan lebih detail
Bot: Tentang APA ITU BAUHAUS: Bauhaus adalah aliran ... (ambil <get name="TOPIK">)

User: tadi aku nanya apa
Bot: Kamu tadi nanya soal APA ITU BAUHAUS.
User: apa topik terakhir
Bot: Topik terakhir kita adalah APA ITU BAUHAUS.
```

Implementasi di `NativeConversation.aiml`:

* `JELASKAN LEBIH DETAIL`, `CONTOHNYA`, `KELEBIHANNYA APA`, `KALAU YANG * GIMANA`, `YANG TADI`, `LANJUT` — semua pakai `<get name="TOPIK">` + random follow-up.
* `TADI AKU NANYA APA`, `KAMU INGAT GA`, `TOPIK TERAKHIR` — recall langsung.

### 3. `<that>` — konteks jawaban terakhir

AIML `that` = kalimat respon bot terakhir. Memungkinkan follow-up natural:

```
Bot: Ngomong-ngomong, lu udah tau belum info seputar Teknik Arsitektur?
User: mau
Bot: Asik, tanyain aja soal arsitektur apa aja.   (matched <that>* MAU NANYA APA LAGI</that>)
```

Ditambahkan kategori `<pattern>MAU</pattern><that>* MAU NANYA *</that>` dan variasi `IYA MAU`, `BOLEH`, `LANJUT DONK`.

### 4. History via `<input>` (web)

`app.py:81` mengembalikan predicate, dan `main.py:22` fallback tetap pakai `chatbot.getPredicate("_inputHistory")` internal. Kamu bisa kembangkan `/history` endpoint untuk menampilkan `getPredicate("_inputHistory", sid)` jika butuh.

**Limitasi:** AIML context masih berbasis pattern matching, bukan LLM. Untuk pertanyaan di luar 750 topik (misal typo `arsitektur` vs `arsitekstur`), fallback `*` akan menyarankan tanya seputar arsitektur.

---

## Troubleshooting

* `WARNING: No match found` — cek pattern pakai underscore atau lowercase; harus spasi & uppercase.
* `maximum recursion depth exceeded` — SRAI loop (misal `A -> B -> A`). Pastikan `MASTER` tidak srai ke diri sendiri.
* `ModuleNotFoundError: main` saat `python app.py` — sudah di-fix `app.py:3` `sys.path.insert(0, ...)`. Jalankan dari folder `Project` atau `python -m app`.
* Web tidak reload AIML setelah edit — restart Flask (debug=True auto-reload).

---

## Roadmap (Feature.md)

* [x] AIML native + arsitektur terpisah
* [x] Context-aware (TOPIK + that)
* [ ] LLM generate AIML dari file upload (RAG)
* [ ] TTS (`gTTS`) & STT (`SpeechRecognition`) + wake word `callword`
* [ ] UI web full (bukan debug) + history chat persistent (DB)

---

## Referensi

* Lecture6 PDF (50 hal) — `python-aiml 0.9.3`, `PatternMgr.py` `puncStripRE`
* Mitsuku (AIML, 5× Loebner winner) — contoh AIML kompleks

## Lisensi

Internal — Class Practical, Universitas Klabat.

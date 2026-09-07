# SCRIPT DEMO — ArsitekBot (5-7 Menit)

> **Gunakan setelah `PENJELASAN_MENDALAM.md` fix.**  
> **Tujuan:** Meyakinkan dosen bahwa 150 kategori terpenuhi (justru 875) + demo live lancar + boost tidak kaku.  
> **Setup sebelum kelas:** `Set-Location "D:\collage\AI\ClassPractical\Project"; pip install -r requirements.txt; python app.py` → `http://127.0.0.1:5000` siap di tab 1, `main.py` CLI di tab 2, `PENJELASAN_MENDALAM.md` open, `git log --oneline` siap.

---

## 0. Checklist 2 Menit Sebelum Maju

- [ ] `python app.py` jalan, `875 categories` di terminal
- [ ] Browser `http://127.0.0.1:5000` tampil `Welcome Developer` + `Nama Anda` pill (bukan `LogIn/Signup` lagi)
- [ ] `data/users.json` kosong `{}` (biar demo fresh)
- [ ] HP juga open `http://<ip>:5000` untuk bukti responsive (atau DevTools `Ctrl+Shift+M`)
- [ ] Slide/PDF Lecture6 siap di background (hal Demo #1)

**Jika offline:** fallback `python main.py` CLI — ketik `halo` → `apa itu void` tetap jalan.

---

## 1. Opening (30 detik)

> "Selamat pagi, saya Timothy. Tugas Class Practical #1 diminta chatbot AIML sederhana 150 kategori. Saya buat **ArsitekBot — 875 categories** (Native 125 + Ars 750) tetap AIML murni, bukan LLM, tapi context-aware + login + responsive. Repo ada di `github.com/tmthyjw23/AIML-AIClass`, semua commit ada. Saya akan jelaskan 1 menit lalu live demo."

*Gesture:* tunjuk `PENJELASAN_MENDALAM.md:2` (150 vs 875) dan `git log` 12 commit.

---

## 2. Penjelasan Kilat (90 detik) — Jangan Baca Full, Poin Saja

> "Awalnya `model.aiml` cuma 2 kategori `HEI` — selalu fallback. Saya pecah jadi 2 file: `NativeConversation.aiml` untuk sapaan & smalltalk, `Ars_Optimized.aiml` 150 topik ×5 pattern =750. Tiap topik pakai `MASTER` + `SRAI` biar `apa itu void`, `void`, `elemen arsitektur?` semua match tanpa duplikasi template."

> "Bug kritis yang saya temukan: pattern `MASTER_APA_ITU` pakai underscore, tapi `PatternMgr.py:30` strip `_` jadi spasi — tidak pernah match, `maximum recursion` — saya fix ganti spasi."

> "Boost agar tidak kaku: typo `viod→void` via `difflib`, short alias `VOID→VOID DALAM`, fallback word-boundary (jadi `TIDAK` tidak trigger `DAK`), personalisasi `nama saya adalah Timothy` simpan ke `predicate` + `data/users.json`, dan fallback helpful saran 3 topik."

*Gesture:* tunjuk `main.py:27` `KEYWORD_MAP`, `main.py:86` `_handle_name_intent`, `app.py:31` `sanitize_sid`.

---

## 3. Live Demo — Skenario Transcript (3 menit) — KETIK PERSIS INI

**Login dulu:** Ketik `Timothy` di `Nama Anda` → Enter.

> "Halo, Timothy! Selamat datang..." (personal, bukan generic)

**Skenario 1 — Typo & Pendek:**
Ketik berurutan, biarkan audiens lihat bubble:
1. `halo` → `Selamat datang! Ada yang bisa saya bantu hari ini?` (formal)
2. `apa itu viod` → `Tentang VOID DALAM... (aku koreksi 'viod' jadi 'void' ya)` (typo)
3. `void` → `Tentang VOID DALAM...` (pendek, tanpa `apa itu ... dalam`)
4. `elemen arsitektur?` → `Tentang ELEMEN...` (tanpa `apa saja`, + `?`)
5. `prinsip arsitektur` → `Tentang PRINSIP DESAIN...` (tanpa `apa itu`)

*Narasi:* "Tanpa boost, 3 ini tadi fallback `Maaf... di luar kemampuan`."

**Skenario 2 — Context:**
6. `apa itu bauhaus` → `Tentang BAUHAUS...`
7. `jelaskan lebih detail` → `Maksud kamu 'apa itu bauhaus' yang tadi? Tentang BAUHAUS...` (TOPIK)
8. `tadi aku nanya apa` → `Kamu tadi nanya soal BAUHAUS`

**Skenario 3 — Personal & Hallucination Fix:**
9. `siapa nama kamu` → `Saya adalah ArsitekBot...`
10. `siapa nama saya?` → `Nama kamu adalah Timothy...` (ambil dari login)
11. `apakah kamu tidak bisa ambil dari nama yang saya input?` → `Bisa dong! Aku sudah simpan namamu sebagai Timothy...` (dulu hallu `DAK BETON` karena substring `DAK` di `TIDAK`, kini word-boundary)
12. `kita akan bahas tentang yang kamu bilang` → `Maksud kamu 'bauhaus' yang tadi?` atau `Boleh, kita mau bahas apa?` (vague handler, tidak `BAUHAUS` ngarang)

**Skenario 4 — Responsive & Session:**
*Putar HP* atau `Ctrl+Shift+M` → tunjuk navbar pill tetap rapi, hamburger muncul, `Reset Konteks`/`Reset Sesi`/`Pengaturan` di dropdown, `Logout` → login `Valdo` → bubble beda (isolasi `web_7s8ht3` vs `web_xxxx`).

---

## 4. Penutup & Nilai Tambah (30 detik)

> "Jadi 150 kategori terpenuhi, saya buat 875 biar coverage natural. Semua tetap AIML, tidak pakai LLM di tugas ini (LLM ada di roadmap `Feature.md:5` untuk upload file jadi AIML). Keamanan sudah hardening: `sanitize_sid`, rate limit, CORS. Terima kasih, saya siap tanya-jawab."

**Antisipasi Q&A:**

*Q: Kenapa 875 bukan 150?*  
A: "150×5 varian biar `apa itu void`, `void`, `* void *` semua match — tetap 150 topik, cuma pattern diperbanyak, dosen minta 150 kategori minimal, ini 5.8×."

*Q: Kenapa tidak pakai LLM saja?*  
A: "Tugas minta AIML sederhana, LLM saya taruh roadmap `Feature.md:5` (Demo #4 RAG) — biar tetap murni, tapi boost typo & context via Python tipis."

*Q: Kok `TIDAK` jadi `DAK BETON` dulu?*  
A: "Keyword alias pakai `in` substring — `DAK` ada di `TIDAK` — saya ganti `\bDAK\b` word-boundary."

*Q: Data `users.json` aman?*  
A: "Di `.gitignore:50` `data/* !.gitkeep`, tidak ke-push, `html.escape` + `MAX_CONTENT_LENGTH 1MB` + `sanitize_sid`."

---

## 5. Cadangan Jika Demo Gagal

* **WiFi mati:** `python main.py` CLI ketik `apa itu void` → sama.
* **Port 5000 taken:** `app.run(port=5001)` atau `py -m http.server` fallback.
* **Typo tidak koreksi:** tunjuk `main.py:65` `_correct_typos` cutoff 0.85.

---

## 6. Cue Waktu

* 0:00-0:30 Opening
* 0:30-2:00 Penjelasan kilat
* 2:00-5:00 Live demo 12 input
* 5:00-5:30 Penutup
* 5:30-7:00 Q&A

**Akhir:** `git log --oneline` tunjuk 12 commit, `PENJELASAN_MENDALAM.md` siap untuk laporan PDF.

> **Catatan:** Script ini dibuat setelah `PENJELASAN_MENDALAM.md` fix — sinkron.


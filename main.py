from pathlib import Path
import re
import difflib
import html

import aiml

# --- Kernel tetap global agar bisa di-import dari web wrapper (app.py) ---
chatbot = aiml.Kernel()
# matikan verbose untuk CLI bersih (aktifkan True jika debug)
chatbot.verbose(False)

BASE = Path(__file__).parent
# Load order: domain dulu, NativeConversation terakhir agar fallback "*" paling akhir
chatbot.learn(str(BASE / "Ars_Optimized.aiml"))
chatbot.learn(str(BASE / "NativeConversation.aiml"))

# --- Helper: load topics & keyword alias for boost ---
def _load_topics():
    try:
        txt = (BASE / "Ars_Optimized.aiml").read_text(encoding="utf-8")
        masters = re.findall(r"<pattern>MASTER (.*?)</pattern>", txt)
        return masters
    except:
        return []

KNOWN_TOPICS = _load_topics()  # 150 topics
# keyword -> full topic (first occurrence)
KEYWORD_MAP = {}
for _t in KNOWN_TOPICS:
    for w in _t.split():
        if w in {"APA","ITU","SAJA","SIAPA","DALAM","YANG","DAN","DI"}:
            continue
        if w not in KEYWORD_MAP:
            KEYWORD_MAP[w] = _t
# tambahan alias pendek yang sering dipakai user
ALIASES = {
    "VOID": "APA ITU VOID DALAM ARSITEKTUR",
    "VIOD": "APA ITU VOID DALAM ARSITEKTUR",
    "VVOID": "APA ITU VOID DALAM ARSITEKTUR",
    "ELEMEN": "APA SAJA ELEMEN ARSITEKTUR",
    "ELEMEN ARSITEKTUR": "APA SAJA ELEMEN ARSITEKTUR",
    "PRINSIP": "APA ITU PRINSIP DESAIN ARSITEKTUR",
    "PRINSIP ARSITEKTUR": "APA ITU PRINSIP DESAIN ARSITEKTUR",
    "PRINSIP DESAIN": "APA ITU PRINSIP DESAIN ARSITEKTUR",
    "TEKNIK ARSITEKTUR": "APA ITU TEKNIK ARSITEKTUR",
    "FUNGSI": "APA FUNGSI ARSITEKTUR",
    "SKALA": "APA ITU SKALA ARSITEKTUR",
    "PROPORSI": "APA ITU PROPORSI DALAM ARSITEKTUR",
}
for k,v in ALIASES.items():
    KEYWORD_MAP[k] = v

FALLBACK_MARKERS = ["maaf", "sorry", "kurang", "tidak menemukan", "tidak mengerti", "tidak paham", "di luar kemampuan", "sepertinya di luar", "tidak nangkap", "kurang paham", "kurang nangkap", "waduh", "ketinggian", "hmm"]

def _is_fallback(resp: str) -> bool:
    if not resp:
        return True
    low = resp.lower()
    return any(m in low for m in FALLBACK_MARKERS)

def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text).strip()

def _correct_typos(text: str) -> str:
    vocab = set()
    for t in KNOWN_TOPICS:
        vocab.update(t.split())
    vocab.update(KEYWORD_MAP.keys())
    # tambah vocab native agar OKE/GAS/WOY tidak dikoreksi
    vocab.update(["HALO","WOY","WOI","HEI","HAI","OKE","OK","SIP","GAS","GASS","BRO","CUY","P","MAKASIH","CAPEK","WKWK","HAHA","HEHE","SIAPA","KAMU","AKU","KITA","BAHAS","TENTANG","YANG","KALAU","VOID","VVOID","VIOD"])
    # words yang valid jangan dikoreksi
    words = text.upper().split()
    corrected = []
    for w in words:
        if w in vocab or len(w) <= 3:
            corrected.append(w)
        else:
            matches = difflib.get_close_matches(w, vocab, n=1, cutoff=0.85)
            corrected.append(matches[0] if matches else w)
    return " ".join(corrected)

def _keyword_alias(text_upper: str):
    # pakai word boundary agar TIDAK match substring di dalam kata (mis DAK di TIDAK)
    for kw in sorted(KEYWORD_MAP.keys(), key=lambda x: -len(x)):
        if re.search(r"\b" + re.escape(kw) + r"\b", text_upper):
            return KEYWORD_MAP[kw]
    return None

def _handle_name_intent(pesan: str, session_id: str):
    low = pesan.lower()
    # tanya kemampuan ambil nama dari input/login
    if re.search(r"ambil.*nama|bisa.*ambil.*nama|dari.*nama.*input|dari.*login", low):
        name = chatbot.getPredicate("user_name", session_id)
        if name:
            return f"Bisa dong! Aku sudah simpan namamu sebagai {name} dari sesi login. Kalau mau ganti, bilang 'nama saya adalah Budi' — nanti aku update."
        else:
            # coba ambil dari users.json jika ada
            try:
                import json
                users = json.loads((BASE / "data" / "users.json").read_text(encoding="utf-8") or "{}")
                u = users.get(session_id, {})
                if u.get("name"):
                    chatbot.setPredicate("user_name", u["name"], session_id)
                    return f"Bisa! Dari login kamu tercatat sebagai {u['name']}. Mau aku panggil begitu?"
            except:
                pass
            return "Bisa! Cukup bilang 'nama saya adalah Budi' atau login di awal dengan nama, nanti aku ingat dan pakai di chat selanjutnya."
    # recall: siapa nama saya / namaku siapa
    if re.search(r"siapa.*nama.*saya|namaku siapa|siapa namaku", low):
        name = chatbot.getPredicate("user_name", session_id)
        if not name:
            # fallback coba users.json
            try:
                import json
                users = json.loads((BASE / "data" / "users.json").read_text(encoding="utf-8") or "{}")
                name = users.get(session_id, {}).get("name", "")
                if name:
                    chatbot.setPredicate("user_name", name, session_id)
            except:
                pass
        if name:
            return f"Nama kamu adalah {name}, sudah aku ingat! Ada lagi yang mau ditanya soal arsitektur?"
        else:
            return "Aku belum tahu namamu. Coba bilang 'nama saya adalah Budi' — nanti aku ingat."
    m = re.search(r"nama saya (?:adalah|:)?\s*([a-zA-Z\s]{2,32})", low)
    if not m:
        m = re.search(r"panggil saya\s+([a-zA-Z\s]{2,32})", low)
    if not m:
        m = re.search(r"ingat.*nama.*?(?:adalah)?\s*([a-zA-Z]{2,20})$", low)
    if m:
        raw_name = m.group(1).strip()
        raw_name = re.split(r"[.,!;]| ingat", raw_name)[0].strip()
        raw_name = raw_name.split()[0].capitalize() if raw_name else ""
        if raw_name and len(raw_name) >= 2:
            chatbot.setPredicate("user_name", raw_name, session_id)
            # persist ke users.json juga agar tidak hilang ganti sesi
            try:
                import json
                from datetime import datetime
                users_path = BASE / "data" / "users.json"
                users = {}
                if users_path.exists():
                    users = json.loads(users_path.read_text(encoding="utf-8") or "{}")
                users.setdefault(session_id, {})
                users[session_id]["name"] = raw_name
                users[session_id]["updated_at"] = datetime.now().isoformat()
                if "created_at" not in users[session_id]:
                    users[session_id]["created_at"] = users[session_id]["updated_at"]
                # keep email if ada
                users_path.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")
                # also log
                try:
                    from pathlib import Path
                    hist = BASE / "data" / "history" / f"{session_id}.jsonl"
                    hist.parent.mkdir(exist_ok=True, parents=True)
                    with open(hist, "a", encoding="utf-8") as f:
                        import json as _j
                        f.write(_j.dumps({"ts": datetime.now().isoformat(), "session_id": session_id, "role": "system", "message": f"SET name={raw_name}", "name": raw_name}, ensure_ascii=False) + "\n")
                except:
                    pass
            except:
                pass
            return f"Siap, aku ingat namamu adalah {raw_name}! Senang berkenalan. Ada yang mau ditanya soal arsitektur?"
    if re.search(r"siapa.*nama.*kamu|nama kamu siapa|kamu siapa.*nama", low):
        return None
    return None

def get_response(pesan: str, session_id: str = "_global") -> str:
    """Wrapper untuk web & CLI. Handle kosong, personalisasi, typo, alias, fallback helpful."""
    if not pesan or not pesan.strip():
        return "Ketik sesuatu dulu ya."
    original = pesan.strip()
    # 1. personalisasi nama
    name_resp = _handle_name_intent(original, session_id)
    if name_resp:
        return name_resp
    # 2. handle siapa nama kamu -> biarkan AIML tapi fallback ke CORE SIAPA KAMU jika perlu
    low = original.lower()
    if re.search(r"siapa nama kamu", low):
        resp = chatbot.respond("SIAPA KAMU", session_id)
        if resp and not _is_fallback(resp):
            return resp.strip()
    # 3. handle validasi santai "oke, gas" -> jangan dikoreksi typo
    if re.search(r"\b(oke|ok|sip|gass?|gas|mantap|lanjut)\b", low):
        # coba SRAI ke CORE VALIDASI via OKE
        r = chatbot.respond("OKE", session_id)
        if r and not _is_fallback(r):
            return r.strip()
    # 4. coba AIML langsung
    resp = chatbot.respond(original, session_id)
    if resp and resp.strip() and not _is_fallback(resp):
        return resp.strip()
    # 5. handle vague "kita akan bahas tentang yang kamu bilang" -> context recall
    if re.search(r"kita akan bahas|yang kamu bilang|tentang yang.*bilang", low):
        topik = chatbot.getPredicate("TOPIK", session_id)
        if topik:
            r = chatbot.respond(topik, session_id)
            if r and not _is_fallback(r):
                return f"Maksud kamu '{topik.lower()}' yang tadi? " + r.strip()
            return f"Kita tadi bahas {topik}. Mau lanjut detailnya?"
        else:
            return "Boleh, kita mau bahas apa? Coba sebut topiknya, mis. 'void' atau 'elemen arsitektur'."
    # 5. keyword alias untuk query pendek seperti 'void', 'elemen arsitektur?'
    norm_upper = _normalize(original).upper()
    alias_topic = _keyword_alias(norm_upper)
    if alias_topic:
        alias_resp = chatbot.respond(alias_topic, session_id)
        if alias_resp and not _is_fallback(alias_resp):
            return alias_resp.strip()
        master_resp = chatbot.respond(f"MASTER {alias_topic}", session_id)
        if master_resp and not _is_fallback(master_resp):
            return master_resp.strip()
    # 6. typo correction (viod -> void) dengan catatan dinamis
    corrected = _correct_typos(norm_upper)
    if corrected != norm_upper:
        # cari kata yang berubah untuk catatan
        orig_words = norm_upper.split()
        corr_words = corrected.split()
        diffs = [f"'{o.lower()}' jadi '{c.lower()}'" for o,c in zip(orig_words, corr_words) if o!=c]
        note = f" (aku koreksi {', '.join(diffs)} ya)" if diffs else f" (maksud kamu '{corrected.lower()}' ya?)"
        typo_resp = chatbot.respond(corrected, session_id)
        if typo_resp and not _is_fallback(typo_resp):
            return typo_resp.strip() + note
        alias2 = _keyword_alias(corrected)
        if alias2:
            r2 = chatbot.respond(alias2, session_id)
            if r2 and not _is_fallback(r2):
                return r2.strip() + note
            r3 = chatbot.respond(f"MASTER {alias2}", session_id)
            if r3 and not _is_fallback(r3):
                return r3.strip() + note
    # 7. fallback helpful + saran (hanya untuk kata >=4 huruf agar tidak hallucinate untuk 'wah'/'weh')
    suggestions = difflib.get_close_matches(norm_upper, KNOWN_TOPICS, n=3, cutoff=0.45)
    if not suggestions:
        for w in norm_upper.split():
            if len(w) < 4:
                continue
            sugg = difflib.get_close_matches(w, list(KEYWORD_MAP.keys()), n=2, cutoff=0.65)
            if sugg:
                for s in sugg:
                    if KEYWORD_MAP[s] not in suggestions:
                        suggestions.append(KEYWORD_MAP[s])
                    if len(suggestions) >= 3:
                        break
            if len(suggestions) >= 3:
                break
    gaya = chatbot.getPredicate("gaya_bahasa", session_id)
    base = "Maaf, aku belum nangkap maksud '" + original + "'." if gaya == "santai" else f"Maaf, saya kurang mengerti '{original}'."
    if suggestions:
        sug_text = ", ".join([f"'{s.lower()}'" for s in suggestions[:3]])
        return base + f" Mungkin maksud kamu: {sug_text}? Coba tanya seperti 'apa itu void dalam arsitektur'."
    if resp and resp.strip():
        return resp.strip()
    return "Maaf, saya kurang mengerti. Coba tanyakan seputar Fakultas Teknik Arsitektur, mis. 'apa itu void dalam arsitektur' atau 'apa saja elemen arsitektur'."

if __name__ == "__main__":
    print(f"Bot ready | categories={chatbot.numCategories()} | ketik 'keluar' untuk selesai")
    SESSION = "_cli"
    while True:
        try:
            pesan = input("Kamu: ")
        except (EOFError, KeyboardInterrupt):
            print("\nBot: Oke, sampai ketemu lagi!")
            break
        if pesan.strip().lower() in {"keluar", "selesai", "dah", "exit", "quit"}:
            print("Bot: Oke, sampai ketemu lagi!")
            break
        response = get_response(pesan, SESSION)
        print(f"Bot: {response}")

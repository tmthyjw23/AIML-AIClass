from pathlib import Path

import aiml

# --- Kernel tetap global agar bisa di-import dari web wrapper (app.py) ---
chatbot = aiml.Kernel()
# matikan verbose untuk CLI bersih (aktifkan True jika debug)
chatbot.verbose(False)

BASE = Path(__file__).parent
# Load order: domain dulu, NativeConversation terakhir agar fallback "*" paling akhir
chatbot.learn(str(BASE / "Ars_Optimized.aiml"))
chatbot.learn(str(BASE / "NativeConversation.aiml"))




def get_response(pesan: str, session_id: str = "_global") -> str:
    """Wrapper untuk web & CLI. Handle kosong & fallback."""
    if not pesan or not pesan.strip():
        return "Ketik sesuatu dulu ya."
    resp = chatbot.respond(pesan, session_id)
    # AIML mengembalikan "" jika tidak match dan tidak ada fallback
    if not resp or not resp.strip():
        # fallback manual jika "*" di AIML tidak ter-load
        return "Maaf, saya kurang mengerti. Coba tanyakan seputar Fakultas Teknik Arsitektur."
    return resp.strip()


if __name__ == "__main__":
    print(f"Bot ready | categories={chatbot.numCategories()} | ketik 'keluar' untuk selesai")
    # session CLI pakai _global agar gaya_bahasa (santai/formal) persisten
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

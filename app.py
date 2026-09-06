from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from main import get_response, chatbot  # re-use kernel yang sudah di-load
import time

app = Flask(__name__)
CORS(app)  # agar bisa di-fetch dari frontend lain

HTML = r"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arsitek Chatbot - Debug</title>
<style>
  body{font-family:system-ui,Arial;max-width:720px;margin:24px auto;padding:0 16px}
  #log{border:1px solid #ddd;border-radius:12px;padding:12px;height:420px;overflow:auto;background:#fafafa}
  .msg{margin:8px 0;padding:8px 12px;border-radius:10px;max-width:80%}
  .user{background:#dbeafe;margin-left:auto;text-align:right}
  .bot{background:#fff;border:1px solid #e5e7eb}
  #row{display:flex;gap:8px;margin-top:12px}
  input{flex:1;padding:10px;border:1px solid #ccc;border-radius:10px}
  button{padding:10px 16px;border:0;background:#111;color:#fff;border-radius:10px;cursor:pointer}
  small{color:#666}
</style>
</head>
<body>
<h2>Arsitek Chatbot <small id="cats"></small></h2>
<div id="log"></div>
<div id="row">
  <input id="inp" placeholder="Ketik: halo / apa itu bauhaus / kampus ..." autocomplete="off">
  <button id="send">Kirim</button>
</div>
<p><small>Session: <span id="sid"></span> | Coba urutan: <code>HALO -> OKE -> apa itu arsitektur</code> untuk test predicate gaya_bahasa</small></p>
<script>
const sid = 'web_' + Math.random().toString(36).slice(2,8);
document.getElementById('sid').textContent = sid;
const log = document.getElementById('log');
const inp = document.getElementById('inp');
function add(text, cls){ const d=document.createElement('div'); d.className='msg '+cls; d.textContent=text; log.appendChild(d); log.scrollTop=log.scrollHeight; }
async function send(){
  const msg = inp.value.trim(); if(!msg) return;
  add(msg,'user'); inp.value='';
  const res = await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg, session_id:sid})});
  const j = await res.json();
  add(j.response,'bot');
}
document.getElementById('send').onclick=send;
inp.addEventListener('keydown', e=>{ if(e.key==='Enter') send(); });
fetch('/health').then(r=>r.json()).then(j=>{ document.getElementById('cats').textContent='| '+j.categories+' categories'; add(j.demo,'bot'); });
</script>
</body>
</html>
"""

@app.get("/")
def index():
    return render_template_string(HTML)

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "categories": chatbot.numCategories(),
        "demo": get_response("HALO", "_health"),
        "time": time.time()
    })

@app.post("/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    msg = (data.get("message") or "").strip()
    sid = (data.get("session_id") or "_global").strip() or "_global"
    if not msg:
        return jsonify({"response": "Ketik sesuatu dulu ya.", "session_id": sid}), 400
    # optional: log predicate untuk debug
    resp = get_response(msg, sid)
    gaya = chatbot.getPredicate("gaya_bahasa", sid)
    topik = chatbot.getPredicate("TOPIK", sid)
    return jsonify({
        "response": resp,
        "session_id": sid,
        "predicate": {"gaya_bahasa": gaya, "TOPIK": topik}
    })

# kompatibel dengan `python app.py` dan `flask run`
if __name__ == "__main__":
    print(f"[app] categories={chatbot.numCategories()} http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)

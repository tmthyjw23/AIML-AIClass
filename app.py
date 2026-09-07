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
<title>ArsitekBot — AI-Powered AIML Chatbot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Geist:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box}
  html,body{height:100%;margin:0}
  body{
    font-family:'Inter',system-ui,-apple-system,Segoe UI,Roboto,Arial;
    background:#000;
    color:#fff;
    overflow-x:hidden;
    -webkit-font-smoothing:antialiased;
  }
  /* dotted grid like 21st.dev */
  .bg-dots{
    position:fixed; inset:0;
    background-image: radial-gradient(rgba(255,255,255,.18) 1px, transparent 1px);
    background-size:22px 22px;
    mask: radial-gradient(ellipse at center, black 60%, transparent 85%);
    opacity:.55;
    pointer-events:none;
  }
  .bg-glow{
    position:fixed; inset:0; pointer-events:none;
    background:
      radial-gradient(600px 400px at 70% -10%, rgba(255,255,255,.07), transparent 60%),
      radial-gradient(800px 600px at 50% 120%, rgba(255,255,255,.05), transparent 60%);
  }
  a{color:inherit;text-decoration:none}
  /* pill navbar — exact like preview */
  .nav-wrap{position:fixed; top:18px; left:50%; transform:translateX(-50%); z-index:30; width:min(720px, calc(100% - 24px));}
  .nav-pill{
    display:flex; align-items:center; justify-content:space-between; gap:16px;
    background:rgba(18,18,18,.72); backdrop-filter:blur(16px) saturate(140%);
    border:1px solid rgba(255,255,255,.12);
    border-radius:9999px; padding:8px 10px 8px 14px;
    box-shadow:0 10px 40px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.06);
  }
  .nav-left{display:flex; align-items:center; gap:18px}
  .logo{width:32px;height:32px; display:grid; place-items:center; border-radius:50%;}
  .logo-dots{width:22px;height:22px; display:grid; grid-template-columns:6px 6px; gap:4px; place-content:center}
  .logo-dots i{width:5px;height:5px; background:#fff; border-radius:50%; display:block; opacity:.95}
  .logo-dots i:nth-child(1){opacity:.9} .logo-dots i:nth-child(2){opacity:.7} .logo-dots i:nth-child(3){opacity:.45} .logo-dots i:nth-child(4){opacity:1}
  .nav-links{display:flex; gap:22px; font-size:14px; font-weight:500; color:rgba(255,255,255,.78)}
  .nav-links a:hover{color:#fff}
  .nav-actions{display:flex; gap:8px; align-items:center}
  .btn-pill{
    border-radius:9999px; padding:10px 18px; font-size:14px; font-weight:600; border:1px solid rgba(255,255,255,.14);
    background:rgba(255,255,255,.06); color:#fff; cursor:pointer; transition:.2s;
  }
  .btn-pill:hover{background:rgba(255,255,255,.10)}
  .btn-pill.primary{ background:#fff; color:#000; border-color:#fff; box-shadow:0 0 28px rgba(255,255,255,.45), 0 4px 16px rgba(0,0,0,.4); }
  .btn-pill.primary:hover{ background:#f5f5f5; transform:translateY(-1px)}
  /* layout */
  .stage{min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:108px 16px 32px; position:relative; z-index:1}
  .hero{width:min(640px, 100%); text-align:center; animation:fadeUp .7s ease both}
  .hero h1{font-size:clamp(36px, 6vw, 54px); line-height:1.02; letter-spacing:-.04em; font-weight:700; margin:0 0 10px}
  .hero p.sub{color:rgba(255,255,255,.62); font-size:clamp(18px, 3vw, 30px); font-weight:400; margin:0 0 28px; letter-spacing:-.02em}
  @keyframes fadeUp{from{opacity:0; transform:translateY(8px)} to{opacity:1; transform:translateY(0)}}
  /* sign-in pills */
  .pill{
    width:100%; background:rgba(18,18,18,.85); border:1px solid rgba(255,255,255,.14);
    border-radius:9999px; padding:14px 16px; display:flex; align-items:center; gap:12px;
    backdrop-filter:blur(12px); box-shadow:inset 0 1px 0 rgba(255,255,255,.06);
    transition:border-color .2s, background .2s;
  }
  .pill:hover{border-color:rgba(255,255,255,.22)}
  .pill:focus-within{border-color:rgba(255,255,255,.28); background:rgba(22,22,22,.95)}
  .pill-google{justify-content:center; cursor:pointer; font-weight:500; font-size:15px}
  .pill-google:hover{background:rgba(28,28,28,1)}
  .pill input{
    flex:1; background:transparent; border:0; outline:0; color:#fff; font-size:15px; text-align:center;
  }
  .pill input::placeholder{color:rgba(255,255,255,.5)}
  .pill .arrow{
    width:40px; height:40px; border-radius:50%; background:rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.08);
    display:grid; place-items:center; cursor:pointer; flex-shrink:0; transition:.2s;
  }
  .pill .arrow:hover{background:#fff; color:#000; transform:scale(1.02)}
  .divider{display:flex; align-items:center; gap:16px; color:rgba(255,255,255,.35); font-size:14px; margin:16px 0}
  .divider::before,.divider::after{content:""; flex:1; height:1px; background:rgba(255,255,255,.12)}
  .terms{margin-top:26px; color:rgba(255,255,255,.42); font-size:12px; line-height:1.6}
  .terms a{color:rgba(255,255,255,.7); text-decoration:underline; text-underline-offset:3px}
  /* chat view — same pill language */
  .chat-shell{width:min(760px, 100%); display:none; flex-direction:column; gap:14px; animation:fadeUp .5s ease both}
  .chat-shell.active{display:flex}
  .chat-log{
    background:rgba(16,16,16,.72); backdrop-filter:blur(14px);
    border:1px solid rgba(255,255,255,.10); border-radius:24px; padding:18px;
    height:min(58vh, 520px); overflow:auto; display:flex; flex-direction:column; gap:10px;
    box-shadow:0 20px 60px rgba(0,0,0,.5);
  }
  .chat-log::-webkit-scrollbar{width:6px}
  .chat-log::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15); border-radius:9999px}
  .bubble{max-width:78%; padding:12px 16px; border-radius:18px; font-size:14px; line-height:1.55; word-wrap:break-word}
  .bubble.user{align-self:flex-end; background:#fff; color:#000; border-bottom-right-radius:6px; font-weight:500}
  .bubble.bot{align-self:flex-start; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.10); color:rgba(255,255,255,.92); border-bottom-left-radius:6px}
  .bubble.bot small{color:rgba(255,255,255,.45); font-size:11px; display:block; margin-top:6px}
  .chat-input-row{display:flex; gap:10px; align-items:center}
  .chat-input-row .pill{padding:10px 12px 10px 18px}
  .hint{color:rgba(255,255,255,.38); font-size:12px; text-align:center; margin-top:6px}
  .hidden{display:none !important}
  @media (max-width:640px){
    .nav-links{display:none}
    .nav-pill{padding:6px 8px 6px 10px}
    .hero h1{font-size:36px}
    .hero p.sub{font-size:20px}
  }
</style>
</head>
<body>
<div class="bg-dots"></div>
<div class="bg-glow"></div>

<div class="nav-wrap">
  <div class="nav-pill">
    <div class="nav-left">
      <div class="logo" aria-label="logo"><div class="logo-dots"><i></i><i></i><i></i><i></i></div></div>
      <nav class="nav-links">
        <a href="#" onclick="toast('Manifesto — ArsitekBot untuk edukasi Teknik Arsitektur');return false">Manifesto</a>
        <a href="#" onclick="toast('Features: 150+ topik, context-aware, web chat');return false">Careers</a>
        <a href="#" onclick="toast('Discover: coba tanya — apa itu bauhaus?');return false">Discover</a>
      </nav>
    </div>
    <div class="nav-actions">
      <button class="btn-pill" onclick="enterGuest()">LogIn</button>
      <button class="btn-pill primary" onclick="enterGuest()">Signup</button>
    </div>
  </div>
</div>

<main class="stage">
  <!-- AUTH VIEW — exact clone of 21st.dev sign-in flow -->
  <section id="authView" class="hero">
    <h1>Welcome Developer</h1>
    <p class="sub">Your sign in component</p>

    <div style="margin-top:6px">
      <button class="pill pill-google" onclick="signInGoogle()">
        <span style="font-weight:700; font-size:18px; width:18px; text-align:center">G</span>
        <span>Sign in with Google</span>
      </button>

      <div class="divider">or</div>

      <div class="pill" id="emailPill">
        <input id="emailInput" type="email" placeholder="info@gmail.com" autocomplete="email" onkeydown="if(event.key==='Enter') enterChat()">
        <button class="arrow" onclick="enterChat()" aria-label="continue">→</button>
      </div>

      <div class="hint" style="margin-top:10px">Tekan Enter atau → untuk lanjut sebagai tamu — email opsional</div>

      <p class="terms">
        By signing up, you agree to the <a href="#">MSA</a>, <a href="#">Product Terms</a>, <a href="#">Policies</a>,<br>
        <a href="#">Privacy Notice</a>, and <a href="#">Cookie Notice</a>.
      </p>

      <p class="hint" id="catsLine" style="margin-top:18px"></p>
    </div>
  </section>

  <!-- CHAT VIEW — same pill design language -->
  <section id="chatView" class="chat-shell">
    <div style="text-align:center; margin-bottom:2px">
      <h2 style="margin:0; font-size:22px; letter-spacing:-.02em">ArsitekBot</h2>
      <p style="margin:6px 0 0; color:rgba(255,255,255,.55); font-size:13px">Context-aware • <span id="sessLabel"></span> • <span id="catLabel"></span></p>
    </div>

    <div id="log" class="chat-log"></div>

    <div class="chat-input-row">
      <div class="pill" style="flex:1">
        <input id="inp" placeholder="Tanya: halo / apa itu bauhaus / void dalam arsitektur..." autocomplete="off">
        <button class="arrow" id="send" aria-label="send">→</button>
      </div>
    </div>
    <div class="hint">Coba urutan context: <code>apa itu bauhaus</code> → <code>jelaskan lebih detail</code> → <code>tadi aku nanya apa</code></div>
    <div style="text-align:center; margin-top:6px">
      <button onclick="backToAuth()" style="background:transparent; border:0; color:rgba(255,255,255,.5); font-size:12px; cursor:pointer; text-decoration:underline">← Kembali ke Sign In</button>
    </div>
  </section>
</main>

<script>
const sid = 'web_' + Math.random().toString(36).slice(2,8);
let email = '';
const log = document.getElementById('log');
const inp = document.getElementById('inp');
const emailInput = document.getElementById('emailInput');
const authView = document.getElementById('authView');
const chatView = document.getElementById('chatView');

function toast(msg){
  add(msg, 'bot', true);
  if(chatView.classList.contains('active')) return;
  // small temp toast in auth
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = 'position:fixed; bottom:18px; left:50%; transform:translateX(-50%); background:rgba(20,20,20,.9); border:1px solid rgba(255,255,255,.12); padding:10px 14px; border-radius:9999px; font-size:12px; z-index:50';
  document.body.appendChild(t); setTimeout(()=>t.remove(), 2200);
}
function add(text, who, isToast){
  const d = document.createElement('div');
  d.className = 'bubble ' + who;
  d.textContent = text;
  if(who==='bot' && !isToast){
    const meta = document.createElement('small');
    meta.textContent = new Date().toLocaleTimeString('id-ID', {hour:'2-digit', minute:'2-digit'});
    d.appendChild(meta);
  }
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
}
async function send(){
  const msg = inp.value.trim(); if(!msg) return;
  add(msg, 'user'); inp.value='';
  const r = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message: msg, session_id: sid})});
  const j = await r.json();
  add(j.response, 'bot');
}
function enterGuest(){
  email = emailInput.value.trim();
  authView.classList.add('hidden');
  chatView.classList.add('active');
  document.getElementById('sessLabel').textContent = email ? email + ' · ' + sid : sid;
  if(log.children.length===0){
    fetch('/health').then(r=>r.json()).then(j=>{
      document.getElementById('catLabel').textContent = j.categories + ' categories';
      add(j.demo, 'bot');
    });
  }
  setTimeout(()=> inp.focus(), 120);
}
function enterChat(){
  const v = emailInput.value.trim();
  if(v && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)){
    emailInput.style.outline = '1px solid #ff5a5a';
    toast('Format email tidak valid — tetap bisa lanjut sebagai tamu');
    setTimeout(()=> emailInput.style.outline='', 1200);
  }
  enterGuest();
}
function signInGoogle(){
  toast('Sign in with Google — mock (langsung masuk sebagai tamu)');
  setTimeout(enterGuest, 400);
}
function backToAuth(){
  chatView.classList.remove('active');
  authView.classList.remove('hidden');
}
document.getElementById('send').onclick = send;
inp.addEventListener('keydown', e=>{ if(e.key==='Enter') send(); });
emailInput.addEventListener('keydown', e=>{ if(e.key==='Enter') enterChat(); });
// init cats line
fetch('/health').then(r=>r.json()).then(j=>{
  document.getElementById('catsLine').textContent = j.categories + ' AIML categories • Context-aware • Flask';
});
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

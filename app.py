from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from main import get_response, chatbot
import time, json, threading, re, html
from datetime import datetime

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:5000", "http://localhost:5000", "http://127.0.0.1:*", "http://localhost:*"]}})

# --- Persistent storage (nama user & history log) ---
DATA_DIR = Path(__file__).parent / "data"
HISTORY_DIR = DATA_DIR / "history"
USERS_FILE = DATA_DIR / "users.json"
LOG_FILE = DATA_DIR / "chat_log.jsonl"
_lock = threading.Lock()

def ensure_dirs():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("{}", encoding="utf-8")
    if not LOG_FILE.exists():
        LOG_FILE.write_text("", encoding="utf-8")

ensure_dirs()

def sanitize_sid(sid: str) -> str:
    """Whitelist session_id: alnum, _, -, 1-64 chars. Reject traversal."""
    sid = (sid or "").strip()
    if not sid:
        return "_global"
    if "/" in sid or "\\" in sid or ".." in sid:
        return "_global"
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", sid):
        cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", sid)[:64].strip("_")
        return cleaned if cleaned and re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", cleaned) else "_global"
    return sid

def safe_history_path(sid: str) -> Path:
    safe = sanitize_sid(sid)
    path = (HISTORY_DIR / f"{safe}.jsonl").resolve()
    try:
        if not path.is_relative_to(HISTORY_DIR.resolve()):
            return (HISTORY_DIR / "_global.jsonl").resolve()
    except AttributeError:
        if not str(path).startswith(str(HISTORY_DIR.resolve())):
            return (HISTORY_DIR / "_global.jsonl").resolve()
    return path

def load_users():
    with _lock:
        try:
            txt = USERS_FILE.read_text(encoding="utf-8") or "{}"
            data = json.loads(txt)
            if not isinstance(data, dict):
                return {}
            return data
        except Exception:
            try:
                USERS_FILE.rename(USERS_FILE.with_suffix(".corrupt." + datetime.now().strftime("%Y%m%d%H%M%S")))
                USERS_FILE.write_text("{}", encoding="utf-8")
            except:
                pass
            return {}

def save_users(data):
    with _lock:
        USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def save_user(session_id, name, email):
    session_id = sanitize_sid(session_id)
    name = html.escape(name.strip()[:64])
    email = html.escape(email.strip()[:100])
    users = load_users()
    users[session_id] = {
        "name": name.strip(),
        "email": email.strip(),
        "updated_at": datetime.now().isoformat(),
        "created_at": users.get(session_id, {}).get("created_at", datetime.now().isoformat())
    }
    save_users(users)
    # also set AIML predicates for personalization
    if name:
        chatbot.setPredicate("user_name", name.strip(), session_id)
    if email:
        chatbot.setPredicate("user_email", email.strip(), session_id)

def get_user(session_id):
    return load_users().get(sanitize_sid(session_id), {})

def append_history(session_id, role, message, name=""):
    ensure_dirs()
    session_id = sanitize_sid(session_id)
    message = str(message)[:2000]
    name = html.escape(str(name)[:64])
    entry = {
        "ts": datetime.now().isoformat(),
        "session_id": session_id,
        "role": role,  # user | bot
        "message": message,
        "name": name
    }
    sess_file = safe_history_path(session_id)
    with _lock:
        try:
            if sess_file.exists() and sess_file.stat().st_size > 5*1024*1024:
                sess_file.rename(sess_file.with_suffix(".old." + datetime.now().strftime("%Y%m%d%H%M%S")))
        except:
            pass
        with open(sess_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        try:
            if LOG_FILE.exists() and LOG_FILE.stat().st_size > 10*1024*1024:
                LOG_FILE.rename(LOG_FILE.with_suffix(".old." + datetime.now().strftime("%Y%m%d%H%M%S")))
                LOG_FILE.write_text("", encoding="utf-8")
        except:
            pass
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def read_history(session_id, limit=100):
    sess_file = safe_history_path(session_id)
    if not sess_file.exists():
        return []
    with _lock:
        try:
            txt = sess_file.read_text(encoding="utf-8")
        except:
            return []
    lines = txt.strip().splitlines()
    # keep last limit
    out = []
    for l in lines[-limit:]:
        try:
            out.append(json.loads(l))
        except:
            continue
    return out

def clear_session_predicates(session_id, mode="context"):
    session_id = sanitize_sid(session_id)
    # mode: context -> clear TOPIK & gaya_bahasa only; session -> full reset
    if mode == "session":
        # delete session entirely (Kernel internal)
        try:
            chatbot._deleteSession(session_id)
        except:
            pass
        # also clear history file (optional keep for audit — we keep but predicate cleared)
        # we keep file, but user can request history clear via separate
        chatbot._addSession(session_id)
        chatbot.setPredicate("TOPIK", "", session_id)
        chatbot.setPredicate("gaya_bahasa", "", session_id)
        chatbot.setPredicate("user_name", get_user(session_id).get("name",""), session_id)
    else:  # context
        chatbot.setPredicate("TOPIK", "", session_id)
        # keep gaya_bahasa as is to keep persona, but clear last topic
        # also clear _inputHistory/_outputHistory last? keep for audit but topic cleared


# --- Simple rate limit (in-memory) ---
_rate = {}
_rate_lock = threading.Lock()
def check_rate(sid, limit=20, window=60):
    now = time.time()
    with _rate_lock:
        lst = _rate.get(sid, [])
        lst = [t for t in lst if now - t < window]
        if len(lst) >= limit:
            return False
        lst.append(now)
        _rate[sid] = lst
        return True

@app.before_request
def rate_guard():
    if request.path in ("/chat", "/login") and request.method=="POST":
        sid = ""
        try:
            sid = (request.get_json(silent=True) or {}).get("session_id","") or request.headers.get("X-Session-Id","") or request.remote_addr or "unknown"
        except:
            sid = request.remote_addr or "unknown"
        sid = sanitize_sid(sid) if sid and sid != "unknown" else (request.remote_addr or "unknown")
        # use sanitized but fallback to ip
        check_sid = sid if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", sid) else (request.remote_addr or "unknown")
        if not check_rate(check_sid, limit=30, window=60):
            return jsonify({"error":"rate limit, coba lagi 1 menit"}), 429

@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp

HTML = r"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ArsitekBot — AI-Powered AIML Chatbot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box}
  html,body{height:100%;margin:0}
  body{
    font-family:'Inter',system-ui,-apple-system,Segoe UI,Roboto,Arial;
    background:#000; color:#fff; overflow-x:hidden; -webkit-font-smoothing:antialiased;
  }
  .bg-dots{
    position:fixed; inset:0;
    background-image: radial-gradient(rgba(255,255,255,.18) 1px, transparent 1px);
    background-size:22px 22px;
    mask: radial-gradient(ellipse at center, black 60%, transparent 85%);
    opacity:.55; pointer-events:none;
  }
  .bg-glow{
    position:fixed; inset:0; pointer-events:none;
    background:
      radial-gradient(600px 400px at 70% -10%, rgba(255,255,255,.07), transparent 60%),
      radial-gradient(800px 600px at 50% 120%, rgba(255,255,255,.05), transparent 60%);
  }
  a{color:inherit;text-decoration:none}
  .nav-wrap{position:fixed; top:18px; left:50%; transform:translateX(-50%); z-index:30; width:min(820px, calc(100% - 24px));}
  .nav-pill{
    display:flex; align-items:center; justify-content:space-between; gap:12px;
    background:rgba(18,18,18,.72); backdrop-filter:blur(16px) saturate(140%);
    border:1px solid rgba(255,255,255,.12); border-radius:9999px; padding:8px 10px 8px 14px;
    box-shadow:0 10px 40px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.06);
  }
  .nav-left{display:flex; align-items:center; gap:14px}
  .logo{width:32px;height:32px; display:grid; place-items:center; border-radius:50%; flex-shrink:0}
  .logo-dots{width:22px;height:22px; display:grid; grid-template-columns:6px 6px; gap:4px; place-content:center}
  .logo-dots i{width:5px;height:5px; background:#fff; border-radius:50%; display:block}
  .logo-dots i:nth-child(1){opacity:.9} .logo-dots i:nth-child(2){opacity:.7} .logo-dots i:nth-child(3){opacity:.45} .logo-dots i:nth-child(4){opacity:1}
  .nav-links{display:flex; gap:14px; font-size:13px; font-weight:500; color:rgba(255,255,255,.72)}
  .nav-links a{padding:6px 10px; border-radius:9999px; border:1px solid transparent}
  .nav-links a:hover{color:#fff; background:rgba(255,255,255,.06); border-color:rgba(255,255,255,.08)}
  .nav-actions{display:flex; gap:8px; align-items:center}
  .btn-pill{
    border-radius:9999px; padding:9px 15px; font-size:13px; font-weight:600; border:1px solid rgba(255,255,255,.14);
    background:rgba(255,255,255,.06); color:#fff; cursor:pointer; transition:.2s; white-space:nowrap;
  }
  .btn-pill:hover{background:rgba(255,255,255,.10)}
  .btn-pill.primary{ background:#fff; color:#000; border-color:#fff; box-shadow:0 0 28px rgba(255,255,255,.45), 0 4px 16px rgba(0,0,0,.4); }
  .btn-pill.primary:hover{ background:#f5f5f5; transform:translateY(-1px)}
  .btn-pill.small{padding:7px 12px; font-size:12px}
  .btn-pill.danger{border-color:rgba(255,80,80,.3); background:rgba(255,50,50,.08); color:#ff9a9a}
  .btn-pill.danger:hover{background:rgba(255,50,50,.15)}
  .user-pill{
    display:flex; align-items:center; gap:8px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.12);
    border-radius:9999px; padding:6px 10px 6px 8px; font-size:12px; color:rgba(255,255,255,.85)
  }
  .user-pill .avatar{width:22px; height:22px; border-radius:50%; background:#fff; color:#000; display:grid; place-items:center; font-weight:700; font-size:11px; flex-shrink:0}
  .stage{min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:108px 16px 32px; position:relative; z-index:1}
  .hero{width:min(640px, 100%); text-align:center; animation:fadeUp .7s ease both}
  .hero h1{font-size:clamp(36px, 6vw, 54px); line-height:1.02; letter-spacing:-.04em; font-weight:700; margin:0 0 10px}
  .hero p.sub{color:rgba(255,255,255,.62); font-size:clamp(18px, 3vw, 30px); font-weight:400; margin:0 0 28px; letter-spacing:-.02em}
  @keyframes fadeUp{from{opacity:0; transform:translateY(8px)} to{opacity:1; transform:translateY(0)}}
  .pill{
    width:100%; background:rgba(18,18,18,.85); border:1px solid rgba(255,255,255,.14);
    border-radius:9999px; padding:12px 16px; display:flex; align-items:center; gap:12px;
    backdrop-filter:blur(12px); box-shadow:inset 0 1px 0 rgba(255,255,255,.06);
    transition:border-color .2s, background .2s;
  }
  .pill:hover{border-color:rgba(255,255,255,.22)}
  .pill:focus-within{border-color:rgba(255,255,255,.28); background:rgba(22,22,22,.95)}
  .pill input{
    flex:1; background:transparent; border:0; outline:0; color:#fff; font-size:15px; text-align:center;
  }
  .pill input::placeholder{color:rgba(255,255,255,.5)}
  .pill .arrow{
    width:40px; height:40px; border-radius:50%; background:rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.08);
    display:grid; place-items:center; cursor:pointer; flex-shrink:0; transition:.2s;
  }
  .pill .arrow:hover{background:#fff; color:#000; transform:scale(1.02)}
  .divider{display:flex; align-items:center; gap:16px; color:rgba(255,255,255,.35); font-size:14px; margin:14px 0}
  .divider::before,.divider::after{content:""; flex:1; height:1px; background:rgba(255,255,255,.12)}
  .terms{margin-top:20px; color:rgba(255,255,255,.42); font-size:12px; line-height:1.6}
  .terms a{color:rgba(255,255,255,.7); text-decoration:underline; text-underline-offset:3px}
  .chat-shell{width:min(780px, 100%); display:none; flex-direction:column; gap:14px; animation:fadeUp .5s ease both}
  .chat-shell.active{display:flex}
  .chat-log{
    background:rgba(16,16,16,.72); backdrop-filter:blur(14px);
    border:1px solid rgba(255,255,255,.10); border-radius:24px; padding:18px;
    height:min(56vh, 520px); overflow:auto; display:flex; flex-direction:column; gap:10px;
    box-shadow:0 20px 60px rgba(0,0,0,.5);
  }
  .chat-log::-webkit-scrollbar{width:6px}
  .chat-log::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15); border-radius:9999px}
  .bubble{max-width:78%; padding:11px 15px; border-radius:18px; font-size:14px; line-height:1.55; word-wrap:break-word}
  .bubble.user{align-self:flex-end; background:#fff; color:#000; border-bottom-right-radius:6px; font-weight:500}
  .bubble.bot{align-self:flex-start; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.10); color:rgba(255,255,255,.92); border-bottom-left-radius:6px}
  .bubble.bot small{color:rgba(255,255,255,.45); font-size:11px; display:block; margin-top:6px}
  .chat-input-row{display:flex; gap:10px; align-items:center}
  .chat-input-row .pill{padding:10px 12px 10px 18px}
  .hint{color:rgba(255,255,255,.38); font-size:12px; text-align:center; margin-top:6px}
  .hidden{display:none !important}
  /* modal */
  .modal-bg{position:fixed; inset:0; background:rgba(0,0,0,.6); backdrop-filter:blur(8px); display:none; place-items:center; z-index:50; padding:16px}
  .modal-bg.open{display:grid}
  .modal{
    width:min(480px, 100%); background:#111; border:1px solid rgba(255,255,255,.12); border-radius:20px; padding:22px;
    box-shadow:0 20px 60px rgba(0,0,0,.6);
  }
  .modal h3{margin:0 0 14px; font-size:18px}
  .field{margin-bottom:12px}
  .field label{display:block; font-size:12px; color:rgba(255,255,255,.6); margin-bottom:6px}
  .field input, .field select{
    width:100%; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); color:#fff;
    padding:10px 14px; border-radius:12px; outline:0; font-size:14px;
  }
  .field input:focus, .field select:focus{border-color:rgba(255,255,255,.25)}
  .row{ display:flex; gap:10px; justify-content:flex-end; margin-top:16px}
  @media (max-width:740px){
    .nav-links{display:none}
    .nav-pill{padding:6px 8px}
    .hero h1{font-size:36px}
    .hero p.sub{font-size:20px}
    .nav-actions .btn-pill{padding:7px 10px; font-size:12px}
  }
</style>
</head>
<body>
<div class="bg-dots"></div>
<div class="bg-glow"></div>

<div class="nav-wrap">
  <div class="nav-pill" id="navPill">
    <div class="nav-left">
      <div class="logo"><div class="logo-dots"><i></i><i></i><i></i><i></i></div></div>
      <!-- guest nav -->
      <nav class="nav-links" id="navGuest">
        <a href="#" onclick="toast('ArsitekBot — 875 AIML categories, context-aware');return false">Manifesto</a>
        <a href="#" onclick="toast('Fitur: login nama, history log, reset konteks/sesi');return false">Careers</a>
        <a href="#" onclick="toast('Coba: apa itu bauhaus → jelaskan lebih detail → tadi aku nanya apa');return false">Discover</a>
      </nav>
      <!-- logged in user pill -->
      <div id="navUser" class="user-pill hidden">
        <div class="avatar" id="navAvatar">A</div>
        <span id="navName">User</span>
        <span style="opacity:.4">·</span>
        <span id="navSess" style="opacity:.6; font-size:11px"></span>
      </div>
    </div>
    <div class="nav-actions" id="navActionsGuest">
      <button class="btn-pill" onclick="focusAuth()">LogIn</button>
      <button class="btn-pill primary" onclick="focusAuth()">Signup</button>
    </div>
    <div class="nav-actions hidden" id="navActionsUser">
      <button class="btn-pill small" onclick="resetContext()" title="Hapus TOPIK & konteks arsitektur">Reset Konteks</button>
      <button class="btn-pill small danger" onclick="resetSession()" title="Hapus semua sesi & gaya_bahasa">Reset Sesi</button>
      <button class="btn-pill small" onclick="openSettings()">Pengaturan</button>
      <button class="btn-pill small" onclick="logout()" style="background:rgba(255,255,255,.10)">Logout</button>
    </div>
  </div>
</div>

<main class="stage">
  <section id="authView" class="hero">
    <h1>Welcome Developer</h1>
    <p class="sub">Your sign in component</p>
    <div style="margin-top:6px">
      <button class="pill pill-google" onclick="signInGoogle()">
        <span style="font-weight:700; font-size:18px; width:18px; text-align:center">G</span>
        <span>Sign in with Google</span>
      </button>
      <div class="divider">or</div>
      <div class="pill" id="namePill" style="margin-bottom:10px">
        <input id="nameInput" type="text" placeholder="Nama Anda" maxlength="32" autocomplete="name" onkeydown="if(event.key==='Enter') document.getElementById('emailInput').focus()">
        <span style="opacity:.35; font-size:13px">👤</span>
      </div>
      <div class="pill" id="emailPill">
        <input id="emailInput" type="email" placeholder="info@gmail.com" autocomplete="email" onkeydown="if(event.key==='Enter') enterChat()">
        <button class="arrow" onclick="enterChat()" aria-label="continue">→</button>
      </div>
      <div class="hint" style="margin-top:10px">Nama akan disimpan & history dicatat di log. Email opsional.</div>
      <p class="terms">
        By signing up, you agree to the <a href="#">MSA</a>, <a href="#">Product Terms</a>, <a href="#">Policies</a>,<br>
        <a href="#">Privacy Notice</a>, and <a href="#">Cookie Notice</a>.
      </p>
      <p class="hint" id="catsLine" style="margin-top:18px"></p>
    </div>
  </section>

  <section id="chatView" class="chat-shell">
    <div style="text-align:center; margin-bottom:2px">
      <h2 style="margin:0; font-size:22px; letter-spacing:-.02em">ArsitekBot <span id="helloName" style="font-weight:400; color:rgba(255,255,255,.55)"></span></h2>
      <p style="margin:6px 0 0; color:rgba(255,255,255,.55); font-size:12px">
        <span id="catLabel"></span> • <span id="sessLabel"></span> • <span id="historyCount"></span>
      </p>
    </div>
    <div id="log" class="chat-log"></div>
    <div class="chat-input-row">
      <div class="pill" style="flex:1">
        <input id="inp" placeholder="Tanya: halo / apa itu bauhaus / void dalam arsitektur..." autocomplete="off">
        <button class="arrow" id="send" aria-label="send">→</button>
      </div>
    </div>
    <div class="hint">Context test: <code>apa itu bauhaus</code> → <code>jelaskan lebih detail</code> → <code>tadi aku nanya apa</code> &nbsp;|&nbsp; <a href="#" onclick="loadHistory();return false" style="color:rgba(255,255,255,.6); text-decoration:underline">Lihat history log</a></div>
  </section>
</main>

<!-- Settings Modal -->
<div id="settingsModal" class="modal-bg" onclick="if(event.target===this) closeSettings()">
  <div class="modal">
    <h3>Pengaturan User</h3>
    <div class="field">
      <label>Nama</label>
      <input id="setName" type="text" maxlength="32" placeholder="Nama Anda">
    </div>
    <div class="field">
      <label>Email</label>
      <input id="setEmail" type="email" placeholder="info@gmail.com">
    </div>
    <div class="field">
      <label>Gaya Bahasa</label>
      <select id="setGaya">
        <option value="">Otomatis (sesuai sapaan)</option>
        <option value="santai">Santai (gue, bro)</option>
        <option value="formal">Formal (saya, Anda)</option>
      </select>
    </div>
    <div class="field">
      <label>Session ID</label>
      <input id="setSid" type="text" disabled style="opacity:.6">
    </div>
    <div class="row">
      <button class="btn-pill small" onclick="closeSettings()">Batal</button>
      <button class="btn-pill primary small" onclick="saveSettings()">Simpan</button>
    </div>
    <p class="hint" style="margin-top:12px; text-align:left">Nama & email disimpan di <code>data/users.json</code>, history di <code>data/history/{sid}.jsonl</code> & <code>data/chat_log.jsonl</code></p>
  </div>
</div>

<script>
let sid = localStorage.getItem('ars_sid') || ('web_' + Math.random().toString(36).slice(2,8));
let userName = localStorage.getItem('ars_name') || '';
let userEmail = localStorage.getItem('ars_email') || '';
localStorage.setItem('ars_sid', sid);

const log = document.getElementById('log');
const inp = document.getElementById('inp');
const nameInput = document.getElementById('nameInput');
const emailInput = document.getElementById('emailInput');
const authView = document.getElementById('authView');
const chatView = document.getElementById('chatView');

function updateNav(){
  const logged = !!localStorage.getItem('ars_logged');
  document.getElementById('navGuest').classList.toggle('hidden', logged);
  document.getElementById('navActionsGuest').classList.toggle('hidden', logged);
  document.getElementById('navUser').classList.toggle('hidden', !logged);
  document.getElementById('navActionsUser').classList.toggle('hidden', !logged);
  if(logged){
    const n = localStorage.getItem('ars_name') || 'User';
    document.getElementById('navName').textContent = n;
    document.getElementById('navAvatar').textContent = n.trim().charAt(0).toUpperCase() || 'U';
    document.getElementById('navSess').textContent = sid;
    document.getElementById('helloName').textContent = '— hai, ' + n + '!';
  }
}
function toast(msg){
  const t=document.createElement('div');
  t.textContent=msg;
  t.style.cssText='position:fixed; bottom:18px; left:50%; transform:translateX(-50%); background:rgba(20,20,20,.92); border:1px solid rgba(255,255,255,.12); padding:10px 14px; border-radius:9999px; font-size:12px; z-index:60';
  document.body.appendChild(t); setTimeout(()=>t.remove(), 2400);
}
function add(text, who){
  const d=document.createElement('div');
  d.className='bubble '+who;
  d.textContent=text;
  if(who==='bot'){
    const m=document.createElement('small');
    m.textContent=new Date().toLocaleTimeString('id-ID',{hour:'2-digit',minute:'2-digit'});
    d.appendChild(m);
  }
  log.appendChild(d); log.scrollTop=log.scrollHeight;
}
async function send(){
  const msg=inp.value.trim(); if(!msg) return;
  add(msg,'user'); inp.value='';
  const r=await fetch('/chat',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg, session_id:sid})});
  const j=await r.json();
  add(j.response,'bot');
  document.getElementById('historyCount').textContent = 'history: ' + (log.children.length-1) + ' pesan';
}
async function enterChat(){
  const name = nameInput.value.trim() || userName || '';
  const email = emailInput.value.trim() || userEmail || '';
  if(!name){
    nameInput.style.outline='1px solid #ff5a5a'; nameInput.placeholder='Isi nama dulu';
    setTimeout(()=>nameInput.style.outline='',1200);
    // allow guest without name but warn
    // return;
  }
  if(email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){
    emailInput.style.outline='1px solid #ff5a5a';
    toast('Email tidak valid'); setTimeout(()=>emailInput.style.outline='',1200); return;
  }
  const finalName = name || 'Tamu';
  // persist to backend
  await fetch('/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:sid, name:finalName, email:email})});
  localStorage.setItem('ars_name', finalName);
  localStorage.setItem('ars_email', email);
  localStorage.setItem('ars_logged','1');
  userName=finalName; userEmail=email;
  authView.classList.add('hidden'); chatView.classList.add('active');
  updateNav();
  document.getElementById('sessLabel').textContent=sid;
  document.getElementById('setSid').value=sid;
  if(log.children.length===0){
    const h=await (await fetch('/health')).json();
    document.getElementById('catLabel').textContent=h.categories+' categories';
    add(h.demo,'bot');
    // load existing history
    loadHistory(true);
  }
  setTimeout(()=>inp.focus(),120);
}
function signInGoogle(){
  // mock google -> use name Google User
  nameInput.value = nameInput.value || 'Google User';
  toast('Sign in with Google — mock OK');
  setTimeout(enterChat, 400);
}
function focusAuth(){
  authView.classList.remove('hidden'); chatView.classList.remove('active');
  nameInput.focus();
}
async function resetContext(){
  if(!confirm('Reset konteks? TOPIK arch & history chat akan dibersihkan untuk sesi ini.')) return;
  const r=await fetch('/reset', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:sid, mode:'context'})});
  const j=await r.json();
  toast(j.message); log.innerHTML=''; add(j.demo || 'Konteks direset. Coba tanya lagi.', 'bot');
}
async function resetSession(){
  if(!confirm('Reset sesi penuh? Semua predicate & gaya bahasa akan direset.')) return;
  const r=await fetch('/reset', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:sid, mode:'session'})});
  const j=await r.json();
  toast(j.message); log.innerHTML=''; add('Sesi direset. Halo lagi!', 'bot');
}
async function logout(){
  await fetch('/logout', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:sid})});
  localStorage.removeItem('ars_logged');
  chatView.classList.remove('active'); authView.classList.remove('hidden');
  updateNav(); toast('Logout — sesi tetap tersimpan di log');
}
function openSettings(){
  document.getElementById('setName').value = localStorage.getItem('ars_name')||'';
  document.getElementById('setEmail').value = localStorage.getItem('ars_email')||'';
  document.getElementById('setSid').value = sid;
  // fetch current gaya
  fetch('/settings?session_id='+sid).then(r=>r.json()).then(j=>{
    document.getElementById('setGaya').value = j.gaya_bahasa || '';
  });
  document.getElementById('settingsModal').classList.add('open');
}
function closeSettings(){ document.getElementById('settingsModal').classList.remove('open'); }
async function saveSettings(){
  const name=document.getElementById('setName').value.trim();
  const email=document.getElementById('setEmail').value.trim();
  const gaya=document.getElementById('setGaya').value;
  if(email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){ toast('Email tidak valid'); return; }
  await fetch('/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:sid, name:name||'Tamu', email:email})});
  if(gaya){ await fetch('/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:sid, gaya_bahasa:gaya})}); }
  localStorage.setItem('ars_name', name); localStorage.setItem('ars_email', email);
  updateNav(); closeSettings(); toast('Pengaturan disimpan');
}
async function loadHistory(silent){
  const r=await fetch('/history?session_id='+sid);
  const j=await r.json();
  if(j.history && j.history.length && !silent){
    log.innerHTML='';
    j.history.slice(-40).forEach(h=>{
      const who = h.role==='user' ? 'user' : 'bot';
      add(h.message, who);
    });
    toast('History loaded ('+j.history.length+' pesan)');
  } else if(j.history){
    document.getElementById('historyCount').textContent='history: '+j.history.length+' pesan';
  }
}
document.getElementById('send').onclick=send;
inp.addEventListener('keydown', e=>{ if(e.key==='Enter') send(); });
emailInput.addEventListener('keydown', e=>{ if(e.key==='Enter') enterChat(); });
nameInput.addEventListener('keydown', e=>{ if(e.key==='Enter') emailInput.focus(); });
// init
nameInput.value = userName; emailInput.value = userEmail;
fetch('/health').then(r=>r.json()).then(j=>{
  document.getElementById('catsLine').textContent=j.categories+' AIML categories • Context-aware • Flask';
  document.getElementById('catLabel').textContent=j.categories+' categories';
});
updateNav();
// auto-enter if already logged
if(localStorage.getItem('ars_logged')){
  authView.classList.add('hidden'); chatView.classList.add('active');
  document.getElementById('sessLabel').textContent=sid;
  fetch('/health').then(r=>r.json()).then(j=>{ if(log.children.length===0) add(j.demo,'bot'); loadHistory(true); });
}
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

@app.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    raw_sid = data.get("session_id") or request.headers.get("X-Session-Id") or "_global"
    sid = sanitize_sid(raw_sid)
    # reject traversal/invalid sid
    if raw_sid and raw_sid.strip() and sid != raw_sid.strip():
        return jsonify({"error": "session_id tidak valid (hanya a-z, 0-9, _, -)"}), 400
    name = (data.get("name") or "").strip()[:64]
    email = (data.get("email") or "").strip()[:100]
    if not name and not email:
        return jsonify({"error": "nama atau email wajib"}), 400
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({"error": "email tidak valid"}), 400
    save_user(sid, name or "Tamu", email)
    append_history(sid, "system", f"LOGIN name={name} email={email}", name)
    return jsonify({"ok": True, "session_id": sid, "name": name, "email": email, "user": get_user(sid)})

@app.post("/logout")
def logout():
    data = request.get_json(force=True, silent=True) or {}
    raw = data.get("session_id") or "_global"
    sid = sanitize_sid(raw)
    if raw and raw.strip() and sid != raw.strip():
        return jsonify({"error": "session_id tidak valid"}), 400
    # keep history file for audit, just log event
    append_history(sid, "system", "LOGOUT", get_user(sid).get("name",""))
    return jsonify({"ok": True, "session_id": sid})

@app.post("/reset")
def reset():
    data = request.get_json(force=True, silent=True) or {}
    raw = data.get("session_id") or "_global"
    sid = sanitize_sid(raw)
    if raw and raw.strip() and sid != raw.strip():
        return jsonify({"error": "session_id tidak valid"}), 400
    mode = (data.get("mode") or "context").strip()  # context | session
    if mode not in ("context","session"):
        mode="context"
    clear_session_predicates(sid, mode)
    append_history(sid, "system", f"RESET mode={mode}", get_user(sid).get("name",""))
    demo = get_response("HALO", sid) if mode=="session" else "Konteks arsitektur direset. TOPIK kosong."
    msg = "Konteks direset." if mode=="context" else "Sesi direset total."
    return jsonify({"ok": True, "mode": mode, "message": msg, "demo": demo, "predicate": {"TOPIK": chatbot.getPredicate("TOPIK", sid), "gaya_bahasa": chatbot.getPredicate("gaya_bahasa", sid)}})

@app.get("/history")
def history():
    raw = request.args.get("session_id", "_global")
    sid = sanitize_sid(raw)
    if raw and raw.strip() and sid != raw.strip():
        return jsonify({"error": "session_id tidak valid"}), 400
    hist = read_history(sid, limit=200)
    return jsonify({"session_id": sid, "history": hist, "count": len(hist), "user": get_user(sid)})

@app.get("/settings")
def get_settings():
    raw = request.args.get("session_id", "_global")
    sid = sanitize_sid(raw)
    if raw and raw.strip() and sid != raw.strip():
        return jsonify({"error": "session_id tidak valid"}), 400
    return jsonify({
        "session_id": sid,
        "user": get_user(sid),
        "gaya_bahasa": chatbot.getPredicate("gaya_bahasa", sid),
        "TOPIK": chatbot.getPredicate("TOPIK", sid)
    })

@app.post("/settings")
def post_settings():
    data = request.get_json(force=True, silent=True) or {}
    raw = data.get("session_id") or "_global"
    sid = sanitize_sid(raw)
    if raw and raw.strip() and sid != raw.strip():
        return jsonify({"error": "session_id tidak valid"}), 400
    gaya = (data.get("gaya_bahasa") or "").strip()
    if gaya in ("santai","formal",""):
        if gaya:
            chatbot.setPredicate("gaya_bahasa", gaya, sid)
        return jsonify({"ok": True, "gaya_bahasa": chatbot.getPredicate("gaya_bahasa", sid)})
    return jsonify({"error": "gaya_bahasa harus santai/formal"}), 400

@app.post("/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    msg = (data.get("message") or "").strip()
    if len(msg) > 2000:
        msg = msg[:2000]
    raw = data.get("session_id") or "_global"
    sid = sanitize_sid(raw)
    if raw and raw.strip() and sid != raw.strip():
        return jsonify({"error": "session_id tidak valid"}), 400
    if not msg:
        return jsonify({"response": "Ketik sesuatu dulu ya.", "session_id": sid}), 400
    user = get_user(sid)
    name = user.get("name","")
    # log user
    append_history(sid, "user", msg, name)
    resp = get_response(msg, sid)
    # log bot
    append_history(sid, "bot", resp, name)
    gaya = chatbot.getPredicate("gaya_bahasa", sid)
    topik = chatbot.getPredicate("TOPIK", sid)
    return jsonify({
        "response": resp,
        "session_id": sid,
        "predicate": {"gaya_bahasa": gaya, "TOPIK": topik}
    })

if __name__ == "__main__":
    print(f"[app] categories={chatbot.numCategories()} http://127.0.0.1:5000")
    print(f"[app] data dir: {DATA_DIR} users={USERS_FILE} log={LOG_FILE}")
    app.run(host="127.0.0.1", port=5000, debug=True)

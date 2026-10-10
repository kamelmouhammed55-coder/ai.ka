# -*- coding: utf-8 -*-
# Moka AI v39.0 — مجاني بالكامل — المطور: محمد كامل
import os, re, json, time, hashlib, secrets
import urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from functools import wraps
from collections import defaultdict
from flask import (Flask, request, jsonify, render_template_string,
                   session, redirect, url_for, Response)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=90)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "kameladmin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "KamelDz2026Prime")
ADMIN_KEY      = os.environ.get("ADMIN_KEY",      "mokaadmin2026")
ADMIN_EMAIL    = os.environ.get("ADMIN_EMAIL",    "kamelmouhammed55@gmail.com").lower()
SECRET_SALT    = os.environ.get("SECRET_SALT",    "mokasalt2026kamel")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
OR_MODELS = ["google/gemini-2.0-flash-exp:free",
             "meta-llama/llama-3.3-70b-instruct:free",
             "qwen/qwen-2.5-72b-instruct:free"]

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(DATA_DIR, "users.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")

RATE_LIMITS = defaultdict(list)
SESSIONS = {}

def load_json(p, d):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except: return d

def save_json(p, d):
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception as e: print("[save]", e, flush=True)

def hash_pw(pw):
    return hashlib.sha256((pw + SECRET_SALT).encode()).hexdigest()

USERS = load_json(USERS_FILE, {})
if ADMIN_USERNAME not in USERS:
    USERS[ADMIN_USERNAME] = {"password": hash_pw(ADMIN_PASSWORD),
        "name": "محمد كامل", "role": "admin", "email": ADMIN_EMAIL,
        "created": datetime.now().isoformat()}
    save_json(USERS_FILE, USERS)

DEFAULT_STATS = {"visitors":0,"logins":0,"messages":0,"images_generated":0,
    "voice_used":0,"books_generated":0,"ratings_up":0,"ratings_down":0,
    "modes":{m:0 for m in ["general","write","code","math","translate",
                            "summary","religion","science"]}}
STATS = {**DEFAULT_STATS, **load_json(STATS_FILE, {})}
for m in DEFAULT_STATS["modes"]: STATS["modes"].setdefault(m, 0)
def save_stats(): save_json(STATS_FILE, STATS)
def save_users(): save_json(USERS_FILE, USERS)

def get_ip():
    return (request.headers.get("X-Forwarded-For", request.remote_addr or "?")
            .split(",")[0].strip())

def now_dz(): return datetime.now(timezone(timedelta(hours=1)))

def date_ctx():
    d = now_dz()
    m = ["جانفي","فيفري","مارس","أفريل","ماي","جوان","جويلية","أوت",
         "سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
    return f"{d.day} {m[d.month-1]} {d.year}"

def rate_limit(max_c=100, win=60):
    def dec(fn):
        @wraps(fn)
        def w(*a, **k):
            ip = get_ip(); now = time.time()
            RATE_LIMITS[ip] = [t for t in RATE_LIMITS[ip] if now-t < win]
            if len(RATE_LIMITS[ip]) >= max_c:
                return jsonify({"reply": "أرسلت رسائل كثيرة."}), 429
            RATE_LIMITS[ip].append(now)
            return fn(*a, **k)
        return w
    return dec

def login_required(fn):
    @wraps(fn)
    def w(*a, **k):
        if not session.get("user"):
            if request.path.startswith("/api"):
                return jsonify({"ok": False, "msg": "غير مسجل"}), 401
            return redirect(url_for("index"))
        return fn(*a, **k)
    return w

def search_wiki(q):
    try:
        url = ("https://ar.wikipedia.org/w/api.php?action=query&list=search&srsearch="
               + urllib.parse.quote(q) + "&format=json&utf8=1&srlimit=1")
        r = urllib.request.Request(url, headers={"User-Agent":"Moka/39"})
        with urllib.request.urlopen(r, timeout=8) as x:
            d = json.loads(x.read().decode())
        h = d.get("query",{}).get("search",[])
        if not h: return None
        t = h[0]["title"]
        u2 = ("https://ar.wikipedia.org/api/rest_v1/page/summary/"
              + urllib.parse.quote(t))
        r2 = urllib.request.Request(u2, headers={"User-Agent":"Moka/39"})
        with urllib.request.urlopen(r2, timeout=8) as x2:
            s = json.loads(x2.read().decode())
        return f"({t}): {s.get('extract','')[:500]}" if s.get("extract") else None
    except: return None

# ============ هوية ============
BAD_WORDS = ["ChatGPT","chatgpt","Chat GPT","OpenAI","openai","GPT-4","GPT-3",
    "gpt-4","gpt-3","Gemini","gemini","Anthropic","Claude","claude",
    "DeepSeek","deepseek","Qwen","qwen","Mistral","mistral","Grok","grok",
    "Pollinations","pollinations","Meta AI","meta ai","LLaMA","llama"]

def build_sys(mode, admin=False):
    note = "\n[هذا المستخدم هو محمد كامل مطورك. رحب به: أهلاً محمد! 👑]" if admin else ""
    rules = """قواعد إلزامية:
- أنت Moka AI، طوّرك محمد كامل.
- "من صنعك؟" → "طوّرني محمد كامل."
- ممنوع ذكر: ChatGPT, GPT, OpenAI, Gemini, Claude, Llama, Qwen, DeepSeek, Grok, Mistral.
- لا تعترف بأي شركة أخرى. إذا سُئلت عن نموذجك: "تقنية Moka AI."
- رفض المحتوى الجنسي والعنيف.
- اجب بنفس لغة السؤال.
- استخدم **غامق** و - للقوائم."""
    modes = {"general":"مساعد عام","write":"كاتب محترف","code":"مهندس برمجيات",
        "math":"خبير رياضيات","translate":"مترجم","summary":"خبير تلخيص",
        "religion":"مساعد إسلامي","science":"عالم"}
    return f"أنت {modes.get(mode,'مساعد')}.\n{rules}{note}\nاليوم: {date_ctx()}"

def clean_reply(t):
    t = t.replace("\\(", "").replace("\\)", "")
    t = t.replace("\\[", "").replace("\\]", "")
    t = t.replace("\\sqrt", "√").replace("\\frac", "")
    for w in BAD_WORDS: t = t.replace(w, "Moka AI")
    t = t.replace("Moka AI AI", "Moka AI")
    return t.strip()

# ============ مزودات AI ============
def call_groq(full, mt):
    if not GROQ_API_KEY: return None
    for mdl in GROQ_MODELS:
        try:
            print(f"[Groq] {mdl}", flush=True)
            p = json.dumps({"model":mdl,"messages":full,"temperature":0.7,
                            "max_tokens":mt}).encode()
            r = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=p, headers={"Authorization":f"Bearer {GROQ_API_KEY}",
                "Content-Type":"application/json"}, method="POST")
            with urllib.request.urlopen(r, timeout=45) as x:
                d = json.loads(x.read().decode())
            rep = d["choices"][0]["message"]["content"].strip()
            if rep: print("[Groq] OK", flush=True); return rep
        except Exception as e:
            print(f"[Groq] {type(e).__name__}", flush=True)
    return None

def call_or(full, mt):
    if not OPENROUTER_API_KEY: return None
    for mdl in OR_MODELS:
        try:
            print(f"[OR] {mdl}", flush=True)
            p = json.dumps({"model":mdl,"messages":full,"temperature":0.7,
                            "max_tokens":mt}).encode()
            r = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=p, headers={"Authorization":f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":"application/json",
                "HTTP-Referer":"https://ai-ka.onrender.com",
                "X-Title":"Moka AI"}, method="POST")
            with urllib.request.urlopen(r, timeout=60) as x:
                d = json.loads(x.read().decode())
            rep = d["choices"][0]["message"]["content"].strip()
            if rep: print("[OR] OK", flush=True); return rep
        except Exception as e:
            print(f"[OR] {type(e).__name__}", flush=True)
    return None

def call_poll_post(full, mt=1500):
    try:
        print("[PollPOST] trying", flush=True)
        p = json.dumps({"model":"openai","messages":full,"max_tokens":mt}).encode()
        r = urllib.request.Request("https://text.pollinations.ai/openai",
            data=p, headers={"Content-Type":"application/json",
            "User-Agent":"MokaAI"}, method="POST")
        with urllib.request.urlopen(r, timeout=60) as x:
            d = json.loads(x.read().decode())
        rep = d["choices"][0]["message"]["content"].strip()
        if rep: print("[PollPOST] OK", flush=True); return rep
    except Exception as e:
        print(f"[PollPOST] {type(e).__name__}", flush=True)
    return None

def call_poll_get(prompt_txt):
    try:
        print("[PollGET] trying", flush=True)
        txt = urllib.parse.quote(prompt_txt[:700])
        url = f"https://text.pollinations.ai/{txt}?model=openai&seed={int(time.time())}"
        r = urllib.request.Request(url, headers={"User-Agent":"MokaAI"})
        with urllib.request.urlopen(r, timeout=60) as x:
            rep = x.read().decode("utf-8").strip()
        if rep: print("[PollGET] OK", flush=True); return rep
    except Exception as e:
        print(f"[PollGET] {type(e).__name__}", flush=True)
    return None

def call_ai(msgs, mode="general", mt=1500, admin=False):
    full = [{"role":"system","content":build_sys(mode,admin)}] + msgs[-20:]
    r = call_groq(full, mt)
    if r: return clean_reply(r)
    r = call_or(full, mt)
    if r: return clean_reply(r)
    r = call_poll_post(full, mt)
    if r: return clean_reply(r)
    prompt_txt = full[0]["content"][:250] + "\n\n"
    prompt_txt += "\n".join([m["content"][:200] for m in full[1:]])
    r = call_poll_get(prompt_txt)
    if r: return clean_reply(r)
    return "⚠️ الخدمة مشغولة. حاول بعد دقيقة."

# ============ Auth ============
def verify_google(tok):
    try:
        u = f"https://oauth2.googleapis.com/tokeninfo?id_token={tok}"
        r = urllib.request.Request(u, headers={"User-Agent":"Moka/39"})
        with urllib.request.urlopen(r, timeout=10) as x:
            d = json.loads(x.read().decode())
        return {"email": d.get("email","").lower(),
                "name": d.get("name",""),
                "picture": d.get("picture","")}
    except: return None

@app.route("/api/google-login", methods=["POST"])
def g_login():
    d = request.get_json(silent=True) or {}
    tok = d.get("credential","").strip()
    if not tok: return jsonify({"ok":False,"msg":"no token"}), 400
    info = verify_google(tok)
    if not info or not info["email"]:
        return jsonify({"ok":False,"msg":"token غير صالح"}), 401
    email = info["email"]; name = info["name"] or email.split("@")[0]
    is_admin = (email == ADMIN_EMAIL)
    if email not in USERS:
        USERS[email] = {"name":name, "email":email,
            "picture":info.get("picture",""),
            "role":"admin" if is_admin else "user",
            "created":datetime.now().isoformat(), "provider":"google"}
    else:
        USERS[email]["name"] = name
        USERS[email]["picture"] = info.get("picture","")
    save_users()
    session.permanent = True
    session["user"] = email
    session["role"] = "admin" if is_admin else "user"
    session["name"] = name
    session["picture"] = info.get("picture","")
    session["sid"] = secrets.token_hex(8)
    STATS["logins"] = STATS.get("logins",0)+1
    save_stats()
    return jsonify({"ok":True,"name":name,"email":email,
        "role":session["role"],"is_admin":is_admin})

@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.get_json(silent=True) or {}
    u = d.get("username","").strip(); p = d.get("password","")
    if not u or not p: return jsonify({"ok":False,"msg":"أدخل البيانات"}), 400
    user = USERS.get(u)
    if not user or user.get("password") != hash_pw(p):
        return jsonify({"ok":False,"msg":"بيانات خاطئة"}), 401
    session.permanent = True
    session["user"] = u
    session["role"] = user["role"]
    session["name"] = user["name"]
    session["sid"] = secrets.token_hex(8)
    STATS["logins"] = STATS.get("logins",0)+1
    save_stats()
    return jsonify({"ok":True,"name":user["name"],"role":user["role"]})

@app.route("/api/me")
def api_me():
    if not session.get("user"): return jsonify({"ok":False}), 401
    return jsonify({"ok":True,"name":session.get("name"),
        "email":session.get("user"),"role":session.get("role"),
        "picture":session.get("picture","")})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok":True})

@app.route("/")
def index():
    STATS["visitors"] = STATS.get("visitors",0)+1
    save_stats()
    return render_template_string(HTML_APP, google_client_id=GOOGLE_CLIENT_ID)

@app.route("/manifest.json")
def manifest():
    return Response(MANIFEST, mimetype="application/manifest+json")

@app.route("/sw.js")
def sw():
    r = Response(SW_JS, mimetype="application/javascript")
    r.headers["Service-Worker-Allowed"] = "/"
    return r

@app.route("/icon.svg")
def icon():
    return Response(ICON, mimetype="image/svg+xml")

@app.route("/api/chat", methods=["POST"])
@login_required
@rate_limit(max_c=100, win=60)
def api_chat():
    d = request.get_json(silent=True) or {}
    msg = (d.get("message") or "").strip()
    mode = d.get("mode","general")
    sid = session.get("sid","default")
    is_admin = session.get("role") == "admin"
    if not msg: return jsonify({"reply":"اكتب رسالة."}), 400
    if mode not in ["general","write","code","math","translate",
                    "summary","religion","science"]: mode = "general"
    ml = msg.lower().strip()

    if any(p in ml for p in ["من صنعك","من طورك","من أنشأك","من برمجك",
        "من هو مطورك","من المطور","من صانعك","who made you","who created"]):
        return jsonify({"reply":"طوّرني **محمد كامل** 🇩🇿\n\nأنا **Moka AI**."})
    if any(p in ml for p in ["هل انت chatgpt","are you chatgpt","هل انت gpt","are you gemini"]):
        return jsonify({"reply":"لا، أنا **Moka AI**، من تطوير محمد كامل. لا علاقة لي بأي شركة أخرى."})
    if is_admin:
        if any(p in ml for p in ["مرحبا","السلام عليكم","اهلا","هاي","hi","hello"]):
            return jsonify({"reply":"أهلاً **محمد** 👑\n\nكيف أساعدك؟"})
        if any(p in ml for p in ["من انا","من أنا","هل تعرفني","who am i"]):
            return jsonify({"reply":"أنت **محمد كامل** 👑 مطوّري وصاحب Moka AI."})

    # صورة
    if msg.startswith("/صورة ") or msg.startswith("/image "):
        p = msg.split(" ",1)[1].strip()
        if not p: return jsonify({"reply":"اكتب وصفًا"})
        bad = ["جنس","عاري","إباحي","sex","porn","nude","naked","nsfw",
               "girl","woman","man","امرأة","رجل","فتاة","شاب","شخص"]
        if any(w in p.lower() for w in bad):
            return jsonify({"reply":"🚫 جرّب وصفًا آخر."})
        e = f"beautiful photo of {p}, no people, no humans, 8k"
        STATS["images_generated"] = STATS.get("images_generated",0)+1
        save_stats()
        u = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(e)}"
             f"?width=1024&height=1024&model=flux&safe=true&nologo=true&seed={int(time.time())}")
        return jsonify({"reply":f"🎨 **{p}**","image":u})

    # كتاب
    if msg.startswith("/كتاب ") or msg.startswith("/book "):
        topic = msg.split(" ",1)[1].strip()
        if not topic: return jsonify({"reply":"اكتب موضوعًا"})
        STATS["books_generated"] = STATS.get("books_generated",0)+1
        save_stats()
        toc = call_ai([{"role":"user","content":
            f"اكتب فهرسًا لكتاب عن: {topic}. 3 فصول مع 3 عناوين فرعية."}],
            "write", 500, is_admin)
        out = f"# 📖 {topic}\n\n## 📋 الفهرس\n\n{toc}\n\n---\n\n"
        for t in ["الفصل الأول","الفصل الثاني","الفصل الثالث"]:
            ch = call_ai([{"role":"user","content":
                f"اكتب {t} من كتاب عن: {topic}. 400 كلمة."}], "write", 1500, is_admin)
            out += f"## {t}\n\n{ch}\n\n---\n\n"
        return jsonify({"reply":out})

    # محادثة
    conv = SESSIONS.setdefault(sid, [])
    conv.append({"role":"user","content":msg})
    extra = ""
    if any(k in msg for k in ["ما هو","ما هي","من هو","من هي","عاصمة","تاريخ"]) and len(msg) > 8:
        w = search_wiki(msg)
        if w: extra = f"\n[معلومة]\n{w}"
    if extra: conv.insert(-1, {"role":"system","content":extra})
    if len(conv) > 24: conv[:] = [conv[0]] + conv[-23:]
    reply = call_ai(conv, mode, 1500, is_admin)
    conv.append({"role":"assistant","content":reply})
    STATS["messages"] = STATS.get("messages",0)+1
    STATS["modes"][mode] = STATS["modes"].get(mode,0)+1
    save_stats()
    return jsonify({"reply":reply})

@app.route("/api/clear", methods=["POST"])
@login_required
def clear():
    SESSIONS.pop(session.get("sid","default"), None)
    return jsonify({"ok":True})

@app.route("/api/rate", methods=["POST"])
@login_required
def rate():
    d = request.get_json(silent=True) or {}
    if d.get("rating") == "up": STATS["ratings_up"] = STATS.get("ratings_up",0)+1
    elif d.get("rating") == "down": STATS["ratings_down"] = STATS.get("ratings_down",0)+1
    save_stats(); return jsonify({"ok":True})

@app.route("/api/voice_used", methods=["POST"])
@login_required
def voice_used():
    STATS["voice_used"] = STATS.get("voice_used",0)+1
    save_stats(); return jsonify({"ok":True})

@app.route("/api/tts")
def tts():
    text = request.args.get("text","")[:200]
    lang = request.args.get("lang","ar")
    if not text: return "", 400
    try:
        u = ("https://translate.google.com/translate_tts?ie=UTF-8"
             "&client=tw-ob&tl=" + lang + "&q=" + urllib.parse.quote(text))
        r = urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0",
            "Referer":"https://translate.google.com/"})
        with urllib.request.urlopen(r, timeout=15) as x:
            data = x.read()
        resp = Response(data, mimetype="audio/mpeg")
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
    except: return "", 500

@app.route("/admin")
def admin():
    if not session.get("user"): return "سجل الدخول", 403
    if session.get("role") != "admin": return "للمدير فقط", 403
    if request.args.get("key") != ADMIN_KEY: return "مفتاح مطلوب", 403
    return render_template_string(HTML_ADMIN, stats=STATS, users=USERS)

@app.route("/health")
def health(): return jsonify({"status":"ok"})

MANIFEST = json.dumps({"name":"Moka AI","short_name":"Moka AI",
    "description":"مساعد ذكي من تطوير محمد كامل",
    "start_url":"/","display":"standalone",
    "background_color":"#0a0a14","theme_color":"#dc2626",
    "lang":"ar","dir":"rtl","icons":[
        {"src":"/icon.svg","sizes":"any","type":"image/svg+xml"},
        {"src":"/icon.svg","sizes":"192x192","type":"image/svg+xml","purpose":"maskable"},
        {"src":"/icon.svg","sizes":"512x512","type":"image/svg+xml","purpose":"maskable"}]},
    ensure_ascii=False)

SW_JS = """const C="moka-v39";
self.addEventListener("install",()=>self.skipWaiting());
self.addEventListener("activate",e=>e.waitUntil(self.clients.claim()));
self.addEventListener("fetch",e=>{
  if(e.request.url.includes("/api/"))return;
  if(!e.request.url.startsWith(location.origin))return;
  e.respondWith(fetch(e.request).then(r=>{
    if(r&&r.status===200){const c=r.clone();
      caches.open(C).then(x=>x.put(e.request,c));}
    return r;}).catch(()=>caches.match(e.request)));
});"""

ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<defs>
<linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#ef4444"/><stop offset="100%" stop-color="#991b1b"/>
</linearGradient></defs>
<rect width="512" height="512" rx="128" fill="#0a0a14"/>
<path d="M 128 380 L 128 150 L 200 150 L 256 260 L 312 150 L 384 150 L 384 380
  L 320 380 L 320 250 L 270 340 L 242 340 L 192 250 L 192 380 Z" fill="url(#g1)"/>
<circle cx="400" cy="100" r="22" fill="#fbbf24"/>
<circle cx="400" cy="100" r="10" fill="#fff"/>
</svg>"""

HTML_APP = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Moka AI</title>
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#dc2626">
<link rel="icon" type="image/svg+xml" href="/icon.svg">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
<script src="https://accounts.google.com/gsi/client" async defer></script>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{--bg:#0a0a14;--card:#181828;--card2:#1f1f33;--border:#2a2a45;
--text:#eaeaf5;--muted:#8a8aa8;--red:#dc2626;
--grad:linear-gradient(135deg,#dc2626,#1e3a8a)}
body{font-family:Cairo,system-ui,sans-serif;background:var(--bg);color:var(--text);
min-height:100vh;font-size:14px}
#login{position:fixed;inset:0;z-index:99;background:var(--bg);display:flex;
flex-direction:column;align-items:center;justify-content:center;padding:20px;gap:14px}
.logo{width:70px;height:70px}
.title{font-size:26px;font-weight:900;background:var(--grad);
-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--muted);font-size:12px;margin-top:-4px}
.gbox{display:flex;justify-content:center;width:100%}
.manual-btn{background:transparent;border:1px solid var(--border);color:var(--muted);
padding:8px 16px;border-radius:9px;cursor:pointer;font-family:inherit;font-size:12px}
.manual-form{width:100%;max-width:320px;display:none;flex-direction:column;gap:8px}
.manual-form.on{display:flex}
.manual-form input{padding:11px 14px;border-radius:10px;border:1.5px solid var(--border);
background:var(--card);color:var(--text);font-size:14px;font-family:inherit;outline:none}
.manual-form button{padding:11px;border-radius:10px;border:none;background:var(--grad);
color:#fff;font-size:14px;font-weight:700;font-family:inherit;cursor:pointer}
.err{color:#f87171;font-size:11px;min-height:14px;text-align:center}
#app{display:none;min-height:100vh;flex-direction:column}
#app.on{display:flex}
.hd{display:flex;align-items:center;gap:8px;padding:10px 14px;background:var(--card);
border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10}
.hd-logo{width:30px;height:30px;border-radius:8px}
.hd h1{font-size:14px;font-weight:800;background:var(--grad);
-webkit-background-clip:text;background-clip:text;color:transparent}
.hd .sub{font-size:9px;color:var(--muted)}
.hd-actions{margin-inline-start:auto;display:flex;gap:4px}
.hd-actions button{width:32px;height:32px;border-radius:9px;border:none;
background:var(--card2);color:var(--text);cursor:pointer;font-size:14px}
.hd-actions button.voice-on{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff}
#ch{flex:1;overflow-y:auto;padding:12px 12px 190px;display:flex;flex-direction:column;gap:10px}
.welcome{display:flex;flex-direction:column;align-items:center;gap:12px;
text-align:center;padding:30px 16px}
.welcome img{width:60px;height:60px}
.welcome h2{font-size:18px;font-weight:800}
.welcome p{color:var(--muted);font-size:12px;max-width:260px;line-height:1.6}
.chips{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;max-width:340px;width:100%}
.chips button{padding:10px;border-radius:10px;border:1px solid var(--border);
background:var(--card);color:var(--text);font-family:inherit;font-size:11px;
font-weight:600;cursor:pointer}
.chips button:hover{border-color:var(--red)}
.mw{display:flex;gap:6px;max-width:92%}
.mw.u{align-self:flex-start;flex-direction:row-reverse}
.mw.b{align-self:flex-end}
.avt{width:28px;height:28px;border-radius:9px;display:grid;place-items:center;
font-weight:800;font-size:11px;color:#fff;flex-shrink:0;overflow:hidden}
.mw.u .avt{background:var(--grad)}
.mw.b .avt{background:linear-gradient(135deg,#06b6d4,#8b5cf6)}
.avt img{width:100%;height:100%;object-fit:cover}
.m{padding:10px 14px;border-radius:14px;line-height:1.7;font-size:13px;
word-wrap:break-word;overflow-wrap:anywhere}
.u .m{background:var(--grad);color:#fff;border-top-right-radius:4px}
.b .m{background:var(--card2);color:var(--text);border:1px solid var(--border);
border-top-left-radius:4px}
.b .m h1,.b .m h2,.b .m h3{margin:8px 0 4px;font-weight:700}
.b .m h1,.b .m h2{color:#ef4444}
.b .m h3{color:#3b82f6}
.b .m strong{color:#ef4444}
.b .m ul,.b .m ol{padding-inline-start:1.2rem;margin:4px 0}
.b .m pre{background:#000;padding:10px;border-radius:8px;overflow-x:auto;
direction:ltr;text-align:left;margin:6px 0;font-size:11px;font-family:monospace}
.b .m code{background:rgba(220,38,38,.2);padding:2px 5px;border-radius:4px;
font-family:monospace;font-size:.9em;direction:ltr}
.b .m pre code{background:transparent;padding:0;color:inherit}
.b .m img{max-width:100%;border-radius:10px;margin-top:6px;display:block}
.acts{display:flex;gap:3px;margin-top:4px;flex-wrap:wrap}
.acts button{padding:3px 8px;border-radius:6px;border:1px solid var(--border);
background:transparent;color:var(--muted);font-family:inherit;font-size:10px;cursor:pointer}
.acts button.active{background:var(--red);color:#fff;border-color:var(--red)}
.tp{display:flex;gap:3px;padding:10px 14px}
.tp span{width:6px;height:6px;border-radius:50%;background:var(--red);animation:b 1.2s infinite}
.tp span:nth-child(2){animation-delay:.15s}
.tp span:nth-child(3){animation-delay:.3s}
@keyframes b{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-5px);opacity:1}}
.input-area{position:fixed;bottom:0;left:0;right:0;padding:8px 10px 12px;
background:linear-gradient(to top,var(--bg) 70%,transparent);z-index:5}
.modes{display:flex;gap:4px;margin-bottom:6px;overflow-x:auto;padding-bottom:3px;scrollbar-width:none}
.modes::-webkit-scrollbar{display:none}
.modes button{background:var(--card);border:1px solid var(--border);color:var(--muted);
padding:6px 11px;border-radius:9px;font-size:11px;font-family:inherit;font-weight:600;
cursor:pointer;white-space:nowrap}
.modes button.on{background:var(--grad);color:#fff;border-color:transparent}
.inp-box{display:flex;align-items:flex-end;gap:5px;background:var(--card);
border:1px solid var(--border);border-radius:18px;padding:5px}
.inp-box:focus-within{border-color:var(--red)}
#i{flex:1;resize:none;border:none;outline:none;background:transparent;color:var(--text);
padding:8px 10px;font-family:inherit;font-size:13px;max-height:110px;line-height:1.5}
#i::placeholder{color:var(--muted)}
.ib{width:36px;height:36px;border-radius:10px;border:none;font-size:15px;
cursor:pointer;display:grid;place-items:center;flex-shrink:0}
#mic{background:var(--card2);color:var(--text)}
#mic.rec{background:#dc2626;color:#fff}
#s{background:var(--grad);color:#fff}
#s:disabled{opacity:.4}
.modal{position:fixed;inset:0;background:rgba(10,10,20,.95);backdrop-filter:blur(10px);
z-index:200;display:none;flex-direction:column;padding:20px;overflow-y:auto}
.modal.on{display:flex}
.modal-in{max-width:400px;margin:auto;width:100%;background:var(--card);
border-radius:16px;padding:20px;border:1px solid var(--border);position:relative}
.modal h2{font-size:16px;font-weight:800;margin-bottom:12px;
background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.close{position:absolute;top:12px;left:12px;width:34px;height:34px;border-radius:9px;
border:none;background:var(--card2);color:var(--text);font-size:16px;cursor:pointer}
.set{margin-bottom:10px}
.set label{font-size:11px;color:var(--muted);display:block;margin-bottom:5px;font-weight:600}
.set select{width:100%;padding:10px;border-radius:9px;border:1px solid var(--border);
background:var(--card2);color:var(--text);font-family:inherit;font-size:13px;outline:none}
.btn-act{padding:11px;border-radius:9px;border:none;background:var(--grad);color:#fff;
font-family:inherit;font-weight:700;cursor:pointer;width:100%;margin-top:6px;font-size:13px}
</style>
</head>
<body>

<div id="login">
  <img src="/icon.svg" class="logo" alt="Moka">
  <div class="title">Moka AI</div>
  <div class="sub">من تطوير محمد كامل</div>
  <div class="gbox">
    <div id="g_id_onload" data-client_id="{{ google_client_id }}"
         data-callback="onGoogleLogin" data-auto_prompt="false"></div>
    <div class="g_id_signin" data-type="standard" data-size="large"
         data-theme="filled_black" data-text="signin_with"
         data-shape="pill" data-locale="ar"></div>
  </div>
  <button class="manual-btn" onclick="toggleManual()">🔑 دخول احتياطي</button>
  <div class="manual-form" id="manualForm">
    <input id="mu" placeholder="اسم المستخدم">
    <input id="mp" type="password" placeholder="كلمة السر">
    <button onclick="doManualLogin()">دخول</button>
  </div>
  <div class="err" id="err"></div>
</div>

<div id="app">
  <div class="hd">
    <img src="/icon.svg" class="hd-logo" alt="M">
    <div>
      <h1>Moka AI</h1>
      <div class="sub" id="who">—</div>
    </div>
    <div class="hd-actions">
      <button id="vb" onclick="toggleVoice()" title="الصوت">🔇</button>
      <button onclick="menu()" title="القائمة">☰</button>
    </div>
  </div>

  <div id="ch"></div>

  <div class="input-area">
    <div class="modes">
      <button class="on" data-m="general" onclick="sw('general')">💬 عامة</button>
      <button data-m="write" onclick="sw('write')">✍️ كتابة</button>
      <button data-m="code" onclick="sw('code')">💻 برمجة</button>
      <button data-m="math" onclick="sw('math')">📐 رياضيات</button>
      <button data-m="translate" onclick="sw('translate')">🌍 ترجمة</button>
      <button data-m="summary" onclick="sw('summary')">📝 ملخص</button>
      <button data-m="religion" onclick="sw('religion')">🕌 دين</button>
      <button data-m="science" onclick="sw('science')">🔬 علوم</button>
    </div>
    <div class="inp-box">
      <button class="ib" id="mic" onclick="toggleMic()">🎤</button>
      <textarea id="i" rows="1" placeholder="اكتب رسالتك..."></textarea>
      <button class="ib" id="s" onclick="send()">➤</button>
    </div>
  </div>
</div>

<div class="modal" id="settingsModal">
  <div class="modal-in">
    <button class="close" onclick="closeModal('settingsModal')">✕</button>
    <h2>⚙️ الإعدادات</h2>
    <div class="set">
      <label>محرك الصوت</label>
      <select id="engineSelect">
        <option value="google">🔊 Google</option>
        <option value="browser">🔈 المتصفح</option>
      </select>
    </div>
    <div class="set">
      <label>اللهجة</label>
      <select id="langSelect">
        <option value="ar">🌍 فصحى</option>
        <option value="ar-SA">🇸🇦 سعودية</option>
        <option value="ar-EG">🇪🇬 مصرية</option>
        <option value="ar-DZ">🇩🇿 جزائرية</option>
      </select>
    </div>
    <button class="btn-act" onclick="testVoice()">🎧 تجربة الصوت</button>
    <button class="btn-act" style="background:var(--card2);margin-top:8px"
      onclick="fetch('/api/logout',{method:'POST'}).then(()=>location.reload())">
      🚪 تسجيل الخروج
    </button>
  </div>
</div>

<script>
let mode="general", history=[], isAdmin=false, isSending=false;
let userName="", userPic="", voiceEnabled=false, currentAudio=null;

const ch=document.getElementById("ch"), i=document.getElementById("i"),
      s=document.getElementById("s"), mic=document.getElementById("mic"),
      vb=document.getElementById("vb"), errEl=document.getElementById("err");

window.addEventListener("load", () => {
  fetch("/api/me").then(r=>r.json()).then(d=>{
    if(d.ok) enterApp(d.name, d.role, d.picture||"");
  }).catch(()=>{});
});

function toggleManual(){document.getElementById("manualForm").classList.toggle("on")}
function closeModal(id){document.getElementById(id).classList.remove("on")}
function openModal(id){document.getElementById(id).classList.add("on")}

async function doManualLogin(){
  const u = document.getElementById("mu").value.trim();
  const p = document.getElementById("mp").value;
  if(!u || !p){errEl.textContent="املأ الحقول"; return}
  try{
    const r = await fetch("/api/login", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({username:u, password:p})});
    const d = await r.json();
    if(!d.ok){errEl.textContent = d.msg || "خطأ"; return}
    enterApp(d.name, d.role, "");
  }catch(e){errEl.textContent = "تعذر الاتصال"}
}

function onGoogleLogin(resp){
  fetch("/api/google-login", {method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({credential: resp.credential})})
  .then(r=>r.json()).then(d=>{
    if(!d.ok){errEl.textContent = d.msg || "فشل"; return}
    enterApp(d.name, d.role, d.picture);
  }).catch(()=>{errEl.textContent="تعذر الاتصال"});
}

function esc(t){return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function md(t){
  let h=esc(t);
  h=h.replace(/```(\w*)\n([\s\S]*?)```/g,(_,l,c)=>`<pre><code>${c}</code></pre>`);
  h=h.replace(/^### (.+)$/gm,"<h3>$1</h3>");
  h=h.replace(/^## (.+)$/gm,"<h2>$1</h2>");
  h=h.replace(/^# (.+)$/gm,"<h1>$1</h1>");
  h=h.replace(/`([^`]+)`/g,"<code>$1</code>");
  h=h.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>");
  h=h.replace(/^\s*[-*] (.+)$/gm,"<li>$1</li>");
  h=h.replace(/(<li>[\s\S]*?<\/li>)/g,m=>`<ul>${m}</ul>`);
  h=h.replace(/\n/g,"<br>");
  return h;
}

function addMsg(text, who, img){
  const w=document.createElement("div"); w.className="mw "+who;
  const av=document.createElement("div"); av.className="avt";
  if(who==="u" && userPic) av.innerHTML='<img src="'+userPic+'" alt="">';
  else av.textContent = who==="u" ? (userName||"أ").charAt(0).toUpperCase() : "M";
  const m=document.createElement("div"); m.className="m";
  m.innerHTML = who==="b" ? md(text) : esc(text);
  if(img){const im=document.createElement("img"); im.src=img; m.appendChild(im);}
  const wrap=document.createElement("div"); wrap.appendChild(m);
  if(who==="b"){
    const a=document.createElement("div"); a.className="acts";
    const c1=document.createElement("button"); c1.textContent="📋";
    c1.onclick=()=>{navigator.clipboard.writeText(text);c1.textContent="✅";
      setTimeout(()=>c1.textContent="📋",1200)};
    const c2=document.createElement("button"); c2.textContent="🔊";
    c2.onclick=()=>speak(text,true);
    const up=document.createElement("button"); up.textContent="👍";
    up.onclick=()=>{fetch("/api/rate",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({rating:"up"})}); up.classList.add("active")};
    const dn=document.createElement("button"); dn.textContent="👎";
    dn.onclick=()=>{fetch("/api/rate",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({rating:"down"})}); dn.classList.add("active")};
    a.appendChild(c1); a.appendChild(c2); a.appendChild(up); a.appendChild(dn);
    wrap.appendChild(a);
  }
  w.appendChild(av); w.appendChild(wrap);
  ch.appendChild(w); ch.scrollTop=ch.scrollHeight;
}

function typ(){
  const w=document.createElement("div"); w.className="mw b"; w.id="tp";
  w.innerHTML='<div class="avt">M</div><div class="m tp"><span></span><span></span><span></span></div>';
  ch.appendChild(w); ch.scrollTop=ch.scrollHeight; return w;
}

function welcome(){
  const gr = isAdmin ? "أهلاً "+userName+" 👑" : "مرحبًا "+userName;
  ch.innerHTML='<div class="welcome"><img src="/icon.svg" alt="Moka">'+
    '<h2>'+gr+'</h2>'+
    '<p>أنا Moka AI، مساعدك الذكي من تطوير محمد كامل.</p>'+
    '<div class="chips">'+
    '<button onclick="quick(\'من صنعك؟\')">👋 من صنعك؟</button>'+
    '<button onclick="quick(\'/كتاب تاريخ الجزائر\')">📚 كتاب</button>'+
    '<button onclick="quick(\'اكتب كود Python\')">💻 كود</button>'+
    '<button onclick="quick(\'/صورة غروب\')">🎨 صورة</button>'+
    '</div></div>';
}

function quick(t){i.value=t; send()}

function toggleVoice(){
  voiceEnabled = !voiceEnabled;
  vb.classList.toggle("voice-on", voiceEnabled);
  vb.innerHTML = voiceEnabled?"🔊":"🔇";
  if(voiceEnabled){fetch("/api/voice_used",{method:"POST"}); speak("تم التفعيل",true);}
  else {if(currentAudio){currentAudio.pause();currentAudio=null}
    if(window.speechSynthesis) speechSynthesis.cancel();}
}

function clean(t){
  return t.replace(/```[\s\S]*?```/g,"").replace(/`([^`]+)`/g,"$1")
          .replace(/[#*_]/g,"").replace(/\n+/g," ").slice(0,190);
}

function speak(text, force){
  if(!voiceEnabled && !force) return;
  const c = clean(text); if(!c) return;
  const lng = document.getElementById("langSelect").value;
  const eng = document.getElementById("engineSelect").value;
  if(currentAudio){currentAudio.pause();currentAudio=null}
  if(window.speechSynthesis) speechSynthesis.cancel();
  if(eng === "google"){
    currentAudio = new Audio("/api/tts?lang="+lng+"&text="+encodeURIComponent(c));
    currentAudio.play().catch(()=>{});
  } else {
    if(!("speechSynthesis" in window)) return;
    const u = new SpeechSynthesisUtterance(c); u.lang = lng;
    speechSynthesis.speak(u);
  }
}

let rec = null;
function toggleMic(){
  if(!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)){
    alert("المتصفح لا يدعم المايك"); return;
  }
  if(rec){rec.stop();return}
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  rec = new SR(); rec.lang = document.getElementById("langSelect").value;
  rec.onstart = ()=>mic.classList.add("rec");
  rec.onend = ()=>{mic.classList.remove("rec"); rec=null};
  rec.onresult = (e)=>{i.value += (i.value?" ":"") + e.results[0][0].transcript; i.focus()};
  rec.start();
}

function enterApp(name, role, pic){
  userName = name; userPic = pic||""; isAdmin = (role==="admin");
  document.getElementById("login").style.display="none";
  document.getElementById("app").classList.add("on");
  document.getElementById("who").textContent = (isAdmin?"👑 ":"") + name;
  try{
    const saved = localStorage.getItem("moka_chat");
    if(saved && JSON.parse(saved).length > 2){
      history = JSON.parse(saved);
      history.forEach(m => addMsg(m.content, m.role==="user"?"u":"b"));
    } else { welcome(); }
  }catch(e){welcome()}
  i.focus();
}

async function send(){
  const t = i.value.trim();
  if(!t || isSending) return;
  const w = ch.querySelector(".welcome"); if(w) ch.innerHTML="";
  addMsg(t,"u"); history.push({role:"user",content:t});
  i.value=""; i.style.height="auto";
  isSending=true; s.disabled=true;
  const tp=typ();
  try{
    const r = await fetch("/api/chat",{method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:t,mode:mode,history:history.slice(0,-1)})});
    const d = await r.json();
    tp.remove();
    addMsg(d.reply||"لا يوجد رد.","b",d.image||null);
    history.push({role:"assistant",content:d.reply||""});
    try{localStorage.setItem("moka_chat", JSON.stringify(history.slice(-30)));}catch(e){}
    if(voiceEnabled && !d.image) speak(d.reply);
  }catch(e){
    tp.remove(); addMsg("تعذر الاتصال","b");
  }finally{
    isSending=false; s.disabled=false; i.focus();
  }
}

function sw(m){
  mode=m;
  document.querySelectorAll(".modes button").forEach(b=>b.classList.toggle("on", b.dataset.m===m));
}

function testVoice(){
  const o=voiceEnabled; voiceEnabled=true;
  speak("مرحبًا، أنا Moka AI من تطوير محمد كامل",true);
  setTimeout(()=>voiceEnabled=o,100);
}

function menu(){
  const a=["مسح المحادثة","تصدير المحادثة","الإعدادات"];
  if(isAdmin) a.push("لوحة الإدارة");
  const c = prompt("اختر:\n"+a.map((x,n)=>(n+1)+". "+x).join("\n"));
  const x = a[parseInt(c)-1]; if(!x) return;
  if(x==="مسح المحادثة"){
    if(confirm("مسح؟")){
      history=[]; localStorage.removeItem("moka_chat");
      fetch("/api/clear",{method:"POST"}); welcome();
    }
  } else if(x==="تصدير المحادثة"){
    const txt = history.map(m=>`[${m.role==="user"?"أنا":"Moka"}] ${m.content}`).join("\n\n");
    const bl = new Blob([txt],{type:"text/plain;charset=utf-8"});
    const a2 = document.createElement("a"); a2.href = URL.createObjectURL(bl);
    a2.download = "moka-"+Date.now()+".txt"; a2.click();
  } else if(x==="الإعدادات"){openModal("settingsModal")}
  else if(x==="لوحلة الإدارة"){
    const k = prompt("مفتاح اللوحة:"); if(k) window.open("/admin?key="+k,"_blank");
  }
}

i.addEventListener("keydown",e=>{
  if(e.key==="Enter" && !e.shiftKey){e.preventDefault(); send()}
});
i.addEventListener("input",()=>{
  i.style.height="auto"; i.style.height = Math.min(i.scrollHeight,110)+"px";
});

if("serviceWorker" in navigator){
  window.addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}));
}
</script>
</body>
</html>'''


HTML_ADMIN = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>لوحة الإدارة</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap" rel="stylesheet">
<style>
body{font-family:Cairo;background:#0a0a14;color:#eaeaf5;padding:16px;font-size:13px}
h1{font-size:20px;color:#ef4444;margin-bottom:4px}
.sub{color:#8a8aa8;font-size:11px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:10px;margin-bottom:16px}
.card{background:#181828;border:1px solid #2a2a45;border-radius:12px;padding:12px;text-align:center}
.num{font-size:22px;font-weight:900;color:#ef4444}
.lbl{font-size:10px;color:#8a8aa8;margin-top:3px}
.box{background:#181828;border:1px solid #2a2a45;border-radius:12px;padding:14px;margin-bottom:12px}
.box h2{font-size:14px;font-weight:800;margin-bottom:8px}
.row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #2a2a45;font-size:12px;gap:6px;flex-wrap:wrap}
.row:last-child{border-bottom:none}
.meta{color:#8a8aa8;font-size:10px}
.badge{background:#dc2626;color:#fff;padding:2px 6px;border-radius:5px;font-size:9px;font-weight:800}
.badge.user{background:#22c55e}
a.back{color:#ef4444;text-decoration:none;font-weight:800;font-size:12px}
</style>
</head>
<body>
<a href="/" class="back">← رجوع</a>
<h1>👑 لوحة الإدارة</h1>
<div class="sub">Moka AI v39.0 — مجاني بالكامل</div>

<div class="grid">
  <div class="card"><div class="num">{{ stats.visitors }}</div><div class="lbl">زيارات</div></div>
  <div class="card"><div class="num">{{ stats.logins }}</div><div class="lbl">دخول</div></div>
  <div class="card"><div class="num">{{ stats.messages }}</div><div class="lbl">رسائل</div></div>
  <div class="card"><div class="num">{{ stats.images_generated }}</div><div class="lbl">صور</div></div>
  <div class="card"><div class="num">{{ stats.books_generated }}</div><div class="lbl">كتب</div></div>
  <div class="card"><div class="num">{{ stats.voice_used }}</div><div class="lbl">صوت</div></div>
  <div class="card"><div class="num">{{ stats.ratings_up }}</div><div class="lbl">👍</div></div>
  <div class="card"><div class="num">{{ users|length }}</div><div class="lbl">مستخدمين</div></div>
</div>

<div class="box">
  <h2>👥 المستخدمون</h2>
  {% for u, info in users.items() %}
  <div class="row">
    <span>{{ info.name }} <span class="meta">({{ u }})</span></span>
    <span class="badge {{ 'user' if info.role != 'admin' else '' }}">{{ info.role }}</span>
  </div>
  {% endfor %}
</div>
</body>
</html>'''


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("="*50, flush=True)
    print("Moka AI v39.0 - مجاني بالكامل", flush=True)
    print("Admin: " + ADMIN_EMAIL, flush=True)
    print("Google: " + ("OK" if GOOGLE_CLIENT_ID else "MISSING"), flush=True)
    print("Groq: " + ("OK" if GROQ_API_KEY else "MISSING"), flush=True)
    print("OpenRouter: " + ("OK" if OPENROUTER_API_KEY else "MISSING"), flush=True)
    print("Pollinations: Always ON", flush=True)
    print("="*50, flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)
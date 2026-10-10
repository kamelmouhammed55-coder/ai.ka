# -*- coding: utf-8 -*-
# ============================================================
#  Moka AI v35.0 - Final
#  المطور: محمد كامل
# ============================================================

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

ADMIN_USERNAME   = os.environ.get("ADMIN_USERNAME", "kameladmin")
ADMIN_PASSWORD   = os.environ.get("ADMIN_PASSWORD", "KamelDz2026Prime")
ADMIN_KEY        = os.environ.get("ADMIN_KEY",      "mokaadmin2026")
ADMIN_EMAIL      = os.environ.get("ADMIN_EMAIL",    "kamelmouhammed55@gmail.com").lower()
SECRET_SALT      = os.environ.get("SECRET_SALT",    "mokasalt2026kamel")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

OR_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "deepseek/deepseek-chat:free",
]

DATA_DIR     = os.path.dirname(os.path.abspath(__file__))
USERS_FILE   = os.path.join(DATA_DIR, "users.json")
STATS_FILE   = os.path.join(DATA_DIR, "stats.json")

RATE_LIMITS = defaultdict(list)
SESSIONS    = {}

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[save] " + str(e), flush=True)

def hash_pw(pw):
    return hashlib.sha256((pw + SECRET_SALT).encode("utf-8")).hexdigest()

USERS = load_json(USERS_FILE, {})
if ADMIN_USERNAME not in USERS:
    USERS[ADMIN_USERNAME] = {
        "password": hash_pw(ADMIN_PASSWORD),
        "name": "محمد كامل",
        "role": "admin",
        "email": ADMIN_EMAIL,
        "created": datetime.now().isoformat(),
    }
    save_json(USERS_FILE, USERS)

DEFAULT_STATS = {
    "visitors": 0, "logins": 0, "messages": 0,
    "images_generated": 0, "voice_used": 0, "books_generated": 0,
    "modes": {m: 0 for m in ["general","write","code","math",
                              "translate","summary","religion","science"]},
    "recent": [],
    "started_at": datetime.now().isoformat(),
}
STATS = {**DEFAULT_STATS, **load_json(STATS_FILE, {})}
for m in DEFAULT_STATS["modes"]:
    STATS["modes"].setdefault(m, 0)

def save_stats(): save_json(STATS_FILE, STATS)
def save_users(): save_json(USERS_FILE, USERS)

def get_ip():
    return (request.headers.get("X-Forwarded-For", request.remote_addr or "?")
            .split(",")[0].strip())

def now_algeria():
    return datetime.now(timezone(timedelta(hours=1)))

def date_context():
    d = now_algeria()
    months = ["جانفي","فيفري","مارس","أفريل","ماي","جوان",
              "جويلية","أوت","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
    days = ["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
    return f"اليوم: {days[d.weekday()]} {d.day} {months[d.month-1]} {d.year}"

def rate_limit(max_calls=30, window=60):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            ip = get_ip()
            now = time.time()
            RATE_LIMITS[ip] = [t for t in RATE_LIMITS[ip] if now - t < window]
            if len(RATE_LIMITS[ip]) >= max_calls:
                return jsonify({"reply": "أرسلت رسائل كثيرة."}), 429
            RATE_LIMITS[ip].append(now)
            return fn(*a, **kw)
        return wrapper
    return deco

def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("user"):
            if request.path.startswith("/api"):
                return jsonify({"ok": False, "msg": "غير مسجل"}), 401
            return redirect(url_for("index"))
        return fn(*a, **kw)
    return wrapper

def search_wikipedia(query):
    try:
        url = ("https://ar.wikipedia.org/w/api.php?action=query&list=search&srsearch="
               + urllib.parse.quote(query) + "&format=json&utf8=1&srlimit=1")
        req = urllib.request.Request(url, headers={"User-Agent": "MokaAI/35"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        hits = data.get("query", {}).get("search", [])
        if not hits: return None
        title = hits[0]["title"]
        sum_url = ("https://ar.wikipedia.org/api/rest_v1/page/summary/"
                   + urllib.parse.quote(title))
        req2 = urllib.request.Request(sum_url, headers={"User-Agent": "MokaAI/35"})
        with urllib.request.urlopen(req2, timeout=8) as r2:
            sdata = json.loads(r2.read().decode("utf-8"))
        extract = sdata.get("extract", "")
        return f"معلومات ({title}):\n{extract[:600]}" if extract else None
    except Exception:
        return None

def build_system(mode, is_admin=False):
    admin_note = ""
    if is_admin:
        admin_note = """
【مهم - هذا المستخدم هو محمد كامل مطورك】
- إذا سلم عليك، رحب به بحرارة: "أهلاً محمد! كيف حالك اليوم؟ 🎉"
- إذا سألك "هل تعرفني؟" قل: "أنت محمد كامل، مطوّري وصاحب المشروع 👑"
- عامل باقي الأسئلة بشكل طبيعي.
"""
    rules = """
أنت Moka AI، مساعد ذكي عربي طوّره محمد كامل.
- إذا سئلت "من صنعك؟" قل: "طوّّنِي محمد كامل."
- ممنوع ذكر أي شركة أو نموذج آخر.
- ممنوع المحتوى الجنسي أو العنيف.
- استخدم **غامق** و - للقوائم و # للعناوين.
- اجب بنفس لغة السؤال.
- كن مختصرًا وواضحًا.
"""
    modes = {
        "general": "أنت مساعد عام.",
        "write": "أنت كاتب محترف.",
        "code": "أنت مهندس برمجيات.",
        "math": "أنت خبير رياضيات.",
        "translate": "أنت مترجم محترف.",
        "summary": "أنت خبير تلخيص.",
        "religion": "أنت مساعد علوم إسلامية.",
        "science": "أنت عالم.",
    }
    return (modes.get(mode, modes["general"]) + "\n\n"
            + rules + admin_note + "\n" + date_context())

def clean_reply(t):
    t = t.replace("\\(", "").replace("\\)", "")
    t = t.replace("\\[", "").replace("\\]", "")
    t = t.replace("\\sqrt", "√").replace("\\frac", "")
    return t.strip()

def call_groq(full, max_tokens):
    if not GROQ_API_KEY:
        return None
    for model in GROQ_MODELS:
        try:
            print(f"[Groq] {model}", flush=True)
            payload = json.dumps({
                "model": model, "messages": full,
                "temperature": 0.7, "max_tokens": max_tokens,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                         "Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.loads(r.read().decode("utf-8"))
            reply = data["choices"][0]["message"]["content"].strip()
            if reply:
                print("[Groq] OK", flush=True)
                return reply
        except Exception as e:
            print(f"[Groq] {type(e).__name__}", flush=True)
            continue
    return None

def call_openrouter(full, max_tokens):
    if not OPENROUTER_API_KEY:
        return None
    for model in OR_MODELS:
        try:
            print(f"[OR] {model}", flush=True)
            payload = json.dumps({
                "model": model, "messages": full,
                "temperature": 0.7, "max_tokens": max_tokens,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}",
                         "Content-Type": "application/json",
                         "HTTP-Referer": "https://ai-ka.onrender.com",
                         "X-Title": "Moka AI"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            reply = data["choices"][0]["message"]["content"].strip()
            if reply:
                print("[OR] OK", flush=True)
                return reply
        except Exception as e:
            print(f"[OR] {type(e).__name__}", flush=True)
            continue
    return None

def call_ai(messages, mode="general", max_tokens=2000, is_admin=False):
    full = [{"role": "system", "content": build_system(mode, is_admin)}] + messages[-20:]
    reply = call_groq(full, max_tokens)
    if reply:
        return clean_reply(reply)
    reply = call_openrouter(full, max_tokens)
    if reply:
        return clean_reply(reply)
    return "⚠️ المزودان مشغولان. حاول بعد قليل."

def generate_book(topic, is_admin=False):
    book = {"toc": "", "intro": "", "chapters": []}
    book["toc"] = call_ai([{"role": "user", "content":
        f"اكتب فهرسًا لكتاب عن: {topic}. 3 فصول مع 3 عناوين فرعية."}],
        mode="write", max_tokens=600, is_admin=is_admin)
    book["intro"] = call_ai([{"role": "user", "content":
        f"اكتب مقدمة احترافية لكتاب عن: {topic}. 3 فقرات."}],
        mode="write", max_tokens=800, is_admin=is_admin)
    for ct in ["الفصل الأول","الفصل الثاني","الفصل الثالث"]:
        ch = call_ai([{"role": "user", "content":
            f"اكتب {ct} من كتاب عن: {topic}. 500 كلمة."}],
            mode="write", max_tokens=1800, is_admin=is_admin)
        book["chapters"].append({"title": ct, "content": ch})
    return book

# ============ Google Auth ============
def verify_google_token(id_token):
    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        req = urllib.request.Request(url, headers={"User-Agent": "MokaAI/35"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {
            "email": data.get("email", "").lower(),
            "name": data.get("name", ""),
            "picture": data.get("picture", ""),
        }
    except Exception as e:
        print(f"[Google] {e}", flush=True)
        return None

@app.route("/api/google-login", methods=["POST"])
def api_google_login():
    data = request.get_json(silent=True) or {}
    id_token = data.get("credential", "").strip()
    if not id_token:
        return jsonify({"ok": False, "msg": "no token"}), 400
    info = verify_google_token(id_token)
    if not info or not info["email"]:
        return jsonify({"ok": False, "msg": "token غير صالح"}), 401

    email = info["email"]
    name = info["name"] or email.split("@")[0]
    is_admin = (email == ADMIN_EMAIL)

    if email not in USERS:
        USERS[email] = {
            "name": name, "email": email,
            "picture": info.get("picture", ""),
            "role": "admin" if is_admin else "user",
            "created": datetime.now().isoformat(),
            "provider": "google",
        }
    else:
        USERS[email]["name"] = name
        USERS[email]["picture"] = info.get("picture", "")
    save_users()

    session["user"] = email
    session["role"] = "admin" if is_admin else "user"
    session["name"] = name
    session["picture"] = info.get("picture", "")
    session["sid"] = secrets.token_hex(8)

    STATS["logins"] = STATS.get("logins", 0) + 1
    save_stats()

    return jsonify({
        "ok": True, "name": name, "email": email,
        "role": "admin" if is_admin else "user",
        "is_admin": is_admin,
    })

# ============ الدخول اليدوي (احتياطي) ============
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    u = data.get("username", "").strip()
    p = data.get("password", "")
    if not u or not p:
        return jsonify({"ok": False, "msg": "أدخل البيانات"}), 400
    user = USERS.get(u)
    if not user or user.get("password") != hash_pw(p):
        return jsonify({"ok": False, "msg": "بيانات خاطئة"}), 401
    is_admin = (user.get("role") == "admin")
    session["user"] = u
    session["role"] = user["role"]
    session["name"] = user["name"]
    session["sid"] = secrets.token_hex(8)
    STATS["logins"] = STATS.get("logins", 0) + 1
    save_stats()
    return jsonify({"ok": True, "name": user["name"], "role": user["role"]})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

# ============ الصفحات ============
@app.route("/")
def index():
    STATS["visitors"] = STATS.get("visitors", 0) + 1
    save_stats()
    return render_template_string(HTML_APP, google_client_id=GOOGLE_CLIENT_ID)

@app.route("/manifest.json")
def manifest():
    return Response(MANIFEST_JSON, mimetype="application/manifest+json")

@app.route("/sw.js")
def sw():
    resp = Response(SERVICE_WORKER_JS, mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp

@app.route("/icon.svg")
def icon():
    return Response(ICON_SVG, mimetype="image/svg+xml")

# ============ Chat ============
@app.route("/api/chat", methods=["POST"])
@login_required
@rate_limit(max_calls=30, window=60)
def api_chat():
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    mode = data.get("mode", "general")
    sid = session.get("sid", "default")
    is_admin = session.get("role") == "admin"

    if not msg:
        return jsonify({"reply": "اكتب رسالة."}), 400
    if mode not in ["general","write","code","math","translate","summary","religion","science"]:
        mode = "general"

    msg_l = msg.lower().strip()

    # ردود ثابتة
    if any(p in msg_l for p in ["من صنعك","من طورك","من أنشأك","من برمجك",
                                 "من هو مطورك","من المطور","من صانعك",
                                 "who made you","who created you"]):
        return jsonify({"reply": "طوّرني **محمد كامل** 🇩🇿\n\nأنا **Moka AI**، مساعدك الذكي."})

    if is_admin:
        # ترحيب خاص بالمدير
        if any(p in msg_l for p in ["مرحبا","السلام عليكم","أهلا","اهلا","هاي","hi","hello","salut"]):
            return jsonify({"reply":
                "أهلاً بك يا **محمد** 👑\n\n"
                "نورت! كيف أقدر أساعدك اليوم؟"})

        if any(p in msg_l for p in ["من انا","من أنا","هل تعرفني","who am i"]):
            return jsonify({"reply":
                "أنت **محمد كامل** 👑\n\n"
                "مطوّري وصاحب مشروع Moka AI. هذه منصتي لك!"})

    # صورة
    if msg.startswith("/صورة ") or msg.startswith("/image "):
        prompt = msg.split(" ", 1)[1].strip()
        if not prompt:
            return jsonify({"reply": "اكتب وصفًا بعد /صورة"})
        forbidden = ["جنس","عاري","إباحي","بورن","مثير","sex","porn",
                     "nude","naked","nsfw","xxx","girl","woman","man",
                     "امرأة","رجل","فتاة","شاب","شخص","إنسان","وجه"]
        if any(w in prompt.lower() for w in forbidden):
            return jsonify({"reply": "🚫 جرّب وصفًا آخر."})
        enhanced = f"beautiful photo of {prompt}, no people, no humans, 8k"
        STATS["images_generated"] = STATS.get("images_generated", 0) + 1
        save_stats()
        url = (f"https://image.pollinations.ai/prompt/"
               f"{urllib.parse.quote(enhanced)}?width=1024&height=1024"
               f"&model=flux&safe=true&nologo=true&seed={int(time.time())}")
        return jsonify({"reply": f"🎨 **{prompt}**", "image": url})

    # كتاب
    if msg.startswith("/كتاب ") or msg.startswith("/book "):
        topic = msg.split(" ", 1)[1].strip()
        if not topic:
            return jsonify({"reply": "اكتب موضوعًا بعد /كتاب"})
        STATS["books_generated"] = STATS.get("books_generated", 0) + 1
        save_stats()
        try:
            b = generate_book(topic, is_admin)
            out = f"# 📖 {topic}\n\n## 📋 الفهرس\n\n{b['toc']}\n\n---\n\n"
            out += f"## ✍️ المقدمة\n\n{b['intro']}\n\n---\n\n"
            for ch in b["chapters"]:
                out += f"## {ch['title']}\n\n{ch['content']}\n\n---\n\n"
            out += "_📘 نهاية الكتاب_"
            return jsonify({"reply": out})
        except Exception as e:
            print("[BOOK] " + str(e), flush=True)
            return jsonify({"reply": "⚠️ فشل توليد الكتاب."})

    # محادثة عادية
    conv = SESSIONS.setdefault(sid, [])
    conv.append({"role": "user", "content": msg})

    extra = ""
    wiki_kw = ["ما هو","ما هي","من هو","من هي","تاريخ","دولة",
               "عاصمة","تعريف","معلومات","أين","متى"]
    if any(k in msg for k in wiki_kw) and len(msg) > 8:
        w = search_wikipedia(msg)
        if w:
            extra += f"\n\n[معلومات]\n{w}"
    if extra:
        conv.insert(-1, {"role": "system", "content": extra.strip()})
    if len(conv) > 24:
        conv[:] = [conv[0]] + conv[-23:]

    reply = call_ai(conv, mode=mode, is_admin=is_admin)
    conv.append({"role": "assistant", "content": reply})

    STATS["messages"] = STATS.get("messages", 0) + 1
    STATS["modes"][mode] = STATS["modes"].get(mode, 0) + 1
    save_stats()
    return jsonify({"reply": reply})

@app.route("/api/clear", methods=["POST"])
@login_required
def api_clear():
    SESSIONS.pop(session.get("sid", "default"), None)
    return jsonify({"ok": True})

@app.route("/api/voice_used", methods=["POST"])
@login_required
def api_voice_used():
    STATS["voice_used"] = STATS.get("voice_used", 0) + 1
    save_stats()
    return jsonify({"ok": True})

@app.route("/api/tts")
def api_tts():
    text = request.args.get("text", "")[:200]
    lang = request.args.get("lang", "ar")
    if not text:
        return "", 400
    try:
        url = ("https://translate.google.com/translate_tts"
               "?ie=UTF-8&client=tw-ob&tl=" + lang + "&q="
               + urllib.parse.quote(text))
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://translate.google.com/"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        resp = Response(data, mimetype="audio/mpeg")
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
    except Exception:
        return "", 500

@app.route("/admin")
def admin():
    if not session.get("user"):
        return "سجل الدخول", 403
    if session.get("role") != "admin":
        return "للمدير فقط", 403
    if request.args.get("key") != ADMIN_KEY:
        return "مفتاح مطلوب", 403
    return render_template_string(HTML_ADMIN, stats=STATS, users=USERS)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ============ PWA ============
MANIFEST_JSON = json.dumps({
    "name": "Moka AI", "short_name": "Moka AI",
    "description": "مساعد ذكي من تطوير محمد كامل",
    "start_url": "/", "display": "standalone",
    "background_color": "#0a0a14", "theme_color": "#dc2626",
    "lang": "ar", "dir": "rtl",
    "icons": [
        {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"},
        {"src": "/icon.svg", "sizes": "192x192", "type": "image/svg+xml", "purpose": "maskable"},
        {"src": "/icon.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "maskable"},
    ]
}, ensure_ascii=False)

SERVICE_WORKER_JS = """
const CACHE = "moka-v35";
self.addEventListener("install", function(){self.skipWaiting()});
self.addEventListener("activate", function(e){e.waitUntil(self.clients.claim())});
self.addEventListener("fetch", function(e){
  if(e.request.url.includes("/api/")) return;
  if(!e.request.url.startsWith(location.origin)) return;
  e.respondWith(
    fetch(e.request).then(function(r){
      if(r && r.status === 200){
        const c = r.clone();
        caches.open(CACHE).then(function(x){x.put(e.request, c)});
      }
      return r;
    }).catch(function(){return caches.match(e.request)})
  );
});
"""

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<defs>
<linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#ef4444"/>
<stop offset="100%" stop-color="#991b1b"/>
</linearGradient>
<linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#3b82f6"/>
<stop offset="100%" stop-color="#1e3a8a"/>
</linearGradient>
</defs>
<rect width="512" height="512" rx="128" fill="#0a0a14"/>
<rect x="24" y="24" width="464" height="464" rx="112" fill="none" stroke="url(#g1)" stroke-width="3" opacity="0.4"/>
<path d="M 128 380 L 128 150 L 200 150 L 256 260 L 312 150 L 384 150 L 384 380 L 320 380 L 320 250 L 270 340 L 242 340 L 192 250 L 192 380 Z" fill="url(#g1)"/>
<circle cx="400" cy="100" r="22" fill="url(#g2)"/>
<circle cx="400" cy="100" r="10" fill="#fff"/>
<circle cx="112" cy="412" r="14" fill="#fbbf24"/>
</svg>"""

HTML_APP = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Moka AI</title>
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#dc2626">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="apple-touch-icon" href="/icon.svg">
<link rel="icon" type="image/svg+xml" href="/icon.svg">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://accounts.google.com/gsi/client" async defer></script>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{--bg:#0a0a14;--card:#181828;--card2:#1f1f33;--border:#2a2a45;
--text:#eaeaf5;--muted:#8a8aa8;--red:#dc2626;
--grad:linear-gradient(135deg,#dc2626,#1e3a8a)}
body{font-family:Cairo,system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

#login{position:fixed;inset:0;z-index:99;background:var(--bg);
display:flex;flex-direction:column;align-items:center;justify-content:center;
padding:24px;gap:16px;overflow-y:auto}
.logo{width:90px;height:90px}
.title{font-size:34px;font-weight:900;background:var(--grad);
-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--muted);font-size:13px;margin-top:-6px;margin-bottom:10px}
.gbox{display:flex;justify-content:center;width:100%}
.manual-btn{background:transparent;border:1px solid var(--border);color:var(--muted);
padding:10px 20px;border-radius:10px;cursor:pointer;font-family:inherit;font-size:13px;margin-top:10px}
.manual-form{width:100%;max-width:340px;display:none;flex-direction:column;gap:10px;margin-top:10px}
.manual-form.on{display:flex}
.manual-form input{padding:14px 16px;border-radius:12px;border:1.5px solid var(--border);
background:var(--card);color:var(--text);font-size:15px;font-family:inherit;outline:none}
.manual-form input:focus{border-color:var(--red)}
.manual-form button{padding:14px;border-radius:12px;border:none;background:var(--grad);
color:#fff;font-size:15px;font-weight:800;font-family:inherit;cursor:pointer}
.err{color:#f87171;font-size:12px;min-height:16px;text-align:center}

#app{display:none;min-height:100vh;flex-direction:column}
#app.on{display:flex}
.hd{display:flex;align-items:center;gap:10px;padding:12px 16px;
background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10}
.hd-logo{width:36px;height:36px;border-radius:10px}
.hd h1{font-size:16px;font-weight:800;background:var(--grad);
-webkit-background-clip:text;background-clip:text;color:transparent}
.hd .sub{font-size:10px;color:var(--muted)}
.hd-actions{margin-inline-start:auto;display:flex;gap:6px}
.hd-actions button{width:38px;height:38px;border-radius:11px;border:none;
background:var(--card2);color:var(--text);cursor:pointer;font-size:16px}
.hd-actions button.voice-on{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff}

#ch{flex:1;overflow-y:auto;padding:16px 14px 180px;display:flex;flex-direction:column;gap:14px}

.welcome{display:flex;flex-direction:column;align-items:center;gap:16px;
text-align:center;padding:50px 20px}
.welcome img{width:80px;height:80px}
.welcome h2{font-size:22px;font-weight:800}
.welcome p{color:var(--muted);font-size:13px;max-width:280px;line-height:1.7}
.chips{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;max-width:400px;width:100%}
.chips button{padding:12px;border-radius:12px;border:1px solid var(--border);
background:var(--card);color:var(--text);font-family:inherit;font-size:12px;
font-weight:600;cursor:pointer}

.mw{display:flex;gap:8px;max-width:92%}
.mw.u{align-self:flex-start;flex-direction:row-reverse}
.mw.b{align-self:flex-end}
.avt{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;
font-weight:900;font-size:13px;color:#fff;flex-shrink:0;overflow:hidden}
.mw.u .avt{background:var(--grad)}
.mw.b .avt{background:linear-gradient(135deg,#06b6d4,#8b5cf6)}
.avt img{width:100%;height:100%;object-fit:cover}
.m{padding:12px 16px;border-radius:16px;line-height:1.8;font-size:14px;
word-wrap:break-word;overflow-wrap:anywhere}
.u .m{background:var(--grad);color:#fff;border-top-right-radius:5px}
.b .m{background:var(--card2);color:var(--text);border:1px solid var(--border);
border-top-left-radius:5px}
.b .m h1,.b .m h2,.b .m h3{margin:10px 0 6px;font-weight:800}
.b .m h1{font-size:18px;color:#ef4444}
.b .m h2{font-size:16px;color:#ef4444}
.b .m h3{font-size:14px;color:#3b82f6}
.b .m strong{color:#ef4444}
.b .m ul,.b .m ol{padding-inline-start:1.4rem;margin:6px 0}
.b .m pre{background:#000;padding:12px;border-radius:10px;overflow-x:auto;
direction:ltr;text-align:left;margin:8px 0;font-size:12px;font-family:monospace}
.b .m code{background:rgba(220,38,38,.2);padding:2px 6px;border-radius:5px;
font-family:monospace;font-size:.9em;direction:ltr}
.b .m pre code{background:transparent;padding:0;color:inherit}
.b .m img{max-width:100%;border-radius:12px;margin-top:8px;display:block}
.b .m hr{border:none;border-top:1px solid var(--border);margin:12px 0}

.tp{display:flex;gap:4px;padding:12px 16px}
.tp span{width:7px;height:7px;border-radius:50%;background:var(--red);animation:b 1.2s infinite}
.tp span:nth-child(2){animation-delay:.15s}
.tp span:nth-child(3){animation-delay:.3s}
@keyframes b{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-6px);opacity:1}}

.input-area{position:fixed;bottom:0;left:0;right:0;padding:10px 12px 14px;
background:linear-gradient(to top,var(--bg) 60%,transparent);z-index:5}
.modes{display:flex;gap:6px;margin-bottom:8px;overflow-x:auto;padding-bottom:4px;scrollbar-width:none}
.modes::-webkit-scrollbar{display:none}
.modes button{background:var(--card);border:1px solid var(--border);
color:var(--muted);padding:7px 13px;border-radius:10px;font-size:12px;
font-family:inherit;font-weight:600;cursor:pointer;white-space:nowrap}
.modes button.on{background:var(--grad);color:#fff;border-color:transparent}
.inp-box{display:flex;align-items:flex-end;gap:6px;background:var(--card);
border:1px solid var(--border);border-radius:20px;padding:6px}
.inp-box:focus-within{border-color:var(--red)}
#i{flex:1;resize:none;border:none;outline:none;background:transparent;
color:var(--text);padding:10px 12px;font-family:inherit;font-size:14px;
max-height:140px;line-height:1.5}
#i::placeholder{color:var(--muted)}
.ib{width:42px;height:42px;border-radius:12px;border:none;font-size:17px;
cursor:pointer;display:grid;place-items:center;flex-shrink:0}
#mic{background:var(--card2);color:var(--text)}
#mic.rec{background:#dc2626;color:#fff}
#s{background:var(--grad);color:#fff}
#s:disabled{opacity:.4}

#install{position:fixed;bottom:90px;right:12px;left:12px;max-width:400px;
margin:auto;padding:12px;background:var(--grad);color:#fff;border-radius:14px;
box-shadow:0 12px 32px rgba(220,38,38,.5);z-index:100;display:flex;
align-items:center;gap:10px;font-family:inherit;font-size:13px;font-weight:700}
#install button{padding:7px 12px;border:none;border-radius:9px;background:#fff;
color:var(--red);font-weight:800;font-family:inherit;font-size:12px;cursor:pointer}
#install .x{background:transparent;color:#fff;font-size:16px;padding:4px 6px}
</style>
</head>
<body>

<div id="login">
  <img src="/icon.svg" class="logo" alt="Moka">
  <div class="title">Moka AI</div>
  <div class="sub">من تطوير محمد كامل</div>

  <div class="gbox">
    <div id="g_id_onload"
         data-client_id="{{ google_client_id }}"
         data-callback="onGoogleLogin"
         data-auto_prompt="false"></div>
    <div class="g_id_signin"
         data-type="standard"
         data-size="large"
         data-theme="filled_black"
         data-text="signin_with"
         data-shape="pill"
         data-locale="ar"></div>
  </div>

  <button class="manual-btn" onclick="toggleManual()">🔑 دخول احتياطي</button>

  <div class="manual-form" id="manualForm">
    <input id="mu" placeholder="اسم المستخدم" autocomplete="username">
    <input id="mp" type="password" placeholder="كلمة السر" autocomplete="current-password">
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
      <button id="vb" onclick="toggleVoice()">🔇</button>
      <button onclick="menu()">☰</button>
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

<script>
let mode="general", history=[], isAdmin=false, isSending=false, userName="", userPic="";
let voiceEnabled=false, currentAudio=null, deferredPrompt=null;

const ch=document.getElementById("ch"), i=document.getElementById("i"),
      s=document.getElementById("s"), mic=document.getElementById("mic"),
      vb=document.getElementById("vb"), errEl=document.getElementById("err");

function toggleManual(){
  document.getElementById("manualForm").classList.toggle("on");
}

async function doManualLogin(){
  const u = document.getElementById("mu").value.trim();
  const p = document.getElementById("mp").value;
  if(!u || !p){errEl.textContent="املأ الحقول";return}
  try{
    const r = await fetch("/api/login", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({username:u, password:p})
    });
    const d = await r.json();
    if(!d.ok){errEl.textContent = d.msg || "خطأ";return}
    enterApp(d.name, d.role, "");
  }catch(e){errEl.textContent = "تعذر الاتصال"}
}

function esc(t){return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function md(t){
  let h=esc(t);
  h=h.replace(/```(\w*)\n([\s\S]*?)```/g,function(_,l,c){return "<pre><code>"+c+"</code></pre>"});
  h=h.replace(/^### (.+)$/gm,"<h3>$1</h3>");
  h=h.replace(/^## (.+)$/gm,"<h2>$1</h2>");
  h=h.replace(/^# (.+)$/gm,"<h1>$1</h1>");
  h=h.replace(/^---$/gm,"<hr>");
  h=h.replace(/`([^`]+)`/g,"<code>$1</code>");
  h=h.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>");
  h=h.replace(/^\s*[-*] (.+)$/gm,"<li>$1</li>");
  h=h.replace(/(<li>[\s\S]*?<\/li>)/g,function(m){return "<ul>"+m+"</ul>"});
  h=h.replace(/\n/g,"<br>");
  return h;
}

function addMsg(text, who, img){
  const w=document.createElement("div");
  w.className="mw "+who;
  const av=document.createElement("div");
  av.className="avt";
  if(who==="u" && userPic){
    av.innerHTML='<img src="'+userPic+'" alt="">';
  } else {
    av.textContent=who==="u"?(userName||"أ").charAt(0).toUpperCase():"M";
  }
  const m=document.createElement("div");
  m.className="m";
  m.innerHTML=who==="b"?md(text):esc(text);
  if(img){
    const im=document.createElement("img");
    im.src=img; im.alt="صورة";
    m.appendChild(im);
  }
  const wrap=document.createElement("div");
  wrap.appendChild(m);
  if(who==="b"){
    const acts=document.createElement("div");
    acts.style.cssText="display:flex;gap:4px;margin-top:6px;flex-wrap:wrap";
    const c1=document.createElement("button");
    c1.textContent="📋";
    c1.style.cssText="padding:4px 10px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--muted);font-family:inherit;font-size:11px;cursor:pointer";
    c1.onclick=function(){navigator.clipboard.writeText(text);c1.textContent="✅";setTimeout(function(){c1.textContent="📋"},1500)};
    const c2=document.createElement("button");
    c2.textContent="🔊";
    c2.style.cssText=c1.style.cssText;
    c2.onclick=function(){speak(text,true)};
    acts.appendChild(c1); acts.appendChild(c2);
    wrap.appendChild(acts);
  }
  w.appendChild(av); w.appendChild(wrap);
  ch.appendChild(w);
  ch.scrollTop=ch.scrollHeight;
}

function typ(){
  const w=document.createElement("div");
  w.className="mw b"; w.id="tp";
  w.innerHTML='<div class="avt">M</div><div class="m tp"><span></span><span></span><span></span></div>';
  ch.appendChild(w);
  ch.scrollTop=ch.scrollHeight;
  return w;
}

function welcome(){
  const greeting = isAdmin ? "أهلاً "+userName+" 👑" : "مرحبًا "+userName;
  ch.innerHTML='<div class="welcome"><img src="/icon.svg" alt="Moka">'+
    '<h2>'+greeting+'</h2>'+
    '<p>'+(isAdmin ? "أنا Moka AI، مساعدك الشخصي. يشرفني خدمتك يا مطوّري!" : "أنا Moka AI، مساعدك الذكي من تطوير محمد كامل.")+'</p>'+
    '<div class="chips">'+
    '<button onclick="quick(\'من صنعك؟\')">👋 من صنعك؟</button>'+
    '<button onclick="quick(\'/كتاب تاريخ الجزائر\')">📚 مولّد الكتب</button>'+
    '<button onclick="quick(\'اكتب كود Python\')">💻 كود</button>'+
    '<button onclick="quick(\'/صورة غروب على البحر\')">🎨 صورة</button>'+
    '</div></div>';
}

function quick(t){i.value=t; send()}

function onGoogleLogin(response){
  fetch("/api/google-login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({credential: response.credential})
  })
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.ok){ errEl.textContent = d.msg || "فشل الدخول"; return; }
    enterApp(d.name, d.role, d.picture);
  })
  .catch(function(){ errEl.textContent = "تعذر الاتصال بالخادم"; });
}

function toggleVoice(){
  voiceEnabled = !voiceEnabled;
  vb.classList.toggle("voice-on", voiceEnabled);
  vb.innerHTML = voiceEnabled?"🔊":"🔇";
  if(voiceEnabled){
    fetch("/api/voice_used",{method:"POST"});
    speak("تم تفعيل الصوت", true);
  } else {
    if(currentAudio){currentAudio.pause(); currentAudio=null;}
    if(window.speechSynthesis) speechSynthesis.cancel();
  }
}

function clean(t){
  return t.replace(/```[\s\S]*?```/g,"").replace(/`([^`]+)`/g,"$1")
          .replace(/[#*_]/g,"").replace(/\n+/g," ").slice(0,190);
}

function speak(text, force){
  if(!voiceEnabled && !force) return;
  const c = clean(text);
  if(!c) return;
  if(currentAudio){currentAudio.pause();currentAudio=null;}
  if(window.speechSynthesis) speechSynthesis.cancel();
  currentAudio = new Audio("/api/tts?lang=ar&text="+encodeURIComponent(c));
  currentAudio.play().catch(function(){});
}

let rec = null;
function toggleMic(){
  if(!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)){
    alert("المتصفح لا يدعم المايك"); return;
  }
  if(rec){rec.stop();return;}
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  rec = new SR();
  rec.lang = "ar-SA";
  rec.onstart = function(){mic.classList.add("rec")};
  rec.onend = function(){mic.classList.remove("rec"); rec=null};
  rec.onresult = function(e){
    i.value += (i.value?" ":"") + e.results[0][0].transcript;
    i.focus();
  };
  rec.start();
}

function enterApp(name, role, pic){
  userName = name;
  userPic = pic || "";
  isAdmin = (role === "admin");
  document.getElementById("login").style.display="none";
  document.getElementById("app").classList.add("on");
  document.getElementById("who").textContent = (isAdmin?"👑 ":"") + name;
  welcome();
  i.focus();
}

async function send(){
  const t=i.value.trim();
  if(!t||isSending) return;
  const w=ch.querySelector(".welcome"); if(w) ch.innerHTML="";
  addMsg(t,"u");
  history.push({role:"user",content:t});
  i.value=""; i.style.height="auto";
  isSending=true; s.disabled=true;
  const tp=typ();
  try{
    const r=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:t,mode:mode,history:history.slice(0,-1)})});
    const d=await r.json();
    tp.remove();
    addMsg(d.reply||"لا يوجد رد.","b",d.image||null);
    history.push({role:"assistant",content:d.reply||""});
    if(voiceEnabled && !d.image) speak(d.reply);
  }catch(e){
    tp.remove();
    addMsg("تعذر الاتصال","b");
  }finally{
    isSending=false; s.disabled=false; i.focus();
  }
}

function sw(m){
  mode=m;
  document.querySelectorAll(".modes button").forEach(function(b){b.classList.toggle("on",b.dataset.m===m)});
}

function menu(){
  const a=["مسح المحادثة"];
  if(isAdmin) a.push("لوحة الإدارة");
  a.push("تسجيل الخروج");
  const c=prompt("اختر:\n"+a.map(function(x,n){return (n+1)+". "+x}).join("\n"));
  const idx=parseInt(c)-1, x=a[idx];
  if(!x) return;
  if(x==="مسح المحادثة"){
    if(confirm("مسح؟")){
      history=[];
      fetch("/api/clear",{method:"POST"});
      welcome();
    }
  } else if(x==="لوحة الإدارة"){
    const k=prompt("مفتاح اللوحة:");
    if(k) window.open("/admin?key="+k,"_blank");
  } else if(x==="تسجيل الخروج"){
    if(confirm("خروج؟")) fetch("/api/logout",{method:"POST"}).then(function(){location.reload()});
  }
}

i.addEventListener("keydown",function(e){
  if(e.key==="Enter" && !e.shiftKey){e.preventDefault(); send();}
});
i.addEventListener("input",function(){
  i.style.height="auto";
  i.style.height=Math.min(i.scrollHeight,140)+"px";
});

if("serviceWorker" in navigator){
  window.addEventListener("load",function(){navigator.serviceWorker.register("/sw.js").catch(function(){})});
}
window.addEventListener("beforeinstallprompt",function(e){
  e.preventDefault();
  deferredPrompt=e;
  if(document.getElementById("install")) return;
  const b=document.createElement("div");
  b.id="install";
  b.innerHTML='<span style="font-size:22px">📱</span><div style="flex:1">ثبّت Moka AI<div style="font-size:11px;font-weight:500;opacity:.85">يعمل بدون متصفح</div></div><button onclick="installApp()">تثبيت</button><button class="x" onclick="this.parentElement.remove()">✕</button>';
  document.body.appendChild(b);
});
function installApp(){
  if(!deferredPrompt) return;
  deferredPrompt.prompt();
  deferredPrompt.userChoice.then(function(){
    deferredPrompt=null;
    const b=document.getElementById("install");
    if(b) b.remove();
  });
}
</script>
</body>
</html>'''

HTML_ADMIN = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>لوحة الإدارة</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800;900&display=swap" rel="stylesheet">
<style>
body{font-family:Cairo;background:#0a0a14;color:#eaeaf5;padding:20px;min-height:100vh}
h1{font-size:24px;font-weight:900;color:#ef4444;margin-bottom:6px}
.sub{color:#8a8aa8;font-size:12px;margin-bottom:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:20px}
.card{background:#181828;border:1px solid #2a2a45;border-radius:14px;padding:16px;text-align:center}
.num{font-size:26px;font-weight:900;color:#ef4444}
.lbl{font-size:11px;color:#8a8aa8;margin-top:4px}
.box{background:#181828;border:1px solid #2a2a45;border-radius:14px;padding:16px;margin-bottom:14px}
.box h2{font-size:15px;font-weight:800;margin-bottom:10px}
.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #2a2a45;font-size:13px;gap:8px;flex-wrap:wrap}
.row:last-child{border-bottom:none}
.row .meta{color:#8a8aa8;font-size:11px}
.badge{background:#dc2626;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:800}
.badge.user{background:#22c55e}
a.back{display:inline-block;color:#ef4444;text-decoration:none;font-weight:800;margin-bottom:14px;font-size:13px}
</style>
</head>
<body>
<a href="/" class="back">← رجوع</a>
<h1>لوحة الإدارة</h1>
<div class="sub">Moka AI — محمد كامل</div>

<div class="grid">
  <div class="card"><div class="num">{{ stats.visitors }}</div><div class="lbl">زيارات</div></div>
  <div class="card"><div class="num">{{ stats.logins }}</div><div class="lbl">دخول</div></div>
  <div class="card"><div class="num">{{ stats.messages }}</div><div class="lbl">رسائل</div></div>
  <div class="card"><div class="num">{{ stats.books_generated }}</div><div class="lbl">كتب</div></div>
  <div class="card"><div class="num">{{ stats.images_generated }}</div><div class="lbl">صور</div></div>
  <div class="card"><div class="num">{{ stats.voice_used }}</div><div class="lbl">صوت</div></div>
  <div class="card"><div class="num">{{ users|length }}</div><div class="lbl">مستخدمين</div></div>
</div>

<div class="box">
  <h2>المستخدمون</h2>
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
    print("=" * 55, flush=True)
    print("Moka AI v35.0 - Final", flush=True)
    print("Admin: " + ADMIN_EMAIL, flush=True)
    print("Google: " + ("OK" if GOOGLE_CLIENT_ID else "MISSING!"), flush=True)
    print("Groq: " + ("OK" if GROQ_API_KEY else "MISSING!"), flush=True)
    print("OpenRouter: " + ("OK" if OPENROUTER_API_KEY else "MISSING!"), flush=True)
    print("=" * 55, flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)
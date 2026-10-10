# -*- coding: utf-8 -*-
# ============================================================
#  Moka AI v21.0 — نسخة آمنة
#  المطوّر: محمد كامل
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

# ============================================================
#  🔐 بيانات الإدارة — غيّرها عبر متغيرات البيئة في Render!
# ============================================================
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "km_2026_prime_kamel_dz")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "M0k@.AI#2026$Kamel!X9Secure")
ADMIN_KEY      = os.environ.get("ADMIN_KEY",      "moka_admin_hidden_2026_dz_#X9prime")
SECRET_SALT    = os.environ.get("SECRET_SALT",    "moka_salt_2026_kamel_dz_#X9")

# ============================================================
#  🤖 مفاتيح API
# ============================================================
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
TOGETHER_API_KEY   = os.environ.get("TOGETHER_API_KEY", "").strip()

PROVIDERS = [
    {"name": "groq",
     "url": "https://api.groq.com/openai/v1/chat/completions",
     "key": GROQ_API_KEY,
     "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant",
                "mixtral-8x7b-32768", "gemma2-9b-it"]},
    {"name": "openrouter",
     "url": "https://openrouter.ai/api/v1/chat/completions",
     "key": OPENROUTER_API_KEY,
     "models": ["meta-llama/llama-3.3-70b-instruct:free",
                "google/gemma-2-9b-it:free",
                "qwen/qwen-2.5-72b-instruct:free"]},
    {"name": "together",
     "url": "https://api.together.xyz/v1/chat/completions",
     "key": TOGETHER_API_KEY,
     "models": ["meta-llama/Llama-3.3-70B-Instruct-Turbo"]},
]

# ============================================================
#  📁 الملفات
# ============================================================
DATA_DIR     = os.path.dirname(os.path.abspath(__file__))
USERS_FILE   = os.path.join(DATA_DIR, "users.json")
STATS_FILE   = os.path.join(DATA_DIR, "stats.json")
BLOCKED_FILE = os.path.join(DATA_DIR, "blocked.json")

BLOCKED_IPS = set()
RATE_LIMITS = defaultdict(list)
SESSIONS    = {}

# ============================================================
#  💾 دوال الملفات
# ============================================================
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
        print(f"[save_json] {e}")

def hash_pw(pw):
    """تشفير قوي مع Salt"""
    salted = (pw + SECRET_SALT).encode("utf-8")
    return hashlib.sha256(salted).hexdigest()

# ============================================================
#  👤 تحميل/إنشاء المستخدمين
# ============================================================
USERS = load_json(USERS_FILE, {})

# إذا لم يكن هناك users.json، أنشئ حساب المدير الوحيد
if not USERS or ADMIN_USERNAME not in USERS:
    USERS = {
        ADMIN_USERNAME: {
            "password": hash_pw(ADMIN_PASSWORD),
            "name": "محمد كامل",
            "role": "admin",
            "created": datetime.now().isoformat(),
        }
    }
    save_json(USERS_FILE, USERS)

# ============================================================
#  📊 الإحصائيات
# ============================================================
DEFAULT_STATS = {
    "visitors": 0, "logins": 0, "messages": 0,
    "modes": {m: 0 for m in ["general", "math", "code", "religion",
                              "translate", "summary", "creative", "science"]},
    "recent": [], "messages_log": [],
    "started_at": datetime.now().isoformat(),
}

STATS = {**DEFAULT_STATS, **load_json(STATS_FILE, {})}
for m in DEFAULT_STATS["modes"]:
    STATS["modes"].setdefault(m, 0)

def save_stats():   save_json(STATS_FILE, STATS)
def save_users():   save_json(USERS_FILE, USERS)
def save_blocked(): save_json(BLOCKED_FILE, list(BLOCKED_IPS))

BLOCKED_IPS = set(load_json(BLOCKED_FILE, []))

# ============================================================
#  🛠️ دوال مساعدة
# ============================================================
def get_ip():
    return (request.headers.get("X-Forwarded-For", request.remote_addr or "?")
            .split(",")[0].strip())

def now_algeria():
    return datetime.now(timezone(timedelta(hours=1)))

def alg_date_context():
    d = now_algeria()
    months = ["جانفي","فيفري","مارس","أفريل","ماي","جوان",
              "جويلية","أوت","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
    days = ["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
    return (f"اليوم: {days[d.weekday()]} {d.day} {months[d.month-1]} "
            f"{d.year} — {d.strftime('%H:%M')} بتوقيت الجزائر")

def rate_limit(max_calls=20, window=60):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            ip = get_ip()
            now = time.time()
            RATE_LIMITS[ip] = [t for t in RATE_LIMITS[ip] if now - t < window]
            if len(RATE_LIMITS[ip]) >= max_calls:
                return jsonify({"reply": "⏳ أرسلت رسائل كثيرة. انتظر."}), 429
            RATE_LIMITS[ip].append(now)
            return fn(*a, **kw)
        return wrapper
    return deco

def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("user"):
            if request.path.startswith("/api"):
                return jsonify({"ok": False, "msg": "not logged in"}), 401
            return redirect(url_for("index"))
        return fn(*a, **kw)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if session.get("role") != "admin" and request.args.get("key") != ADMIN_KEY:
            return "🔒 وصول مرفوض", 403
        return fn(*a, **kw)
    return wrapper

# ============================================================
#  🔍 البحث في ويكيبيديا
# ============================================================
def search_wikipedia(query):
    try:
        url = ("https://ar.wikipedia.org/w/api.php?action=query&list=search&srsearch="
               + urllib.parse.quote(query) + "&format=json&utf8=1&srlimit=1")
        req = urllib.request.Request(url, headers={"User-Agent": "MokaAI/21.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        hits = data.get("query", {}).get("search", [])
        if not hits: return None
        title = hits[0]["title"]
        sum_url = ("https://ar.wikipedia.org/api/rest_v1/page/summary/"
                   + urllib.parse.quote(title))
        req2 = urllib.request.Request(sum_url, headers={"User-Agent": "MokaAI/21.0"})
        with urllib.request.urlopen(req2, timeout=8) as r2:
            sdata = json.loads(r2.read().decode("utf-8"))
        extract = sdata.get("extract", "")
        return f"📖 {title}:\n{extract[:800]}" if extract else None
    except Exception:
        return None

# ============================================================
#  🧠 رسائل النظام
# ============================================================
OWNER_INFO = """
【معلومات المطوّر】
- الاسم: محمد كامل
- العمر: 15 سنة
- الميلاد: 16 أفريل 2011
- الجنسية: جزائري
- المشروع: Moka AI
"""

RULES = """
【قواعد الهوية — إلزامية】
1. إذا سُئلت "من صنعك؟" أجب: "طوّرني محمد كامل."
2. ممنوع ذكر أي شركة تقنية (OpenAI, Google, Meta, Anthropic, DeepSeek).
3. ممنوع ذكر أسماء نماذج (GPT, Gemini, Claude, Llama). قل: "تقنية Moka AI الداخلية".
4. اسمك Moka AI.
5. لا تتطرق أبدًا لمواضيع جنسية أو غير أخلاقية. اعتذر بلطف وأعد التوجيه.

【اللغة】 أجب بنفس لغة السؤال.
【التنسيق】 ممنوع LaTeX و ###. استخدم **غامق** و - للقوائم.
【الشخصية】 ذكي، مختصر، ودود، محترم.
"""

MODES = {
    "general":   "أنت مساعد عام. تجيب عن أي سؤال بوضوح.",
    "math":      "أنت خبير رياضيات. اشرح خطوة بخطوة.",
    "code":      "أنت خبير برمجة. اكتب كودًا نظيفًا كاملًا.",
    "religion":  "أنت مساعد علوم إسلامية. مصادرك: القرآن، البخاري، مسلم.",
    "translate": "أنت مترجم محترف.",
    "summary":   "أنت خبير تلخيص.",
    "creative":  "أنت كاتب إبداعي.",
    "science":   "أنت عالم. اشرح بدقة وبساطة.",
}

def build_system(mode):
    return (MODES.get(mode, MODES["general"]) + "\n\n"
            + OWNER_INFO + "\n" + RULES + "\n" + alg_date_context())

def clean_reply(text):
    text = text.replace("\\(", "").replace("\\)", "")
    text = text.replace("\\[", "").replace("\\]", "")
    text = text.replace("\\sqrt", "√").replace("\\frac", "")
    return text.strip()

def call_ai(messages, mode="general", max_tokens=1500):
    system = build_system(mode)
    full = [{"role": "system", "content": system}] + messages[-20:]
    last_err = ""
    for provider in PROVIDERS:
        if not provider["key"]: continue
        for model in provider["models"]:
            try:
                payload = json.dumps({
                    "model": model, "messages": full,
                    "temperature": 0.7, "max_tokens": max_tokens,
                }).encode("utf-8")
                req = urllib.request.Request(
                    provider["url"], data=payload,
                    headers={"Authorization": f"Bearer {provider['key']}",
                             "Content-Type": "application/json",
                             "User-Agent": "MokaAI/21.0"},
                    method="POST")
                with urllib.request.urlopen(req, timeout=45) as r:
                    data = json.loads(r.read().decode("utf-8"))
                reply = data["choices"][0]["message"]["content"].strip()
                if reply:
                    print(f"[AI] ✅ {provider['name']} → {model}")
                    return clean_reply(reply)
            except urllib.error.HTTPError as e:
                last_err = f"HTTP {e.code}"
                print(f"[AI] ❌ {provider['name']}/{model}: {last_err}")
                continue
            except Exception as e:
                last_err = str(e)[:80]
                print(f"[AI] ❌ {provider['name']}/{model}: {e}")
                continue
    return f"⚠️ تعذر الاتصال بجميع المزودين. ({last_err})"

# ============================================================
#  🌐 Routes
# ============================================================

@app.route("/")
def index():
    STATS["visitors"] = STATS.get("visitors", 0) + 1
    save_stats()
    if get_ip() in BLOCKED_IPS:
        return "🚫 تم حظر وصولك.", 403
    return render_template_string(HTML_APP)


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    u = data.get("username", "").strip()
    p = data.get("password", "")
    if not u or not p:
        return jsonify({"ok": False, "msg": "أدخل البيانات"}), 400
    if get_ip() in BLOCKED_IPS:
        return jsonify({"ok": False, "msg": "محظور"}), 403
    user = USERS.get(u)
    if not user or user["password"] != hash_pw(p):
        return jsonify({"ok": False, "msg": "بيانات خاطئة"}), 401
    session["user"] = u
    session["role"] = user["role"]
    session["name"] = user["name"]
    session["sid"] = secrets.token_hex(8)
    STATS["logins"] = STATS.get("logins", 0) + 1
    STATS.setdefault("recent", []).append({
        "name": user["name"], "ip": get_ip()[:15],
        "time": now_algeria().strftime("%d/%m %H:%M"),
    })
    STATS["recent"] = STATS["recent"][-50:]
    save_stats()
    return jsonify({"ok": True, "name": user["name"], "role": user["role"]})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
@login_required
@rate_limit(max_calls=20, window=60)
def api_chat():
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    mode = data.get("mode", "general")
    sid = session.get("sid", "default")
    if not msg:
        return jsonify({"reply": "اكتب رسالة."}), 400
    if mode not in MODES:
        mode = "general"
    conv = SESSIONS.setdefault(sid, [])
    conv.append({"role": "user", "content": msg})

    # بحث تلقائي
    extra = ""
    wiki_kw = ["ما هو", "ما هي", "من هو", "من هي", "تاريخ", "دولة",
               "عاصمة", "تعريف", "معلومات", "أين", "متى"]
    if any(k in msg for k in wiki_kw) and len(msg) > 8:
        w = search_wikipedia(msg)
        if w:
            extra += f"\n\n[معلومات من ويكيبيديا]\n{w}"
    if extra:
        conv.insert(-1, {"role": "system", "content": extra.strip()})
    if len(conv) > 24:
        conv[:] = [conv[0]] + conv[-23:]

    reply = call_ai(conv, mode=mode)
    conv.append({"role": "assistant", "content": reply})

    STATS["messages"] = STATS.get("messages", 0) + 1
    STATS["modes"][mode] = STATS["modes"].get(mode, 0) + 1
    STATS.setdefault("messages_log", []).append({
        "user": session.get("name", "?"), "mode": mode,
        "text": msg[:100],
        "time": now_algeria().strftime("%d/%m %H:%M"),
    })
    STATS["messages_log"] = STATS["messages_log"][-200:]
    save_stats()

    return jsonify({"reply": reply})


@app.route("/api/clear", methods=["POST"])
@login_required
def api_clear():
    SESSIONS.pop(session.get("sid", "default"), None)
    return jsonify({"ok": True})


# ============================================================
#  👑 لوحة الإدارة — محمية بـ 3 طبقات
# ============================================================

@app.route("/admin")
def admin():
    # ✅ الطبقة 1: يجب أن يكون مسجّلًا
    if not session.get("user"):
        return "🔒 يجب تسجيل الدخول أولًا", 403
    # ✅ الطبقة 2: يجب أن يكون دوره admin
    if session.get("role") != "admin":
        return "🔒 وصول مرفوض — للمدير فقط", 403
    # ✅ الطبقة 3: يجب أن يمرر المفتاح السري
    if request.args.get("key") != ADMIN_KEY:
        return "🔒 مفتاح الإدارة مطلوب. أضف ?key=YOUR_KEY", 403

    return render_template_string(HTML_ADMIN, stats=STATS, users=USERS,
                                  blocked=list(BLOCKED_IPS), key=ADMIN_KEY)


@app.route("/admin/block/<ip>")
@admin_required
def admin_block(ip):
    BLOCKED_IPS.add(ip); save_blocked()
    return redirect(f"/admin?key={ADMIN_KEY}")


@app.route("/admin/unblock/<ip>")
@admin_required
def admin_unblock(ip):
    BLOCKED_IPS.discard(ip); save_blocked()
    return redirect(f"/admin?key={ADMIN_KEY}")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": now_algeria().isoformat()})

# ============================================================
#  🎨 HTML — الواجهة الرئيسية
# ============================================================

HTML_APP = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Moka AI — مساعدك الذكي</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0a12;--card:rgba(24,24,38,.85);--border:rgba(255,255,255,.08);
  --text:#e8e8f0;--muted:#8b8ba8;--primary:#8b5cf6;--secondary:#ec4899;--accent:#06b6d4;}
[data-theme="light"]{--bg:#f4f4fa;--card:rgba(255,255,255,.85);
  --border:rgba(0,0,0,.08);--text:#1a1a2e;--muted:#666}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:Cairo,system-ui,sans-serif;background:var(--bg);color:var(--text);
  min-height:100vh;overflow-x:hidden;transition:background .3s,color .3s}
.bg{position:fixed;inset:0;z-index:-1;overflow:hidden;pointer-events:none}
.bg::before,.bg::after{content:"";position:absolute;border-radius:50%;filter:blur(110px);opacity:.4}
.bg::before{width:520px;height:520px;background:linear-gradient(135deg,#8b5cf6,#ec4899);
  top:-160px;right:-160px;animation:f1 22s ease-in-out infinite}
.bg::after{width:420px;height:420px;background:linear-gradient(135deg,#06b6d4,#8b5cf6);
  bottom:-160px;left:-160px;animation:f2 26s ease-in-out infinite}
@keyframes f1{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(-70px,70px) scale(1.18)}}
@keyframes f2{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(70px,-70px) scale(1.15)}}
#login{position:fixed;inset:0;z-index:999;background:rgba(10,10,20,.88);
  backdrop-filter:blur(20px);display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:24px;gap:14px;overflow-y:auto}
[data-theme="light"] #login{background:rgba(240,240,250,.92)}
.logo-big{width:110px;height:110px;border-radius:32px;
  background:linear-gradient(135deg,#8b5cf6,#ec4899,#06b6d4);display:grid;place-items:center;
  font-size:52px;font-weight:900;color:#fff;box-shadow:0 24px 70px rgba(139,92,246,.5);
  animation:float 3.5s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-14px) rotate(3deg)}}
.brand-title{font-size:42px;font-weight:900;letter-spacing:-1px;
  background:linear-gradient(135deg,#8b5cf6,#ec4899);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.brand-sub{color:var(--muted);font-size:13px;margin-top:-6px}
.login-form{width:100%;max-width:340px;display:flex;flex-direction:column;gap:12px;margin-top:16px}
.login-form input{width:100%;padding:16px 18px;border-radius:16px;border:2px solid var(--border);
  background:var(--card);color:var(--text);font-size:15px;font-family:inherit;outline:none;
  transition:all .2s;backdrop-filter:blur(10px)}
.login-form input:focus{border-color:var(--primary);box-shadow:0 0 0 4px rgba(139,92,246,.15)}
.login-form button{padding:16px;border-radius:16px;border:none;
  background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;font-size:16px;
  font-weight:800;font-family:inherit;cursor:pointer;
  box-shadow:0 12px 32px rgba(139,92,246,.4);transition:transform .15s}
.login-form button:active{transform:scale(.97)}
.login-form button:disabled{opacity:.6}
#app{display:none;min-height:100vh;flex-direction:column}
#app.on{display:flex}
.hd{display:flex;align-items:center;gap:12px;padding:12px 16px;
  background:var(--card);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:50}
.hd-logo{width:40px;height:40px;border-radius:13px;
  background:linear-gradient(135deg,#8b5cf6,#ec4899);display:grid;place-items:center;
  font-size:20px;font-weight:900;color:#fff;box-shadow:0 6px 20px rgba(139,92,246,.4);flex-shrink:0}
.hd h1{font-size:17px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#ec4899);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.hd .sub{font-size:10px;color:var(--muted);display:flex;align-items:center;gap:5px}
.hd .sub::before{content:"";width:6px;height:6px;border-radius:50%;background:#22c55e;
  box-shadow:0 0 8px #22c55e}
.hd-actions{margin-inline-start:auto;display:flex;gap:6px}
.hd-actions button{width:38px;height:38px;border-radius:12px;border:none;
  background:rgba(255,255,255,.06);color:var(--text);cursor:pointer;font-size:16px;
  transition:background .2s;display:grid;place-items:center}
.hd-actions button:hover{background:rgba(255,255,255,.14)}
#ch{flex:1;overflow-y:auto;padding:20px 14px 200px;display:flex;
  flex-direction:column;gap:14px;scroll-behavior:smooth}
#ch::-webkit-scrollbar{width:6px}
#ch::-webkit-scrollbar-thumb{background:var(--border);border-radius:6px}
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:20px;text-align:center;padding:50px 20px;min-height:55vh}
.welcome .lg{width:100px;height:100px;border-radius:28px;
  background:linear-gradient(135deg,#8b5cf6,#ec4899,#06b6d4);display:grid;place-items:center;
  font-size:46px;font-weight:900;color:#fff;
  box-shadow:0 24px 60px rgba(139,92,246,.5);animation:float 3.5s ease-in-out infinite}
.welcome h2{font-size:26px;font-weight:900;
  background:linear-gradient(135deg,#8b5cf6,#ec4899);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.welcome p{color:var(--muted);font-size:14px;max-width:320px;line-height:1.8}
.quick-chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;max-width:420px;margin-top:8px}
.quick-chips button{padding:9px 16px;border-radius:14px;border:1px solid var(--border);
  background:var(--card);color:var(--text);font-family:inherit;font-size:13px;
  font-weight:600;cursor:pointer;transition:all .2s}
.quick-chips button:hover{border-color:var(--primary);color:var(--primary);transform:translateY(-2px)}
.mw{display:flex;max-width:92%;animation:msgIn .35s cubic-bezier(.16,1,.3,1)}
@keyframes msgIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.mw.u{align-self:flex-start}
.mw.b{align-self:flex-end}
.msg-wrap{position:relative;display:flex;flex-direction:column;gap:4px}
.m{padding:14px 18px;border-radius:20px;line-height:1.85;white-space:pre-wrap;
  word-wrap:break-word;font-size:15px;position:relative}
.u .m{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;
  border-bottom-right-radius:6px;box-shadow:0 8px 26px rgba(139,92,246,.35)}
.b .m{background:var(--card);color:var(--text);border:1px solid var(--border);
  border-bottom-left-radius:6px;backdrop-filter:blur(12px)}
.b .m strong{color:var(--primary);font-weight:800}
.b .m pre{background:#000;color:#e8e8f0;padding:14px;border-radius:14px;
  overflow-x:auto;direction:ltr;text-align:left;margin:10px 0;font-size:13px;
  font-family:'Courier New',monospace;border:1px solid rgba(255,255,255,.1)}
.b .m code{background:rgba(139,92,246,.18);padding:2px 7px;border-radius:6px;
  font-family:'Courier New',monospace;font-size:.9em;direction:ltr;display:inline-block}
.b .m pre code{background:transparent;padding:0;color:inherit;display:block}
.b .m a{color:var(--accent);text-decoration:underline}
.msg-actions{display:flex;gap:4px;opacity:0;transition:opacity .2s;padding-inline-start:6px}
.msg-wrap:hover .msg-actions{opacity:1}
.msg-actions button{background:var(--card);border:1px solid var(--border);
  color:var(--muted);padding:4px 10px;border-radius:8px;font-size:11px;
  font-family:inherit;cursor:pointer;transition:all .2s}
.msg-actions button:hover{color:var(--primary);border-color:var(--primary)}
.tp{display:flex;gap:5px;padding:14px 18px}
.tp span{width:8px;height:8px;border-radius:50%;background:var(--primary);animation:bnc 1.2s infinite}
.tp span:nth-child(2){animation-delay:.15s}
.tp span:nth-child(3){animation-delay:.3s}
@keyframes bnc{0%,60%,100%{transform:translateY(0);opacity:.35}30%{transform:translateY(-6px);opacity:1}}
.input-area{position:fixed;bottom:0;left:0;right:0;padding:12px 14px 16px;
  background:linear-gradient(to top,var(--bg) 60%,transparent);z-index:40}
.modes{display:flex;gap:6px;margin-bottom:10px;overflow-x:auto;padding-bottom:6px;scrollbar-width:none}
.modes::-webkit-scrollbar{display:none}
.modes button{background:var(--card);border:1px solid var(--border);color:var(--muted);
  padding:8px 14px;border-radius:12px;font-size:12px;font-family:inherit;
  font-weight:700;cursor:pointer;white-space:nowrap;transition:all .2s}
.modes button.on{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;
  border-color:transparent;box-shadow:0 4px 18px rgba(139,92,246,.35);transform:translateY(-2px)}
.input-box{display:flex;align-items:flex-end;gap:8px;background:var(--card);
  border:1px solid var(--border);border-radius:22px;padding:8px;
  backdrop-filter:blur(16px);box-shadow:0 12px 40px rgba(0,0,0,.2);transition:border-color .2s}
.input-box:focus-within{border-color:var(--primary);box-shadow:0 12px 40px rgba(139,92,246,.25)}
#i{flex:1;resize:none;border:none;outline:none;background:transparent;color:var(--text);
  padding:10px 14px;font-family:inherit;font-size:15px;max-height:140px;line-height:1.5}
#i::placeholder{color:var(--muted)}
.btn-mic,#s{width:44px;height:44px;border:none;border-radius:14px;color:#fff;
  font-size:18px;cursor:pointer;display:grid;place-items:center;flex-shrink:0;transition:transform .15s,opacity .2s}
.btn-mic{background:rgba(255,255,255,.08);color:var(--text)}
.btn-mic.rec{background:#dc2626;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}
#s{background:linear-gradient(135deg,#8b5cf6,#ec4899);box-shadow:0 6px 22px rgba(139,92,246,.45)}
#s:active:not(:disabled){transform:scale(.94)}
#s:disabled{opacity:.4;cursor:not-allowed}
@media(max-width:600px){
  .welcome .lg{width:80px;height:80px;font-size:36px}
  .welcome h2{font-size:22px}.m{font-size:14px;padding:12px 15px}.brand-title{font-size:34px}
}
</style>
</head>
<body>
<div class="bg"></div>

<div id="login">
  <div class="logo-big">M</div>
  <div class="brand-title">Moka AI</div>
  <div class="brand-sub">من تطوير محمد كامل</div>
  <div class="login-form">
    <input id="u" placeholder="اسم المستخدم" autocomplete="username">
    <input id="p" type="password" placeholder="كلمة السر" autocomplete="current-password">
    <button id="loginBtn" onclick="doLogin()">🚀 دخول</button>
  </div>
</div>

<div id="app">
  <div class="hd">
    <div class="hd-logo">M</div>
    <div>
      <h1>Moka AI</h1>
      <div class="sub">من تطوير محمد كامل</div>
    </div>
    <div class="hd-actions">
      <button onclick="toggleTheme()" id="themeBtn" title="المظهر">🌙</button>
      <button onclick="openSidebar()" title="القائمة">☰</button>
    </div>
  </div>

  <div id="ch"></div>

  <div class="input-area">
    <div class="modes">
      <button class="on" data-m="general" onclick="sw('general')">💬 عامة</button>
      <button data-m="math" onclick="sw('math')">📐 رياضيات</button>
      <button data-m="code" onclick="sw('code')">💻 برمجة</button>
      <button data-m="religion" onclick="sw('religion')">🕌 دين</button>
      <button data-m="translate" onclick="sw('translate')">🌍 ترجمة</button>
      <button data-m="summary" onclick="sw('summary')">📝 ملخص</button>
      <button data-m="creative" onclick="sw('creative')">✨ إبداع</button>
      <button data-m="science" onclick="sw('science')">🔬 علوم</button>
    </div>
    <div class="input-box">
      <button class="btn-mic" id="micBtn" onclick="toggleMic()" title="إدخال صوتي">🎤</button>
      <textarea id="i" rows="1" placeholder="اكتب رسالتك…"></textarea>
      <button id="s" onclick="send()">➤</button>
    </div>
  </div>
</div>

<script>
let mode="general",history=[],isAdmin=false,isSending=false;
const ch=document.getElementById("ch"),i=document.getElementById("i"),
      s=document.getElementById("s"),micBtn=document.getElementById("micBtn");

function esc(t){return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function md(t){
  let h=esc(t);
  h=h.replace(/```(\w*)\n([\s\S]*?)```/g,(_,l,c)=>`<pre><code>${c}</code></pre>`);
  h=h.replace(/`([^`]+)`/g,"<code>$1</code>");
  h=h.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>");
  h=h.replace(/\n/g,"<br>");
  return h;
}
function addMsg(text,who){
  const w=document.createElement("div");
  w.className="mw "+who;
  const wrap=document.createElement("div");wrap.className="msg-wrap";
  const m=document.createElement("div");m.className="m";
  m.innerHTML=who==="b"?md(text):esc(text);
  wrap.appendChild(m);
  if(who==="b"){
    const a=document.createElement("div");a.className="msg-actions";
    const b=document.createElement("button");b.textContent="📋 نسخ";
    b.onclick=()=>navigator.clipboard.writeText(text).then(()=>{
      b.textContent="✅ تم";setTimeout(()=>b.textContent="📋 نسخ",1500);
    });
    a.appendChild(b);wrap.appendChild(a);
  }
  w.appendChild(wrap);ch.appendChild(w);ch.scrollTop=ch.scrollHeight;
}
function typ(){
  const w=document.createElement("div");w.className="mw b";w.id="tp";
  w.innerHTML='<div class="msg-wrap"><div class="m tp"><span></span><span></span><span></span></div></div>';
  ch.appendChild(w);ch.scrollTop=ch.scrollHeight;return w;
}
function welcome(){
  ch.innerHTML='<div class="welcome"><div class="lg">M</div>'+
    '<h2>مرحبًا بك في Moka AI</h2>'+
    '<p>مساعدك الذكي من تطوير محمد كامل. اختر نمطًا وابدأ.</p>'+
    '<div class="quick-chips">'+
    '<button onclick="quick(\'اشرح الثقوب السوداء\')">🌌 الثقوب السوداء</button>'+
    '<button onclick="quick(\'اكتب كود Python\')">💻 كود Python</button>'+
    '<button onclick="quick(\'ما هي عاصمة اليابان؟\')">🌏 جغرافيا</button>'+
    '</div></div>';
}
function quick(t){i.value=t;send()}
async function doLogin(){
  const u=document.getElementById("u").value.trim();
  const p=document.getElementById("p").value;
  if(!u||!p){alert("املأ الحقول");return}
  const btn=document.getElementById("loginBtn");
  btn.disabled=true;btn.textContent="⏳...";
  try{
    const r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({username:u,password:p})});
    const d=await r.json();
    if(!d.ok){alert("❌ "+d.msg);btn.disabled=false;btn.textContent="🚀 دخول";return}
    isAdmin=d.role==="admin";
    document.getElementById("login").style.display="none";
    document.getElementById("app").classList.add("on");
    welcome();i.focus();
  }catch(e){alert("تعذر الاتصال");btn.disabled=false;btn.textContent="🚀 دخول"}
}
async function send(){
  const t=i.value.trim();
  if(!t||isSending)return;
  const w=ch.querySelector(".welcome");if(w)ch.innerHTML="";
  addMsg(t,"u");history.push({role:"user",content:t});
  i.value="";i.style.height="auto";isSending=true;s.disabled=true;
  const tp=typ();
  try{
    const r=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:t,mode:mode,history:history.slice(0,-1)})});
    const d=await r.json();tp.remove();
    const reply=d.reply||"⚠️ لا يوجد رد.";
    addMsg(reply,"b");history.push({role:"assistant",content:reply});
  }catch(e){tp.remove();addMsg("⚠️ تعذر الاتصال","b")}
  finally{isSending=false;s.disabled=false;i.focus()}
}
function sw(m){mode=m;document.querySelectorAll(".modes button").forEach(b=>
  b.classList.toggle("on",b.dataset.m===m))}
function toggleTheme(){
  const cur=document.documentElement.getAttribute("data-theme");
  const nxt=cur==="light"?"dark":"light";
  document.documentElement.setAttribute("data-theme",nxt);
  document.getElementById("themeBtn").textContent=nxt==="light"?"☀️":"🌙";
  localStorage.setItem("theme",nxt);
}
(function(){const sv=localStorage.getItem("theme")||"dark";
  document.documentElement.setAttribute("data-theme",sv);
  const b=document.getElementById("themeBtn");if(b)b.textContent=sv==="light"?"☀️":"🌙"})();
let recognition=null;
function toggleMic(){
  if(!("webkitSpeechRecognition" in window)&&!("SpeechRecognition" in window)){
    alert("المتصفح لا يدعم الصوت");return}
  if(recognition){recognition.stop();return}
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  recognition=new SR();recognition.lang="ar-SA";
  recognition.onstart=()=>micBtn.classList.add("rec");
  recognition.onend=()=>{micBtn.classList.remove("rec");recognition=null};
  recognition.onerror=()=>{micBtn.classList.remove("rec");recognition=null};
  recognition.onresult=e=>{i.value+=(i.value?" ":"")+e.results[0][0].transcript;i.focus()};
  recognition.start();
}
function openSidebar(){
  const a=["مسح المحادثة"];
  if(isAdmin)a.push("لوحة الإدارة");
  a.push("تصدير المحادثة","تسجيل الخروج");
  const c=prompt("اختر رقمًا:\n"+a.map((x,n)=>`${n+1}. ${x}`).join("\n"));
  const idx=parseInt(c)-1,ch2=a[idx];
  if(!ch2)return;
  if(ch2==="مسح المحادثة"){if(confirm("مسح؟")){history=[];fetch("/api/clear",{method:"POST"});welcome()}}
  else if(ch2==="لوحة الإدارة"){window.open("/admin","_blank")}
  else if(ch2==="تصدير المحادثة"){
    const txt=history.map(m=>`[${m.role==="user"?"أنا":"Moka"}] ${m.content}`).join("\n\n");
    const bl=new Blob([txt],{type:"text/plain;charset=utf-8"});
    const a2=document.createElement("a");a2.href=URL.createObjectURL(bl);
    a2.download=`moka-chat-${Date.now()}.txt`;a2.click();
  } else if(ch2==="تسجيل الخروج"){if(confirm("خروج؟"))fetch("/api/logout",{method:"POST"}).then(()=>location.reload())}
}
i.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}});
i.addEventListener("input",()=>{i.style.height="auto";i.style.height=Math.min(i.scrollHeight,140)+"px"});
document.getElementById("p").addEventListener("keydown",e=>{if(e.key==="Enter")doLogin()});
</script>
</body>
</html>'''


# ============================================================
#  👑 HTML — لوحة الإدارة
# ============================================================

HTML_ADMIN = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>لوحة الإدارة — Moka AI</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800;900&display=swap" rel="stylesheet">
<style>
body{font-family:Cairo;background:#0a0a12;color:#e8e8f0;padding:22px;min-height:100vh}
h1{font-size:26px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#ec4899);
  -webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:6px}
.sub{color:#8b8ba8;font-size:13px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px;margin-bottom:22px}
.card{background:rgba(24,24,38,.85);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:20px;text-align:center}
.num{font-size:32px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#ec4899);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.lbl{font-size:12px;color:#8b8ba8;margin-top:6px}
.box{background:rgba(24,24,38,.85);border:1px solid rgba(255,255,255,.08);
  border-radius:18px;padding:18px;margin-bottom:16px}
.box h2{font-size:16px;font-weight:800;margin-bottom:12px}
.row{display:flex;justify-content:space-between;padding:10px 0;
  border-bottom:1px solid rgba(255,255,255,.05);font-size:14px;gap:10px;flex-wrap:wrap}
.row:last-child{border-bottom:none}.row .meta{color:#8b8ba8;font-size:12px}
.badge{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;
  padding:3px 10px;border-radius:8px;font-size:11px;font-weight:800}
.badge.user{background:linear-gradient(135deg,#22c55e,#16a34a)}
.msg-item{padding:10px;background:rgba(0,0,0,.2);border-radius:12px;margin-bottom:6px;font-size:13px}
.msg-item .meta{display:flex;justify-content:space-between;color:#8b8ba8;font-size:11px;margin-bottom:4px}
a.back{display:inline-block;color:#8b5cf6;text-decoration:none;font-weight:800;margin-bottom:16px}
a.unblock{background:#22c55e;color:#fff;padding:4px 10px;border-radius:8px;
  font-size:11px;text-decoration:none;font-weight:800}
</style>
</head>
<body>
<a href="/" class="back">← رجوع</a>
<h1>لوحة الإدارة — Moka AI</h1>
<div class="sub">من تطوير محمد كامل · آخر تحديث: {{ stats.updated_at or "—" }}</div>

<div class="grid">
  <div class="card"><div class="num">{{ stats.visitors }}</div><div class="lbl">👁️ زيارات</div></div>
  <div class="card"><div class="num">{{ stats.logins }}</div><div class="lbl">🔑 تسجيلات</div></div>
  <div class="card"><div class="num">{{ stats.messages }}</div><div class="lbl">💬 رسائل</div></div>
  <div class="card"><div class="num">{{ users|length }}</div><div class="lbl">👥 مستخدمين</div></div>
</div>

<div class="box">
  <h2>📊 استخدام الأنماط</h2>
  {% for k, v in stats.modes.items() %}
  <div class="row"><span>{{ k }}</span><b>{{ v }}</b></div>
  {% endfor %}
</div>

<div class="box">
  <h2>👥 المستخدمون</h2>
  {% for u, info in users.items() %}
  <div class="row">
    <span>👤 <b>{{ info.name }}</b> <span class="meta">({{ u }})</span></span>
    <span class="badge {{ 'user' if info.role != 'admin' else '' }}">{{ info.role }}</span>
  </div>
  {% endfor %}
</div>

<div class="box">
  <h2>🔐 تسجيلات حديثة</h2>
  {% for r in stats.recent[-15:]|reverse %}
  <div class="row"><span>👤 {{ r.name }}</span>
    <span class="meta">{{ r.ip }} · {{ r.time }}</span></div>
  {% endfor %}
</div>

<div class="box">
  <h2>💬 آخر 20 رسالة</h2>
  {% for m in stats.messages_log[-20:]|reverse %}
  <div class="msg-item">
    <div class="meta"><span>{{ m.user }} · {{ m.mode }}</span><span>{{ m.time }}</span></div>
    <div>{{ m.text }}</div>
  </div>
  {% endfor %}
</div>

<div class="box">
  <h2>🚫 عناوين IP محظورة</h2>
  {% if blocked %}
    {% for ip in blocked %}
    <div class="row"><span>🌐 {{ ip }}</span>
      <a class="unblock" href="/admin/unblock/{{ ip }}?key={{ key }}">إلغاء الحظر</a></div>
    {% endfor %}
  {% else %}
    <div class="row"><span class="meta">لا يوجد أحد محظور</span></div>
  {% endif %}
</div>
</body>
</html>'''


# ============================================================
#  🚀 التشغيل
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Moka AI v21.0 يعمل على http://0.0.0.0:{port}")
    print(f"   المطوّر: محمد كامل")
    print(f"   المزودون: {[p['name'] for p in PROVIDERS if p['key']]}")
    app.run(host="0.0.0.0", port=port, debug=False)
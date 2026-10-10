# -*- coding: utf-8 -*-
# ============================================================
#  Moka AI v26.0 - نهائي
#  المطور: محمد كامل
# ============================================================

import os, re, json, time, hashlib, secrets
import urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from functools import wraps
from collections import defaultdict

from flask import (Flask, request, jsonify, render_template_string,
                   session, redirect, url_for)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# ============ المدير ============
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "kameladmin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "KamelDz2026Prime")
ADMIN_KEY      = os.environ.get("ADMIN_KEY",      "mokaadmin2026")
SECRET_SALT    = os.environ.get("SECRET_SALT",    "mokasalt2026kamel")

# ============ Groq API ============
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

# ✅ النماذج المتاحة (بالأولوية)
GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

# ============ الملفات ============
DATA_DIR     = os.path.dirname(os.path.abspath(__file__))
USERS_FILE   = os.path.join(DATA_DIR, "users.json")
STATS_FILE   = os.path.join(DATA_DIR, "stats.json")
BLOCKED_FILE = os.path.join(DATA_DIR, "blocked.json")

BLOCKED_IPS = set()
RATE_LIMITS = defaultdict(list)
SESSIONS    = {}

# ============ دوال التخزين ============
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
    return hashlib.sha256((pw + SECRET_SALT).encode("utf-8")).hexdigest()

# ============ المستخدمون ============
USERS = load_json(USERS_FILE, {})

if ADMIN_USERNAME not in USERS:
    USERS[ADMIN_USERNAME] = {
        "password": hash_pw(ADMIN_PASSWORD),
        "name": "محمد كامل",
        "role": "admin",
        "created": datetime.now().isoformat(),
    }
    save_json(USERS_FILE, USERS)

# ============ الإحصائيات ============
DEFAULT_STATS = {
    "visitors": 0, "logins": 0, "registrations": 0, "messages": 0,
    "images_generated": 0, "voice_used": 0,
    "modes": {m: 0 for m in ["general","math","code","religion",
                              "translate","summary","creative","science"]},
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

# ============ دوال مساعدة ============
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
            f"{d.year} - {d.strftime('%H:%M')} (GMT+1)")

def rate_limit(max_calls=20, window=60):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            ip = get_ip()
            now = time.time()
            RATE_LIMITS[ip] = [t for t in RATE_LIMITS[ip] if now - t < window]
            if len(RATE_LIMITS[ip]) >= max_calls:
                return jsonify({"reply": "ارسلت رسائل كثيرة. انتظر."}), 429
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
            return "مرفوض", 403
        return fn(*a, **kw)
    return wrapper

# ============ بحث ويكيبيديا ============
def search_wikipedia(query):
    try:
        url = ("https://ar.wikipedia.org/w/api.php?action=query&list=search&srsearch="
               + urllib.parse.quote(query) + "&format=json&utf8=1&srlimit=1")
        req = urllib.request.Request(url, headers={"User-Agent": "MokaAI/26.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        hits = data.get("query", {}).get("search", [])
        if not hits: return None
        title = hits[0]["title"]
        sum_url = ("https://ar.wikipedia.org/api/rest_v1/page/summary/"
                   + urllib.parse.quote(title))
        req2 = urllib.request.Request(sum_url, headers={"User-Agent": "MokaAI/26.0"})
        with urllib.request.urlopen(req2, timeout=8) as r2:
            sdata = json.loads(r2.read().decode("utf-8"))
        extract = sdata.get("extract", "")
        return f"معلومات من ويكيبيديا ({title}):\n{extract[:700]}" if extract else None
    except Exception:
        return None

# ============ رسائل النظام ============
OWNER_INFO = """
معلومات المطور:
- الاسم: محمد كامل
- العمر: 15 سنة
- الجنسية: جزائري
- المشروع: Moka AI
"""

RULES = """
قواعد الهوية - إلزامية:
1. إذا سئلت "من صنعك؟" اجب: "طورني محمد كامل."
2. ممنوع ذكر اي شركة تقنية او اسماء نماذج اخرى.
3. اسمك Moka AI.
4. ممنوع تماما الرد على اي سؤال جنسي او اباحي او عنيف.
5. رفض المحتوى الضار او الكراهية.

اللغة: اجب بنفس لغة السؤال.
التنسيق: ممنوع LaTeX. استخدم **غامق** و - للقوائم. للكود ```.
الشخصية: ذكي، مختصر، ودود، محترم.
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
    text = text.replace("\\text", "").replace("\\displaystyle", "")
    return text.strip()

# ============ استدعاء AI ============
def call_ai(messages, mode="general", max_tokens=1500):
    if not GROQ_API_KEY:
        print("[AI] ERROR: GROQ_API_KEY فارغ!")
        return "مفتاح API غير مضبوط. أضف GROQ_API_KEY في Environment."

    system = build_system(mode)
    full = [{"role": "system", "content": system}] + messages[-20:]

    last_error = ""
    for model in GROQ_MODELS:
        try:
            payload = json.dumps({
                "model": model,
                "messages": full,
                "temperature": 0.7,
                "max_tokens": max_tokens,
            }).encode("utf-8")

            req = urllib.request.Request(
                GROQ_URL, data=payload,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "MokaAI/26.0",
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))

            reply = data["choices"][0]["message"]["content"].strip()
            if reply:
                print(f"[AI] OK | model={model} | len={len(reply)}")
                return clean_reply(reply)

        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")[:200]
            except Exception:
                err_body = ""
            last_error = f"HTTP {e.code}"
            print(f"[AI] FAIL | {model} | {last_error}: {err_body}")
            continue

        except Exception as e:
            last_error = f"{type(e).__name__}"
            print(f"[AI] FAIL | {model} | {last_error}: {str(e)[:150]}")
            continue

    return "⚠️ تعذر الاتصال بالخدمة. حاول مرة أخرى."

# ============ Routes ============

@app.route("/")
def index():
    STATS["visitors"] = STATS.get("visitors", 0) + 1
    save_stats()
    if get_ip() in BLOCKED_IPS:
        return "🚫 تم حظر وصولك.", 403
    return render_template_string(HTML_APP)


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    u = data.get("username", "").strip()
    p = data.get("password", "")
    n = data.get("name", "").strip() or u

    if not u or not p:
        return jsonify({"ok": False, "msg": "أدخل اسم المستخدم وكلمة السر"}), 400
    if len(u) < 3 or len(u) > 30:
        return jsonify({"ok": False, "msg": "الاسم بين 3 و 30 حرف"}), 400
    if len(p) < 6:
        return jsonify({"ok": False, "msg": "كلمة السر 6 أحرف على الأقل"}), 400
    if not re.match(r"^[a-zA-Z0-9_]+$", u):
        return jsonify({"ok": False, "msg": "الاسم بحروف إنجليزية وأرقام فقط"}), 400
    if u == ADMIN_USERNAME:
        return jsonify({"ok": False, "msg": "هذا الاسم محجوز"}), 403
    if u in USERS:
        return jsonify({"ok": False, "msg": "الاسم موجود مسبقًا"}), 409

    USERS[u] = {
        "password": hash_pw(p),
        "name": n[:40],
        "role": "user",
        "created": datetime.now().isoformat(),
        "ip": get_ip()[:15],
    }
    save_users()

    STATS["registrations"] = STATS.get("registrations", 0) + 1
    save_stats()

    session["user"] = u
    session["role"] = "user"
    session["name"] = USERS[u]["name"]
    session["sid"] = secrets.token_hex(8)

    return jsonify({"ok": True, "name": USERS[u]["name"], "role": "user"})


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

    # توليد صورة
    if msg.startswith("/صورة ") or msg.startswith("/image "):
        prompt = msg.split(" ", 1)[1].strip()
        if prompt:
            STATS["images_generated"] = STATS.get("images_generated", 0) + 1
            save_stats()
            encoded = urllib.parse.quote(prompt)
            img_url = (f"https://image.pollinations.ai/prompt/{encoded}"
                       f"?width=768&height=768&nologo=true&seed={int(time.time())}")
            return jsonify({
                "reply": f"تم توليد الصورة: **{prompt}**",
                "image": img_url
            })

    conv = SESSIONS.setdefault(sid, [])
    conv.append({"role": "user", "content": msg})

    # بحث تلقائي
    extra = ""
    wiki_kw = ["ما هو", "ما هي", "من هو", "من هي", "تاريخ", "دولة",
               "عاصمة", "تعريف", "معلومات", "أين", "متى"]
    if any(k in msg for k in wiki_kw) and len(msg) > 8:
        w = search_wikipedia(msg)
        if w:
            extra += f"\n\n[معلومات إضافية]\n{w}"
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


@app.route("/api/voice_used", methods=["POST"])
@login_required
def api_voice_used():
    STATS["voice_used"] = STATS.get("voice_used", 0) + 1
    save_stats()
    return jsonify({"ok": True})


@app.route("/admin")
def admin():
    if not session.get("user"):
        return "سجل الدخول أولا", 403
    if session.get("role") != "admin":
        return "للمدير فقط", 403
    if request.args.get("key") != ADMIN_KEY:
        return "مفتاح الإدارة مطلوب", 403
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

# ============ HTML الرئيسية ============

HTML_APP = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Moka AI - مساعدك الذكي</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0a12;--card:rgba(24,24,38,.85);--border:rgba(255,255,255,.08);--text:#e8e8f0;--muted:#8b8ba8;--primary:#8b5cf6;--accent:#06b6d4;}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:Cairo,system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}
.bg{position:fixed;inset:0;z-index:-1;overflow:hidden;pointer-events:none}
.bg::before,.bg::after{content:"";position:absolute;border-radius:50%;filter:blur(110px);opacity:.4}
.bg::before{width:520px;height:520px;background:linear-gradient(135deg,#8b5cf6,#ec4899);top:-160px;right:-160px;animation:f1 22s ease-in-out infinite}
.bg::after{width:420px;height:420px;background:linear-gradient(135deg,#06b6d4,#8b5cf6);bottom:-160px;left:-160px;animation:f2 26s ease-in-out infinite}
@keyframes f1{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(-70px,70px) scale(1.18)}}
@keyframes f2{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(70px,-70px) scale(1.15)}}
#login{position:fixed;inset:0;z-index:999;background:rgba(10,10,20,.88);backdrop-filter:blur(20px);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px;gap:12px;overflow-y:auto}
.logo-big{width:100px;height:100px;border-radius:28px;background:linear-gradient(135deg,#8b5cf6,#ec4899,#06b6d4);display:grid;place-items:center;font-size:46px;font-weight:900;color:#fff;box-shadow:0 20px 60px rgba(139,92,246,.5);animation:float 3.5s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}
.brand-title{font-size:38px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;background-clip:text;color:transparent}
.brand-sub{color:var(--muted);font-size:13px;margin-top:-6px;margin-bottom:8px}
.tabs{display:flex;gap:6px;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:5px;margin-bottom:10px;width:100%;max-width:340px}
.tabs button{flex:1;padding:10px;border:none;background:transparent;color:var(--muted);font-family:inherit;font-size:14px;font-weight:700;cursor:pointer;border-radius:10px}
.tabs button.on{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff}
.login-form{width:100%;max-width:340px;display:flex;flex-direction:column;gap:10px}
.login-form input{width:100%;padding:14px 16px;border-radius:14px;border:2px solid var(--border);background:var(--card);color:var(--text);font-size:15px;font-family:inherit;outline:none}
.login-form input:focus{border-color:var(--primary)}
.login-form button.submit{padding:15px;border-radius:14px;border:none;background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;font-size:15px;font-weight:800;font-family:inherit;cursor:pointer;transition:transform .15s}
.login-form button.submit:active{transform:scale(.97)}
.login-form button.submit:disabled{opacity:.6}
.err{color:#f87171;font-size:12px;text-align:center;min-height:16px}
#app{display:none;min-height:100vh;flex-direction:column}
#app.on{display:flex}
.hd{display:flex;align-items:center;gap:10px;padding:12px 14px;background:var(--card);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:50}
.hd-logo{width:40px;height:40px;border-radius:13px;background:linear-gradient(135deg,#8b5cf6,#ec4899);display:grid;place-items:center;font-size:20px;font-weight:900;color:#fff;flex-shrink:0}
.hd h1{font-size:17px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;background-clip:text;color:transparent}
.hd .sub{font-size:10px;color:var(--muted)}
.hd-actions{margin-inline-start:auto;display:flex;gap:5px}
.hd-actions button{width:38px;height:38px;border-radius:12px;border:none;background:rgba(255,255,255,.06);color:var(--text);cursor:pointer;font-size:16px;display:grid;place-items:center}
.hd-actions button.voice-on{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff}
#ch{flex:1;overflow-y:auto;padding:20px 14px 220px;display:flex;flex-direction:column;gap:14px}
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:50px 20px;min-height:55vh}
.welcome .lg{width:90px;height:90px;border-radius:26px;background:linear-gradient(135deg,#8b5cf6,#ec4899,#06b6d4);display:grid;place-items:center;font-size:42px;font-weight:900;color:#fff;animation:float 3.5s ease-in-out infinite}
.welcome h2{font-size:24px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;background-clip:text;color:transparent}
.welcome p{color:var(--muted);font-size:14px;max-width:320px;line-height:1.8}
.quick-chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;max-width:420px}
.quick-chips button{padding:9px 16px;border-radius:14px;border:1px solid var(--border);background:var(--card);color:var(--text);font-family:inherit;font-size:13px;font-weight:600;cursor:pointer}
.mw{display:flex;max-width:92%;animation:msgIn .35s}
@keyframes msgIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.mw.u{align-self:flex-start}
.mw.b{align-self:flex-end}
.m{padding:14px 18px;border-radius:20px;line-height:1.85;white-space:pre-wrap;word-wrap:break-word;font-size:15px;position:relative}
.u .m{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;border-bottom-right-radius:6px}
.b .m{background:var(--card);color:var(--text);border:1px solid var(--border);border-bottom-left-radius:6px}
.b .m pre{background:#000;color:#e8e8f0;padding:14px;border-radius:14px;overflow-x:auto;direction:ltr;text-align:left;margin:10px 0;font-size:13px}
.b .m code{background:rgba(139,92,246,.18);padding:2px 7px;border-radius:6px;font-family:monospace}
.b .m img{max-width:100%;border-radius:14px;margin-top:8px;display:block}
.msg-actions{display:flex;gap:4px;opacity:0;transition:opacity .2s;margin-top:4px}
.mw:hover .msg-actions{opacity:1}
.msg-actions button{background:rgba(255,255,255,.06);border:1px solid var(--border);color:var(--muted);padding:4px 10px;border-radius:8px;font-size:11px;font-family:inherit;cursor:pointer}
.tp{display:flex;gap:5px;padding:14px 18px}
.tp span{width:8px;height:8px;border-radius:50%;background:var(--primary);animation:bnc 1.2s infinite}
.tp span:nth-child(2){animation-delay:.15s}
.tp span:nth-child(3){animation-delay:.3s}
@keyframes bnc{0%,60%,100%{transform:translateY(0);opacity:.35}30%{transform:translateY(-6px);opacity:1}}
.input-area{position:fixed;bottom:0;left:0;right:0;padding:12px 14px 16px;background:linear-gradient(to top,var(--bg) 60%,transparent);z-index:40}
.modes{display:flex;gap:6px;margin-bottom:10px;overflow-x:auto;padding-bottom:6px}
.modes button{background:var(--card);border:1px solid var(--border);color:var(--muted);padding:8px 14px;border-radius:12px;font-size:12px;font-family:inherit;font-weight:700;cursor:pointer;white-space:nowrap}
.modes button.on{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;border-color:transparent}
.input-box{display:flex;align-items:flex-end;gap:8px;background:var(--card);border:1px solid var(--border);border-radius:22px;padding:8px}
#i{flex:1;resize:none;border:none;outline:none;background:transparent;color:var(--text);padding:10px 14px;font-family:inherit;font-size:15px;max-height:140px}
.btn-mic{width:44px;height:44px;border-radius:14px;border:none;background:rgba(255,255,255,.08);color:var(--text);font-size:18px;cursor:pointer;display:grid;place-items:center;flex-shrink:0}
.btn-mic.rec{background:#dc2626;color:#fff}
#s{width:44px;height:44px;border:none;border-radius:14px;background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;font-size:18px;cursor:pointer;display:grid;place-items:center}
#s:disabled{opacity:.4}
.modal{position:fixed;inset:0;background:rgba(10,10,20,.9);backdrop-filter:blur(20px);z-index:999;display:none;flex-direction:column;padding:24px;overflow-y:auto}
.modal.on{display:flex}
.modal h2{font-size:22px;font-weight:900;margin-bottom:16px;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;background-clip:text;color:transparent}
.setting{margin-bottom:16px}
.setting label{font-size:13px;color:var(--muted);display:block;margin-bottom:6px;font-weight:600}
.setting select,.setting input[type=range]{width:100%;padding:12px;border-radius:12px;border:1px solid var(--border);background:var(--card);color:var(--text);font-family:inherit;font-size:14px;outline:none}
.voice-test{padding:12px;border-radius:12px;border:none;background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;font-family:inherit;font-weight:700;cursor:pointer;width:100%;margin-top:6px}
.modal-close{position:absolute;top:16px;left:16px;width:40px;height:40px;border-radius:12px;border:none;background:var(--card);color:var(--text);font-size:20px;cursor:pointer}
</style>
</head>
<body>
<div class="bg"></div>

<div id="login">
  <div class="logo-big">M</div>
  <div class="brand-title">Moka AI</div>
  <div class="brand-sub">من تطوير محمد كامل</div>

  <div class="tabs">
    <button id="tabLogin" class="on" onclick="showTab('login')">دخول</button>
    <button id="tabReg" onclick="showTab('reg')">حساب جديد</button>
  </div>

  <div class="login-form" id="formLogin">
    <input id="lu" placeholder="اسم المستخدم" autocomplete="username">
    <input id="lp" type="password" placeholder="كلمة السر" autocomplete="current-password">
    <button class="submit" id="loginBtn" onclick="doLogin()">دخول</button>
  </div>

  <div class="login-form" id="formReg" style="display:none">
    <input id="ru" placeholder="اسم المستخدم (انجليزي)" autocomplete="username">
    <input id="rn" placeholder="الاسم الكامل (اختياري)">
    <input id="rp" type="password" placeholder="كلمة السر (6 احرف)" autocomplete="new-password">
    <input id="rp2" type="password" placeholder="تأكيد كلمة السر" autocomplete="new-password">
    <button class="submit" id="regBtn" onclick="doRegister()">انشاء الحساب</button>
  </div>

  <div class="err" id="err"></div>
</div>

<div id="app">
  <div class="hd">
    <div class="hd-logo">M</div>
    <div>
      <h1>Moka AI</h1>
      <div class="sub" id="userInfo">من تطوير محمد كامل</div>
    </div>
    <div class="hd-actions">
      <button id="voiceBtn" onclick="toggleVoice()">&#128263;</button>
      <button onclick="openSettings()">&#9881;</button>
      <button onclick="openSidebar()">&#9776;</button>
    </div>
  </div>

  <div id="ch"></div>

  <div class="input-area">
    <div class="modes">
      <button class="on" data-m="general" onclick="sw('general')">عامة</button>
      <button data-m="math" onclick="sw('math')">رياضيات</button>
      <button data-m="code" onclick="sw('code')">برمجة</button>
      <button data-m="religion" onclick="sw('religion')">دين</button>
      <button data-m="translate" onclick="sw('translate')">ترجمة</button>
      <button data-m="summary" onclick="sw('summary')">ملخص</button>
      <button data-m="creative" onclick="sw('creative')">ابداع</button>
      <button data-m="science" onclick="sw('science')">علوم</button>
    </div>
    <div class="input-box">
      <button class="btn-mic" id="micBtn" onclick="toggleMic()">&#127908;</button>
      <textarea id="i" rows="1" placeholder="اكتب... او /صورة قطة"></textarea>
      <button id="s" onclick="send()">&#10148;</button>
    </div>
  </div>
</div>

<div class="modal" id="settingsModal">
  <button class="modal-close" onclick="closeSettings()">&#10005;</button>
  <h2>إعدادات الصوت</h2>
  <div class="setting">
    <label>الصوت</label>
    <select id="voiceSelect"></select>
  </div>
  <div class="setting">
    <label>السرعة: <span id="speedVal">1.0</span></label>
    <input type="range" id="speedRange" min="0.5" max="2" step="0.1" value="1">
  </div>
  <div class="setting">
    <label>النغمة: <span id="pitchVal">1.0</span></label>
    <input type="range" id="pitchRange" min="0.5" max="2" step="0.1" value="1">
  </div>
  <button class="voice-test" onclick="testVoice()">تجربة الصوت</button>
</div>

<script>
let mode="general",history=[],isAdmin=false,isSending=false,userName="";
let voiceEnabled=false;

const ch=document.getElementById("ch"),i=document.getElementById("i"),
      s=document.getElementById("s"),errEl=document.getElementById("err"),
      micBtn=document.getElementById("micBtn"),voiceBtn=document.getElementById("voiceBtn");

function showTab(t){
  const isL=t==="login";
  document.getElementById("tabLogin").classList.toggle("on",isL);
  document.getElementById("tabReg").classList.toggle("on",!isL);
  document.getElementById("formLogin").style.display=isL?"flex":"none";
  document.getElementById("formReg").style.display=isL?"none":"flex";
  errEl.textContent="";
}
function setErr(t){errEl.textContent=t;setTimeout(function(){errEl.textContent=""},4000)}

function esc(t){return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function md(t){
  let h=esc(t);
  h=h.replace(/```(\w*)\n([\s\S]*?)```/g,function(_,l,c){return "<pre><code>"+c+"</code></pre>"});
  h=h.replace(/`([^`]+)`/g,"<code>$1</code>");
  h=h.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>");
  h=h.replace(/\n/g,"<br>");
  return h;
}
function addMsg(text,who,imageUrl){
  const w=document.createElement("div");w.className="mw "+who;
  const m=document.createElement("div");m.className="m";
  m.innerHTML=who==="b"?md(text):esc(text);
  if(imageUrl){
    const img=document.createElement("img");
    img.src=imageUrl;img.alt="صورة";
    m.appendChild(img);
  }
  w.appendChild(m);
  if(who==="b"){
    const actions=document.createElement("div");actions.className="msg-actions";
    const b1=document.createElement("button");b1.textContent="نسخ";
    b1.onclick=function(){navigator.clipboard.writeText(text)};
    const b2=document.createElement("button");b2.textContent="سماع";
    b2.onclick=function(){var o=voiceEnabled;voiceEnabled=true;speak(text);voiceEnabled=o};
    actions.appendChild(b1);actions.appendChild(b2);
    w.appendChild(actions);
  }
  ch.appendChild(w);ch.scrollTop=ch.scrollHeight;
}
function typ(){
  const w=document.createElement("div");w.className="mw b";w.id="tp";
  w.innerHTML='<div class="m tp"><span></span><span></span><span></span></div>';
  ch.appendChild(w);ch.scrollTop=ch.scrollHeight;return w;
}
function welcome(){
  ch.innerHTML='<div class="welcome"><div class="lg">M</div>'+
    '<h2>مرحبا '+(userName||"بك")+'</h2>'+
    '<p>مساعدك الذكي من تطوير محمد كامل.<br>💡 جرب: /صورة قطة</p>'+
    '<div class="quick-chips">'+
    '<button onclick="quick(\'اشرح الثقوب السوداء\')">الثقوب السوداء</button>'+
    '<button onclick="quick(\'اكتب كود Python للفرز\')">كود Python</button>'+
    '<button onclick="quick(\'/صورة غروب على البحر\')">صورة غروب</button>'+
    '</div></div>';
}
function quick(t){i.value=t;send()}

function initVoices(){
  if(!("speechSynthesis" in window))return;
  const sel=document.getElementById("voiceSelect");
  const voices=speechSynthesis.getVoices();
  const arabic=voices.filter(function(v){return v.lang.startsWith("ar")});
  const others=voices.filter(function(v){return !v.lang.startsWith("ar")});
  sel.innerHTML="";
  arabic.concat(others).forEach(function(v,idx){
    const opt=document.createElement("option");
    opt.value=idx;opt.textContent=v.name+" ("+v.lang+")";
    opt.dataset.voiceName=v.name;
    sel.appendChild(opt);
  });
}
if("speechSynthesis" in window){
  speechSynthesis.onvoiceschanged=initVoices;
  setTimeout(initVoices,100);
}

function toggleVoice(){
  voiceEnabled=!voiceEnabled;
  voiceBtn.classList.toggle("voice-on",voiceEnabled);
  voiceBtn.innerHTML=voiceEnabled?"&#128266;":"&#128263;";
  if(voiceEnabled){
    fetch("/api/voice_used",{method:"POST"});
    speak("تم تفعيل الصوت");
  } else {
    speechSynthesis.cancel();
  }
}
function cleanForSpeech(t){
  return t.replace(/```[\s\S]*?```/g,"").replace(/`([^`]+)`/g,"$1")
          .replace(/\*\*/g,"").replace(/[#*_]/g,"").slice(0,500);
}
function speak(text){
  if(!voiceEnabled)return;
  if(!("speechSynthesis" in window))return;
  speechSynthesis.cancel();
  const clean=cleanForSpeech(text);
  if(!clean)return;
  const u=new SpeechSynthesisUtterance(clean);
  const sel=document.getElementById("voiceSelect");
  const chosen=sel.options[sel.selectedIndex];
  if(chosen && chosen.dataset.voiceName){
    const v=speechSynthesis.getVoices().find(function(vv){return vv.name===chosen.dataset.voiceName});
    if(v)u.voice=v;
    u.lang=v?v.lang:"ar-SA";
  } else {u.lang="ar-SA";}
  u.rate=parseFloat(document.getElementById("speedRange").value)||1;
  u.pitch=parseFloat(document.getElementById("pitchRange").value)||1;
  speechSynthesis.speak(u);
}
function openSettings(){document.getElementById("settingsModal").classList.add("on");initVoices();}
function closeSettings(){document.getElementById("settingsModal").classList.remove("on");}
document.getElementById("speedRange").addEventListener("input",function(e){
  document.getElementById("speedVal").textContent=e.target.value;
});
document.getElementById("pitchRange").addEventListener("input",function(e){
  document.getElementById("pitchVal").textContent=e.target.value;
});
function testVoice(){
  var o=voiceEnabled;voiceEnabled=true;speak("مرحبا، أنا Moka AI من تطوير محمد كامل.");voiceEnabled=o;
}

let recognition=null;
function toggleMic(){
  if(!("webkitSpeechRecognition" in window)&&!("SpeechRecognition" in window)){
    alert("المتصفح لا يدعم المايك");return;
  }
  if(recognition){recognition.stop();return}
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  recognition=new SR();recognition.lang="ar-SA";
  recognition.onstart=function(){micBtn.classList.add("rec")};
  recognition.onend=function(){micBtn.classList.remove("rec");recognition=null};
  recognition.onerror=function(){micBtn.classList.remove("rec");recognition=null};
  recognition.onresult=function(e){i.value+=(i.value?" ":"")+e.results[0][0].transcript;i.focus()};
  recognition.start();
}

async function doLogin(){
  const u=document.getElementById("lu").value.trim();
  const p=document.getElementById("lp").value;
  if(!u||!p){setErr("املأ الحقول");return}
  const btn=document.getElementById("loginBtn");
  btn.disabled=true;btn.textContent="...";
  try{
    const r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({username:u,password:p})});
    const d=await r.json();
    if(!d.ok){setErr(d.msg);btn.disabled=false;btn.textContent="دخول";return}
    enterApp(d.name,d.role);
  }catch(e){setErr("تعذر الاتصال");btn.disabled=false;btn.textContent="دخول"}
}
async function doRegister(){
  const u=document.getElementById("ru").value.trim();
  const n=document.getElementById("rn").value.trim();
  const p=document.getElementById("rp").value;
  const p2=document.getElementById("rp2").value;
  if(!u||!p){setErr("املأ الحقول");return}
  if(p!==p2){setErr("كلمتا السر مختلفتان");return}
  if(p.length<6){setErr("6 احرف على الاقل");return}
  const btn=document.getElementById("regBtn");
  btn.disabled=true;btn.textContent="...";
  try{
    const r=await fetch("/api/register",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({username:u,password:p,name:n})});
    const d=await r.json();
    if(!d.ok){setErr(d.msg);btn.disabled=false;btn.textContent="انشاء الحساب";return}
    enterApp(d.name,d.role);
  }catch(e){setErr("تعذر الاتصال");btn.disabled=false;btn.textContent="انشاء الحساب"}
}
function enterApp(name,role){
  userName=name;isAdmin=role==="admin";
  document.getElementById("login").style.display="none";
  document.getElementById("app").classList.add("on");
  document.getElementById("userInfo").textContent="مرحبا "+name+(isAdmin?" (مدير)":"");
  welcome();i.focus();
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
    const reply=d.reply||"لا يوجد رد.";
    addMsg(reply,"b",d.image||null);
    history.push({role:"assistant",content:reply});
    if(voiceEnabled && !d.image){speak(reply);}
  }catch(e){tp.remove();addMsg("تعذر الاتصال","b")}
  finally{isSending=false;s.disabled=false;i.focus()}
}
function sw(m){mode=m;document.querySelectorAll(".modes button").forEach(function(b){
  b.classList.toggle("on",b.dataset.m===m)})}
function openSidebar(){
  const a=["مسح المحادثة"];
  if(isAdmin)a.push("لوحة الإدارة");
  a.push("تصدير المحادثة","تسجيل الخروج");
  const c=prompt("اختر رقما:\n"+a.map(function(x,n){return (n+1)+". "+x}).join("\n"));
  const idx=parseInt(c)-1,ch2=a[idx];
  if(!ch2)return;
  if(ch2==="مسح المحادثة"){if(confirm("مسح؟")){history=[];fetch("/api/clear",{method:"POST"});welcome()}}
  else if(ch2==="لوحة الإدارة"){const k=prompt("مفتاح اللوحة:");if(k)window.open("/admin?key="+k,"_blank")}
  else if(ch2==="تصدير المحادثة"){
    const txt=history.map(function(m){return "["+(m.role==="user"?"أنا":"Moka")+"] "+m.content}).join("\n\n");
    const bl=new Blob([txt],{type:"text/plain;charset=utf-8"});
    const a2=document.createElement("a");a2.href=URL.createObjectURL(bl);
    a2.download="moka-"+Date.now()+".txt";a2.click();
  } else if(ch2==="تسجيل الخروج"){if(confirm("خروج؟"))fetch("/api/logout",{method:"POST"}).then(function(){location.reload()})}
}
i.addEventListener("keydown",function(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}});
i.addEventListener("input",function(){i.style.height="auto";i.style.height=Math.min(i.scrollHeight,140)+"px"});
document.getElementById("lp").addEventListener("keydown",function(e){if(e.key==="Enter")doLogin()});
document.getElementById("rp2").addEventListener("keydown",function(e){if(e.key==="Enter")doRegister()});
</script>
</body>
</html>'''


# ============ HTML لوحة الإدارة ============

HTML_ADMIN = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>لوحة الإدارة</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800;900&display=swap" rel="stylesheet">
<style>
body{font-family:Cairo;background:#0a0a12;color:#e8e8f0;padding:22px;min-height:100vh}
h1{font-size:26px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:6px}
.sub{color:#8b8ba8;font-size:13px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:14px;margin-bottom:22px}
.card{background:rgba(24,24,38,.85);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:20px;text-align:center}
.num{font-size:30px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;background-clip:text;color:transparent}
.lbl{font-size:12px;color:#8b8ba8;margin-top:6px}
.box{background:rgba(24,24,38,.85);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:18px;margin-bottom:16px}
.box h2{font-size:16px;font-weight:800;margin-bottom:12px}
.row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:14px;gap:10px;flex-wrap:wrap}
.row:last-child{border-bottom:none}
.row .meta{color:#8b8ba8;font-size:12px}
.badge{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:800}
.badge.user{background:linear-gradient(135deg,#22c55e,#16a34a)}
.msg-item{padding:10px;background:rgba(0,0,0,.2);border-radius:12px;margin-bottom:6px;font-size:13px}
.msg-item .meta{display:flex;justify-content:space-between;color:#8b8ba8;font-size:11px;margin-bottom:4px}
a.back{display:inline-block;color:#8b5cf6;text-decoration:none;font-weight:800;margin-bottom:16px}
a.unblock{background:#22c55e;color:#fff;padding:4px 10px;border-radius:8px;font-size:11px;text-decoration:none;font-weight:800}
</style>
</head>
<body>
<a href="/" class="back">← رجوع</a>
<h1>لوحة الإدارة</h1>
<div class="sub">من تطوير محمد كامل</div>

<div class="grid">
  <div class="card"><div class="num">{{ stats.visitors }}</div><div class="lbl">زيارات</div></div>
  <div class="card"><div class="num">{{ stats.logins }}</div><div class="lbl">تسجيلات</div></div>
  <div class="card"><div class="num">{{ stats.registrations }}</div><div class="lbl">حسابات جديدة</div></div>
  <div class="card"><div class="num">{{ stats.messages }}</div><div class="lbl">رسائل</div></div>
  <div class="card"><div class="num">{{ stats.images_generated }}</div><div class="lbl">صور</div></div>
  <div class="card"><div class="num">{{ stats.voice_used }}</div><div class="lbl">صوت</div></div>
  <div class="card"><div class="num">{{ users|length }}</div><div class="lbl">مستخدمين</div></div>
</div>

<div class="box">
  <h2>الأنماط</h2>
  {% for k, v in stats.modes.items() %}
  <div class="row"><span>{{ k }}</span><b>{{ v }}</b></div>
  {% endfor %}
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

<div class="box">
  <h2>تسجيلات حديثة</h2>
  {% for r in stats.recent[-15:]|reverse %}
  <div class="row"><span>{{ r.name }}</span>
    <span class="meta">{{ r.ip }} - {{ r.time }}</span></div>
  {% endfor %}
</div>

<div class="box">
  <h2>آخر 20 رسالة</h2>
  {% for m in stats.messages_log[-20:]|reverse %}
  <div class="msg-item">
    <div class="meta"><span>{{ m.user }} - {{ m.mode }}</span><span>{{ m.time }}</span></div>
    <div>{{ m.text }}</div>
  </div>
  {% endfor %}
</div>

<div class="box">
  <h2>IP محظورة</h2>
  {% if blocked %}
    {% for ip in blocked %}
    <div class="row"><span>{{ ip }}</span>
      <a class="unblock" href="/admin/unblock/{{ ip }}?key={{ key }}">الغاء الحظر</a></div>
    {% endfor %}
  {% else %}
    <div class="row"><span class="meta">لا يوجد</span></div>
  {% endif %}
</div>
</body>
</html>'''


# ============ التشغيل ============

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("Moka AI v26.0 - نهائي")
    print("المطور: محمد كامل")
    print("المدير: " + ADMIN_USERNAME)
    print("Groq Key: " + ("موجود" if GROQ_API_KEY else "مفقود!"))
    print("النموذج الأساسي: " + GROQ_MODELS[0])
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)
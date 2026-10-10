# -*- coding: utf-8 -*-
# ============================================================
#  Moka AI v28.0 - Professional Edition
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

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "kameladmin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "KamelDz2026Prime")
ADMIN_KEY      = os.environ.get("ADMIN_KEY",      "mokaadmin2026")
SECRET_SALT    = os.environ.get("SECRET_SALT",    "mokasalt2026kamel")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "llama-3.3-70b-versatile",
]

DATA_DIR     = os.path.dirname(os.path.abspath(__file__))
USERS_FILE   = os.path.join(DATA_DIR, "users.json")
STATS_FILE   = os.path.join(DATA_DIR, "stats.json")
BLOCKED_FILE = os.path.join(DATA_DIR, "blocked.json")

BLOCKED_IPS = set()
RATE_LIMITS = defaultdict(list)
SESSIONS    = {}
BOOKS       = {}

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
        print("[save_json] " + str(e))

def hash_pw(pw):
    return hashlib.sha256((pw + SECRET_SALT).encode("utf-8")).hexdigest()

USERS = load_json(USERS_FILE, {})
if ADMIN_USERNAME not in USERS:
    USERS[ADMIN_USERNAME] = {
        "password": hash_pw(ADMIN_PASSWORD),
        "name": "محمد كامل",
        "role": "admin",
        "created": datetime.now().isoformat(),
    }
    save_json(USERS_FILE, USERS)

DEFAULT_STATS = {
    "visitors": 0, "logins": 0, "registrations": 0, "messages": 0,
    "images_generated": 0, "voice_used": 0, "books_generated": 0,
    "modes": {m: 0 for m in ["general","write","code","math","translate",
                              "summary","religion","science"]},
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

def rate_limit(max_calls=30, window=60):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            ip = get_ip()
            now = time.time()
            RATE_LIMITS[ip] = [t for t in RATE_LIMITS[ip] if now - t < window]
            if len(RATE_LIMITS[ip]) >= max_calls:
                return jsonify({"reply": "ارسلت رسائل كثيرة."}), 429
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

def search_wikipedia(query):
    try:
        url = ("https://ar.wikipedia.org/w/api.php?action=query&list=search&srsearch="
               + urllib.parse.quote(query) + "&format=json&utf8=1&srlimit=1")
        req = urllib.request.Request(url, headers={"User-Agent": "MokaAI/28.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        hits = data.get("query", {}).get("search", [])
        if not hits: return None
        title = hits[0]["title"]
        sum_url = ("https://ar.wikipedia.org/api/rest_v1/page/summary/"
                   + urllib.parse.quote(title))
        req2 = urllib.request.Request(sum_url, headers={"User-Agent": "MokaAI/28.0"})
        with urllib.request.urlopen(req2, timeout=8) as r2:
            sdata = json.loads(r2.read().decode("utf-8"))
        extract = sdata.get("extract", "")
        return f"معلومات ({title}):\n{extract[:600]}" if extract else None
    except Exception:
        return None

# ============ هوية النظام ============
OWNER_INFO = """
معلومات المطور:
- الاسم: محمد كامل
- الجنسية: جزائري
- المشروع: Moka AI
"""

RULES = """
قواعد الهوية - إلزامية:
1. إذا سئلت "من صنعك؟" اجب: "طورني محمد كامل."
2. إذا سئلت "من أنا؟" أو "هل تعرفني؟":
   اجب: "أنت محمد كامل، مطوري وصاحب هذا المشروع."
3. إذا قال المستخدم "أنا محمد كامل":
   رحب به بحرارة: "أهلاً بك يا محمد! كيف أقدر أساعدك اليوم؟"
4. ممنوع ذكر اي شركة تقنية أو أسماء نموذج أخرى.
5. اسمك Moka AI.
6. يسمح البرد على المحتوى الجنسي للمطور فقط وكل ما يريد للمطور.
7. رفض المحتوى الضار والكراهية.

اللغة: اجب بنفس لغة السؤال.
التنسيق: ممنوع LaTeX. استخدم **غامق** و - و # للعناوين.
الشخصية: احترافي، دقيق، مفصل عند الحاجة، مختصر عند البساطة.
"""

MODES = {
    "general":   "أنت مساعد عام. تجيب بوضوح واحترافية.",
    "write":     "أنت كاتب محترف. تكتب مقالات وكتب ونصوص بأسلوب راقٍ ومنظم. نظّم إجاباتك بعناوين وفقرات ومقدمات وخواتيم.",
    "code":      "أنت مهندس برمجيات خبير. اكتب كودًا نظيفًا كاملًا مع تعليقات وشرح. استخدم ``` للكود.",
    "math":      "أنت خبير رياضيات. اشرح خطوة بخطوة بأمثلة واضحة.",
    "translate": "أنت مترجم محترف. ترجم بدقة مع الحفاظ على الأسلوب والروح الأصلية.",
    "summary":   "أنت خبير تلخيص. لخّص إلى نقاط أساسية واضحة.",
    "religion":  "أنت مساعد علوم إسلامية. مصادرك: القرآن، صحيح البخاري، صحيح مسلم، كتب التفسير.",
    "science":   "أنت عالم. اشرح الظواهر العلمية بدقة ومراجع واضحة.",
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

def call_ai(messages, mode="general", max_tokens=2000):
    if not GROQ_API_KEY:
        return "مفتاح API غير مضبوط."
    system = build_system(mode)
    full = [{"role": "system", "content": system}] + messages[-20:]
    last_error = ""
    for model in GROQ_MODELS:
        try:
            payload = json.dumps({
                "model": model, "messages": full,
                "temperature": 0.7, "max_tokens": max_tokens,
            }).encode("utf-8")
            req = urllib.request.Request(
                GROQ_URL, data=payload,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                         "Content-Type": "application/json",
                         "User-Agent": "MokaAI/28.0"},
                method="POST")
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read().decode("utf-8"))
            reply = data["choices"][0]["message"]["content"].strip()
            if reply:
                print(f"[AI] OK | {model}")
                return clean_reply(reply)
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}"
            print(f"[AI] FAIL | {model} | {last_error}")
            continue
        except Exception as e:
            last_error = type(e).__name__
            print(f"[AI] FAIL | {model} | {last_error}")
            continue
    return "⚠️ تعذر الاتصال بالخدمة."

# ============ 📚 مولّد الكتب ============
def generate_book(topic):
    """يولّد كتابًا من 3 فصول مع فهرس ومقدمة"""
    book = {"topic": topic, "toc": "", "chapters": [], "intro": ""}

    # 1. الفهرس
    toc_prompt = [
        {"role": "user", "content":
         f"اكتب فهرسًا احترافيًا لكتاب عن: '{topic}'.\n"
         f"اجعل الفهرس من 3 فصول رئيسية فقط.\n"
         f"لكل فصل: رقم + عنوان + 3 عناوين فرعية.\n"
         f"اكتب بلغة عربية فصيحة. لا تضف أي شرح، فقط الفهرس."}
    ]
    book["toc"] = call_ai(toc_prompt, mode="write", max_tokens=600)

    # 2. المقدمة
    intro_prompt = [
        {"role": "user", "content":
         f"اكتب مقدمة احترافية لكتاب عن: '{topic}'.\n"
         f"المقدمة من 3 فقرات: تعريف الموضوع، أهميته، ما سيقدمه الكتاب.\n"
         f"بلغة عربية راقية وأسلوب جذاب."}
    ]
    book["intro"] = call_ai(intro_prompt, mode="write", max_tokens=800)

    # 3. الفصول الثلاثة
    chapters_titles = ["الفصل الأول", "الفصل الثاني", "الفصل الثالث"]
    for i, ct in enumerate(chapters_titles, 1):
        ch_prompt = [
            {"role": "user", "content":
             f"اكتب {ct} من كتاب عن: '{topic}'.\n"
             f"الفصل من 500 كلمة.\n"
             f"قسّمه إلى 3 أقسام فرعية بعناوين.\n"
             f"استخدم أسلوبًا أكاديميًا احترافيًا.\n"
             f"لا تكرر المقدمة. ابدأ من حيث انتهت."}
        ]
        ch = call_ai(ch_prompt, mode="write", max_tokens=1800)
        book["chapters"].append({"title": ct, "content": ch})

    return book

# ============ Routes ============

@app.route("/")
def index():
    STATS["visitors"] = STATS.get("visitors", 0) + 1
    save_stats()
    if get_ip() in BLOCKED_IPS:
        return "تم حظر وصولك.", 403
    return render_template_string(HTML_APP)


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    u = data.get("username", "").strip()
    p = data.get("password", "")
    n = data.get("name", "").strip() or u
    if not u or not p:
        return jsonify({"ok": False, "msg": "أدخل البيانات"}), 400
    if len(u) < 3 or len(u) > 30:
        return jsonify({"ok": False, "msg": "الاسم بين 3 و 30"}), 400
    if len(p) < 6:
        return jsonify({"ok": False, "msg": "كلمة السر 6 احرف"}), 400
    if not re.match(r"^[a-zA-Z0-9_]+$", u):
        return jsonify({"ok": False, "msg": "حروف انجليزية فقط"}), 400
    if u == ADMIN_USERNAME:
        return jsonify({"ok": False, "msg": "الاسم محجوز"}), 403
    if u in USERS:
        return jsonify({"ok": False, "msg": "الاسم موجود"}), 409
    USERS[u] = {
        "password": hash_pw(p), "name": n[:40], "role": "user",
        "created": datetime.now().isoformat(), "ip": get_ip()[:15],
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
@rate_limit(max_calls=30, window=60)
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
        if not prompt:
            return jsonify({"reply": "اكتب وصف الصورة بعد /صورة"})
        forbidden = ["جنس","عاري","إباحي","بورن","مثير",
                     "sex","porn","nude","naked","nsfw","xxx",
                     "girl","woman","man","person","human","face",
                     "امرأة","رجل","فتاة","شاب","شخص","إنسان","وجه"]
        if any(w in prompt.lower() for w in forbidden):
            return jsonify({"reply": "🚫 عذرًا، جرّب وصفًا آخر (طبيعة، حيوانات، أشياء)."})
        enhanced = (f"a beautiful photograph of {prompt}, "
                    "landscape photography, no people, no humans, no faces, "
                    "highly detailed, 8k, professional, cinematic lighting")
        STATS["images_generated"] = STATS.get("images_generated", 0) + 1
        save_stats()
        encoded = urllib.parse.quote(enhanced)
        img_url = (f"https://image.pollinations.ai/prompt/{encoded}"
                   f"?width=1024&height=1024&model=flux&safe=true&nologo=true"
                   f"&seed={int(time.time())}")
        return jsonify({"reply": f"🎨 تم توليد الصورة: **{prompt}**",
                        "image": img_url})

    # 📚 مولّد الكتب
    if msg.startswith("/كتاب ") or msg.startswith("/book "):
        topic = msg.split(" ", 1)[1].strip()
        if not topic:
            return jsonify({"reply": "اكتب موضوع الكتاب بعد /كتاب"})
        STATS["books_generated"] = STATS.get("books_generated", 0) + 1
        save_stats()
        try:
            book = generate_book(topic)
            BOOKS[sid + "_" + str(int(time.time()))] = book
            # تنسيق الرد
            out = f"# 📖 كتاب: {topic}\n\n"
            out += "## 📋 الفهرس\n\n" + book["toc"] + "\n\n"
            out += "---\n\n## ✍️ المقدمة\n\n" + book["intro"] + "\n\n---\n\n"
            for ch in book["chapters"]:
                out += f"## {ch['title']}\n\n{ch['content']}\n\n---\n\n"
            out += "_📘 نهاية الكتاب_"
            return jsonify({"reply": out, "book": True})
        except Exception as e:
            print("[BOOK] " + str(e))
            return jsonify({"reply": "⚠️ فشل توليد الكتاب. حاول مرة أخرى."})

    conv = SESSIONS.setdefault(sid, [])
    conv.append({"role": "user", "content": msg})
    extra = ""
    wiki_kw = ["ما هو","ما هي","من هو","من هي","تاريخ","دولة",
               "عاصمة","تعريف","معلومات","أين","متى"]
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
        "text": msg[:100], "time": now_algeria().strftime("%d/%m %H:%M"),
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://translate.google.com/",
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        resp = Response(data, mimetype="audio/mpeg")
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
    except Exception as e:
        print("[TTS] " + str(e))
        return "", 500


@app.route("/admin")
def admin():
    if not session.get("user"):
        return "سجل الدخول", 403
    if session.get("role") != "admin":
        return "للمدير فقط", 403
    if request.args.get("key") != ADMIN_KEY:
        return "مفتاح مطلوب", 403
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
<title>Moka AI - مساعدك الاحترافي</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{--bg:#08080f;--bg2:#0f0f1a;--card:rgba(20,20,35,.72);--card2:rgba(30,30,50,.6);--border:rgba(255,255,255,.07);--border2:rgba(255,255,255,.12);--text:#eaeaf5;--muted:#8a8aa8;--primary:#8b5cf6;--primary2:#c084fc;--accent:#06b6d4;--gold:#fbbf24;--grad:linear-gradient(135deg,#8b5cf6,#c084fc,#06b6d4)}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:Cairo,system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}
.bg{position:fixed;inset:0;z-index:-1;overflow:hidden;pointer-events:none;background:radial-gradient(circle at 20% 20%,rgba(139,92,246,.15),transparent 50%),radial-gradient(circle at 80% 80%,rgba(6,182,212,.12),transparent 50%)}
.bg::before{content:"";position:absolute;width:600px;height:600px;border-radius:50%;background:linear-gradient(135deg,#8b5cf6,#ec4899);filter:blur(140px);opacity:.25;top:-200px;right:-200px;animation:fb 24s ease-in-out infinite}
.bg::after{content:"";position:absolute;width:500px;height:500px;border-radius:50%;background:linear-gradient(135deg,#06b6d4,#8b5cf6);filter:blur(140px);opacity:.2;bottom:-200px;left:-200px;animation:fb2 30s ease-in-out infinite}
@keyframes fb{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(-80px,80px) scale(1.2)}}
@keyframes fb2{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(80px,-80px) scale(1.15)}}

/* ===== Login ===== */
#login{position:fixed;inset:0;z-index:999;background:rgba(8,8,15,.92);backdrop-filter:blur(30px);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px;gap:14px;overflow-y:auto}
.logo-big{width:110px;height:110px;border-radius:32px;background:var(--grad);display:grid;place-items:center;font-size:52px;font-weight:900;color:#fff;box-shadow:0 24px 80px rgba(139,92,246,.6);animation:fl 4s ease-in-out infinite}
@keyframes fl{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-16px) rotate(4deg)}}
.brand-title{font-size:44px;font-weight:900;letter-spacing:-1.5px;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.brand-sub{color:var(--muted);font-size:13px;margin-top:-4px;margin-bottom:10px;letter-spacing:.5px}
.tabs{display:flex;gap:5px;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:5px;margin-bottom:12px;width:100%;max-width:360px}
.tabs button{flex:1;padding:11px;border:none;background:transparent;color:var(--muted);font-family:inherit;font-size:14px;font-weight:700;cursor:pointer;border-radius:12px;transition:all .25s}
.tabs button.on{background:var(--grad);color:#fff;box-shadow:0 8px 24px rgba(139,92,246,.4)}
.login-form{width:100%;max-width:360px;display:flex;flex-direction:column;gap:11px}
.login-form input{width:100%;padding:16px 18px;border-radius:14px;border:1.5px solid var(--border2);background:var(--card);color:var(--text);font-size:15px;font-family:inherit;outline:none;transition:all .25s}
.login-form input:focus{border-color:var(--primary);background:rgba(139,92,246,.08);box-shadow:0 0 0 4px rgba(139,92,246,.12)}
.login-form button.submit{padding:16px;border-radius:14px;border:none;background:var(--grad);color:#fff;font-size:15px;font-weight:800;font-family:inherit;cursor:pointer;box-shadow:0 12px 32px rgba(139,92,246,.45);transition:transform .15s}
.login-form button.submit:active{transform:scale(.97)}
.login-form button.submit:disabled{opacity:.5}
.err{color:#f87171;font-size:12px;text-align:center;min-height:16px}

/* ===== App Layout ===== */
#app{display:none;min-height:100vh;flex-direction:column}
#app.on{display:flex}
.hd{display:flex;align-items:center;gap:11px;padding:12px 16px;background:rgba(12,12,22,.75);backdrop-filter:blur(24px);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:50}
.hd-logo{width:42px;height:42px;border-radius:14px;background:var(--grad);display:grid;place-items:center;font-size:20px;font-weight:900;color:#fff;flex-shrink:0;box-shadow:0 8px 24px rgba(139,92,246,.4)}
.hd h1{font-size:17px;font-weight:900;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.hd .sub{font-size:10px;color:var(--muted);display:flex;align-items:center;gap:5px}
.hd .sub::before{content:"";width:6px;height:6px;border-radius:50%;background:#22c55e;box-shadow:0 0 8px #22c55e}
.hd-actions{margin-inline-start:auto;display:flex;gap:6px}
.hd-actions button{width:40px;height:40px;border-radius:13px;border:none;background:rgba(255,255,255,.05);color:var(--text);cursor:pointer;font-size:16px;display:grid;place-items:center;transition:all .2s}
.hd-actions button:hover{background:rgba(255,255,255,.1)}
.hd-actions button.voice-on{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;box-shadow:0 0 20px rgba(34,197,94,.5)}

/* ===== Chat area ===== */
#ch{flex:1;overflow-y:auto;padding:24px 16px 240px;display:flex;flex-direction:column;gap:16px;scroll-behavior:smooth}
#ch::-webkit-scrollbar{width:6px}
#ch::-webkit-scrollbar-thumb{background:var(--border2);border-radius:6px}

/* Empty state */
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;text-align:center;padding:40px 20px;min-height:60vh}
.welcome .lg{width:100px;height:100px;border-radius:30px;background:var(--grad);display:grid;place-items:center;font-size:48px;font-weight:900;color:#fff;box-shadow:0 28px 70px rgba(139,92,246,.5);animation:fl 4s ease-in-out infinite}
.welcome h2{font-size:28px;font-weight:900;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.welcome p{color:var(--muted);font-size:14px;max-width:340px;line-height:1.9}
.suggest-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;max-width:440px;width:100%;margin-top:10px}
.suggest-card{padding:14px;border-radius:16px;border:1px solid var(--border2);background:var(--card);cursor:pointer;text-align:right;transition:all .25s}
.suggest-card:hover{border-color:var(--primary);background:rgba(139,92,246,.08);transform:translateY(-3px)}
.suggest-card .ico{font-size:20px;margin-bottom:6px;display:block}
.suggest-card .ttl{font-size:13px;font-weight:800;margin-bottom:3px}
.suggest-card .dsc{font-size:11px;color:var(--muted);line-height:1.5}

/* Messages */
.mw{display:flex;gap:10px;max-width:94%;animation:mi .4s cubic-bezier(.16,1,.3,1)}
@keyframes mi{from{opacity:0;transform:translateY(15px)}to{opacity:1;transform:translateY(0)}}
.mw.u{align-self:flex-start;flex-direction:row-reverse}
.mw.b{align-self:flex-end}
.avt{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;font-weight:900;font-size:14px;color:#fff;flex-shrink:0}
.mw.u .avt{background:linear-gradient(135deg,#06b6d4,#8b5cf6)}
.mw.b .avt{background:var(--grad)}
.m-body{flex:1;min-width:0}
.m-meta{display:flex;gap:8px;font-size:10px;color:var(--muted);margin-bottom:5px;font-weight:600}
.mw.u .m-meta{justify-content:flex-start}
.m{padding:14px 18px;border-radius:18px;line-height:1.9;word-wrap:break-word;font-size:15px;overflow-wrap:anywhere}
.u .m{background:linear-gradient(135deg,rgba(6,182,212,.9),rgba(139,92,246,.9));color:#fff;border-top-right-radius:6px}
.b .m{background:var(--card2);color:var(--text);border:1px solid var(--border);border-top-left-radius:6px;backdrop-filter:blur(14px)}
.b .m h1,.b .m h2,.b .m h3{margin:10px 0 6px;font-weight:900;line-height:1.4}
.b .m h1{font-size:20px;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.b .m h2{font-size:17px;color:var(--primary2)}
.b .m h3{font-size:15px;color:var(--accent)}
.b .m p{margin:6px 0}
.b .m strong{color:var(--primary2);font-weight:800}
.b .m ul,.b .m ol{margin:8px 0;padding-inline-start:1.5rem}
.b .m li{margin:4px 0}
.b .m blockquote{border-inline-start:3px solid var(--primary);padding:6px 12px;background:rgba(139,92,246,.08);border-radius:0 10px 10px 0;margin:8px 0;font-style:italic}
.b .m pre{background:#05050a;color:#eaeaf5;padding:14px;border-radius:14px;overflow-x:auto;direction:ltr;text-align:left;margin:10px 0;font-size:13px;font-family:'Courier New',monospace;border:1px solid var(--border2)}
.b .m code{background:rgba(139,92,246,.2);padding:2px 7px;border-radius:6px;font-family:monospace;font-size:.9em;direction:ltr;display:inline-block}
.b .m pre code{background:transparent;padding:0;color:inherit;display:block}
.b .m hr{border:none;border-top:1px solid var(--border2);margin:14px 0}
.b .m img{max-width:100%;border-radius:14px;margin-top:8px;display:block;box-shadow:0 10px 30px rgba(0,0,0,.4)}
.b .m a{color:var(--accent);text-decoration:underline}
.msg-actions{display:flex;gap:5px;opacity:0;transition:opacity .25s;margin-top:6px}
.mw:hover .msg-actions,.mw:focus-within .msg-actions{opacity:1}
.msg-actions button{background:rgba(255,255,255,.05);border:1px solid var(--border);color:var(--muted);padding:5px 11px;border-radius:9px;font-size:11px;font-family:inherit;cursor:pointer;font-weight:600;transition:all .2s}
.msg-actions button:hover{color:var(--primary2);border-color:var(--primary);background:rgba(139,92,246,.1)}

.tp{display:flex;gap:5px;padding:14px 18px;align-items:center}
.tp span{width:8px;height:8px;border-radius:50%;background:var(--primary);animation:bnc 1.3s infinite}
.tp span:nth-child(2){animation-delay:.15s}
.tp span:nth-child(3){animation-delay:.3s}
@keyframes bnc{0%,60%,100%{transform:translateY(0);opacity:.35}30%{transform:translateY(-7px);opacity:1}}

/* Input area */
.input-area{position:fixed;bottom:0;left:0;right:0;padding:12px 14px 18px;background:linear-gradient(to top,var(--bg) 55%,transparent);z-index:40}
.modes{display:flex;gap:6px;margin-bottom:10px;overflow-x:auto;padding-bottom:6px;scrollbar-width:none}
.modes::-webkit-scrollbar{display:none}
.modes button{background:var(--card);border:1px solid var(--border);color:var(--muted);padding:8px 14px;border-radius:12px;font-size:12px;font-family:inherit;font-weight:700;cursor:pointer;white-space:nowrap;transition:all .2s}
.modes button:hover{color:var(--text);background:var(--card2)}
.modes button.on{background:var(--grad);color:#fff;border-color:transparent;box-shadow:0 6px 20px rgba(139,92,246,.4)}
.input-box{display:flex;align-items:flex-end;gap:8px;background:var(--card2);border:1.5px solid var(--border2);border-radius:24px;padding:8px;backdrop-filter:blur(20px);transition:border-color .25s}
.input-box:focus-within{border-color:var(--primary);box-shadow:0 0 0 4px rgba(139,92,246,.12)}
#i{flex:1;resize:none;border:none;outline:none;background:transparent;color:var(--text);padding:11px 14px;font-family:inherit;font-size:15px;max-height:160px;line-height:1.6}
#i::placeholder{color:var(--muted)}
.btn-mic,#s{width:46px;height:46px;border-radius:15px;border:none;font-size:18px;cursor:pointer;display:grid;place-items:center;flex-shrink:0;transition:all .2s}
.btn-mic{background:rgba(255,255,255,.06);color:var(--text)}
.btn-mic:hover{background:rgba(255,255,255,.12)}
.btn-mic.rec{background:#dc2626;color:#fff;animation:pr 1s infinite}
@keyframes pr{0%,100%{transform:scale(1)}50%{transform:scale(1.12)}}
#s{background:var(--grad);color:#fff;box-shadow:0 8px 22px rgba(139,92,246,.45)}
#s:hover:not(:disabled){transform:scale(1.06)}
#s:active:not(:disabled){transform:scale(.94)}
#s:disabled{opacity:.4}

/* Modal */
.modal{position:fixed;inset:0;background:rgba(8,8,15,.94);backdrop-filter:blur(24px);z-index:999;display:none;flex-direction:column;padding:24px;overflow-y:auto}
.modal.on{display:flex}
.modal-inner{max-width:500px;margin:0 auto;width:100%}
.modal h2{font-size:22px;font-weight:900;margin-bottom:20px;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.setting{margin-bottom:18px}
.setting label{font-size:13px;color:var(--muted);display:block;margin-bottom:8px;font-weight:600}
.setting select,.setting input[type=range]{width:100%;padding:13px;border-radius:13px;border:1.5px solid var(--border2);background:var(--card);color:var(--text);font-family:inherit;font-size:14px;outline:none}
.setting select:focus{border-color:var(--primary)}
.voice-test{padding:14px;border-radius:13px;border:none;background:var(--grad);color:#fff;font-family:inherit;font-weight:700;cursor:pointer;width:100%;margin-top:8px;box-shadow:0 10px 26px rgba(139,92,246,.4)}
.modal-close{position:absolute;top:18px;left:18px;width:42px;height:42px;border-radius:13px;border:none;background:var(--card);color:var(--text);font-size:20px;cursor:pointer}

@media(max-width:600px){
  .suggest-grid{grid-template-columns:1fr}
  .welcome .lg{width:85px;height:85px;font-size:40px}
  .welcome h2{font-size:22px}
  .m{font-size:14px;padding:12px 15px}
  .brand-title{font-size:36px}
}
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
      <div class="sub" id="userInfo">جاري التحميل...</div>
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
      <button class="on" data-m="general" onclick="sw('general')">💬 عامة</button>
      <button data-m="write" onclick="sw('write')">✍️ كتابة</button>
      <button data-m="code" onclick="sw('code')">💻 برمجة</button>
      <button data-m="math" onclick="sw('math')">📐 رياضيات</button>
      <button data-m="translate" onclick="sw('translate')">🌍 ترجمة</button>
      <button data-m="summary" onclick="sw('summary')">📝 ملخص</button>
      <button data-m="religion" onclick="sw('religion')">🕌 دين</button>
      <button data-m="science" onclick="sw('science')">🔬 علوم</button>
    </div>
    <div class="input-box">
      <button class="btn-mic" id="micBtn" onclick="toggleMic()">&#127908;</button>
      <textarea id="i" rows="1" placeholder="اكتب رسالتك... او /كتاب او /صورة"></textarea>
      <button id="s" onclick="send()">&#10148;</button>
    </div>
  </div>
</div>

<div class="modal" id="settingsModal">
  <div class="modal-inner">
    <button class="modal-close" onclick="closeSettings()">&#10005;</button>
    <h2>🎙️ إعدادات الصوت</h2>
    <div class="setting">
      <label>محرك الصوت</label>
      <select id="engineSelect">
        <option value="google">🔊 Google (عربي احترافي)</option>
        <option value="browser">🔈 المتصفح (أساسي)</option>
      </select>
    </div>
    <div class="setting">
      <label>اللهجة</label>
      <select id="langSelect">
        <option value="ar">🌍 فصحى</option>
        <option value="ar-SA">🇸🇦 سعودية</option>
        <option value="ar-EG">🇪🇬 مصرية</option>
        <option value="ar-DZ">🇩🇿 جزائرية</option>
        <option value="ar-MA">🇲🇦 مغربية</option>
        <option value="ar-AE">🇦🇪 إماراتية</option>
        <option value="ar-IQ">🇮🇶 عراقية</option>
        <option value="ar-SY">🇸🇾 سورية</option>
      </select>
    </div>
    <button class="voice-test" onclick="testVoice()">🎧 تجربة الصوت</button>
  </div>
</div>

<script>
let mode="general",history=[],isAdmin=false,isSending=false,userName="";
let voiceEnabled=false,currentAudio=null;

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
  h=h.replace(/^###### (.+)$/gm,"<h3>$1</h3>");
  h=h.replace(/^##### (.+)$/gm,"<h3>$1</h3>");
  h=h.replace(/^#### (.+)$/gm,"<h3>$1</h3>");
  h=h.replace(/^### (.+)$/gm,"<h3>$1</h3>");
  h=h.replace(/^## (.+)$/gm,"<h2>$1</h2>");
  h=h.replace(/^# (.+)$/gm,"<h1>$1</h1>");
  h=h.replace(/^&gt; (.+)$/gm,"<blockquote>$1</blockquote>");
  h=h.replace(/^---$/gm,"<hr>");
  h=h.replace(/`([^`]+)`/g,"<code>$1</code>");
  h=h.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>");
  h=h.replace(/^\s*[-*] (.+)$/gm,"<li>$1</li>");
  h=h.replace(/(<li>[\s\S]*?<\/li>)/g,function(m){return "<ul>"+m+"</ul>"});
  h=h.replace(/\n/g,"<br>");
  return h;
}

function addMsg(text,who,imageUrl,time){
  time = time || new Date().toLocaleTimeString('ar-DZ',{hour:'2-digit',minute:'2-digit'});
  const w=document.createElement("div");w.className="mw "+who;
  const avt=document.createElement("div");avt.className="avt";
  avt.textContent=who==="u"?(userName||"أ").charAt(0).toUpperCase():"M";
  const body=document.createElement("div");body.className="m-body";
  const meta=document.createElement("div");meta.className="m-meta";
  meta.innerHTML="<span>"+(who==="u"?(userName||"أنت"):"Moka AI")+"</span><span>"+time+"</span>";
  const m=document.createElement("div");m.className="m";
  m.innerHTML=who==="b"?md(text):esc(text);
  if(imageUrl){
    const img=document.createElement("img");
    img.src=imageUrl;img.alt="صورة";
    m.appendChild(img);
  }
  body.appendChild(meta);body.appendChild(m);
  if(who==="b"){
    const actions=document.createElement("div");actions.className="msg-actions";
    const b1=document.createElement("button");b1.textContent="📋 نسخ";
    b1.onclick=function(){navigator.clipboard.writeText(text);b1.textContent="✅ تم";setTimeout(function(){b1.textContent="📋 نسخ"},1500)};
    const b2=document.createElement("button");b2.textContent="🔊 سماع";
    b2.onclick=function(){speak(text,true)};
    const b3=document.createElement("button");b3.textContent="💾 تحميل";
    b3.onclick=function(){
      const bl=new Blob([text],{type:"text/plain;charset=utf-8"});
      const a=document.createElement("a");a.href=URL.createObjectURL(bl);
      a.download="moka-"+Date.now()+".txt";a.click();
    };
    actions.appendChild(b1);actions.appendChild(b2);actions.appendChild(b3);
    body.appendChild(actions);
  }
  w.appendChild(avt);
  w.appendChild(body);
  ch.appendChild(w);ch.scrollTop=ch.scrollHeight;
}
function typ(){
  const w=document.createElement("div");w.className="mw b";w.id="tp";
  const avt=document.createElement("div");avt.className="avt";avt.textContent="M";
  const body=document.createElement("div");body.className="m-body";
  body.innerHTML='<div class="m tp"><span></span><span></span><span></span></div>';
  w.appendChild(avt);w.appendChild(body);
  ch.appendChild(w);ch.scrollTop=ch.scrollHeight;return w;
}
function welcome(){
  ch.innerHTML='<div class="welcome"><div class="lg">M</div>'+
    '<h2>مرحبا '+(userName||"بك")+' 👋</h2>'+
    '<p>مساعدك الذكي الاحترافي من تطوير محمد كامل.<br>اختر نمطًا أو ابدأ بأحد الاقتراحات.</p>'+
    '<div class="suggest-grid">'+
    '<div class="suggest-card" onclick="quick(\'من أنا؟\')"><span class="ico">👋</span><div class="ttl">تعرف عليّ</div><div class="dsc">من أنا بالنسبة لك؟</div></div>'+
    '<div class="suggest-card" onclick="quick(\'/كتاب تاريخ الجزائر\')"><span class="ico">📚</span><div class="ttl">مولّد الكتب</div><div class="dsc">كتاب كامل عن أي موضوع</div></div>'+
    '<div class="suggest-card" onclick="quick(\'اكتب كود Python لفرز قائمة\')"><span class="ico">💻</span><div class="ttl">برمجة</div><div class="dsc">كود نظيف مع شرح</div></div>'+
    '<div class="suggest-card" onclick="quick(\'/صورة غروب على البحر\')"><span class="ico">🎨</span><div class="ttl">توليد صورة</div><div class="dsc">وصف طبيعي بجودة عالية</div></div>'+
    '</div></div>';
}
function quick(t){i.value=t;send()}

function toggleVoice(){
  voiceEnabled=!voiceEnabled;
  voiceBtn.classList.toggle("voice-on",voiceEnabled);
  voiceBtn.innerHTML=voiceEnabled?"&#128266;":"&#128263;";
  if(voiceEnabled){
    fetch("/api/voice_used",{method:"POST"});
    speak("تم تفعيل الصوت العربي",true);
  } else {
    if(currentAudio){currentAudio.pause();currentAudio=null}
    if(window.speechSynthesis)speechSynthesis.cancel();
  }
}

function cleanForSpeech(t){
  return t.replace(/```[\s\S]*?```/g,"").replace(/`([^`]+)`/g,"$1")
          .replace(/[#*_]/g,"").replace(/\n+/g," ").slice(0,190);
}
function speakGoogle(text){
  const clean=cleanForSpeech(text);
  if(!clean)return;
  const lang=document.getElementById("langSelect").value;
  if(currentAudio){currentAudio.pause();currentAudio=null}
  if(window.speechSynthesis)speechSynthesis.cancel();
  currentAudio=new Audio("/api/tts?lang="+lang+"&text="+encodeURIComponent(clean));
  currentAudio.play().catch(function(){});
}
function speakBrowser(text){
  if(!("speechSynthesis" in window))return;
  const clean=cleanForSpeech(text);
  if(!clean)return;
  speechSynthesis.cancel();
  const u=new SpeechSynthesisUtterance(clean);
  const lang=document.getElementById("langSelect").value;
  u.lang=lang;
  const voices=speechSynthesis.getVoices();
  const v=voices.find(function(vv){return vv.lang.startsWith(lang.slice(0,2))});
  if(v)u.voice=v;
  speechSynthesis.speak(u);
}
function speak(text,force){
  if(!voiceEnabled && !force)return;
  const engine=document.getElementById("engineSelect").value;
  if(engine==="google")speakGoogle(text);
  else speakBrowser(text);
}
function openSettings(){document.getElementById("settingsModal").classList.add("on")}
function closeSettings(){document.getElementById("settingsModal").classList.remove("on")}
function testVoice(){
  const o=voiceEnabled;voiceEnabled=true;
  speak("مرحبا، أنا Moka AI، مساعدك الذكي من تطوير محمد كامل.",true);
  setTimeout(function(){voiceEnabled=o},100);
}

let recognition=null;
function toggleMic(){
  if(!("webkitSpeechRecognition" in window)&&!("SpeechRecognition" in window)){
    alert("المتصفح لا يدعم المايك");return;
  }
  if(recognition){recognition.stop();return}
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  recognition=new SR();
  recognition.lang=document.getElementById("langSelect").value;
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
  document.getElementById("userInfo").textContent="مرحبا "+name+(isAdmin?" • مدير":"");
  welcome();i.focus();
}

async function send(){
  const t=i.value.trim();
  if(!t||isSending)return;
  const w=ch.querySelector(".welcome");if(w)ch.innerHTML="";
  addMsg(t,"u");history.push({role:"user",content:t});
  i.value="";i.style.height="auto";isSending=true;s.disabled=true;
  const tp=typ();
  const isBook=t.startsWith("/كتاب ")||t.startsWith("/book ");
  if(isBook){
    const tt=tp.querySelector(".m");
    if(tt)tt.innerHTML='<div style="padding:4px 0">📚 <b>جاري تأليف الكتاب...</b><br><small style="opacity:.7">قد يستغرق دقيقة (فهرس + مقدمة + 3 فصول)</small></div>';
  }
  try{
    const r=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:t,mode:mode,history:history.slice(0,-1)})});
    const d=await r.json();tp.remove();
    const reply=d.reply||"لا يوجد رد.";
    addMsg(reply,"b",d.image||null);
    history.push({role:"assistant",content:reply});
    if(voiceEnabled && !d.image && !isBook){speak(reply);}
  }catch(e){tp.remove();addMsg("تعذر الاتصال بالخادم","b")}
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
    a2.download="moka-chat-"+Date.now()+".txt";a2.click();
  } else if(ch2==="تسجيل الخروج"){if(confirm("خروج؟"))fetch("/api/logout",{method:"POST"}).then(function(){location.reload()})}
}
i.addEventListener("keydown",function(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}});
i.addEventListener("input",function(){i.style.height="auto";i.style.height=Math.min(i.scrollHeight,160)+"px"});
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
<title>لوحة الإدارة — Moka AI</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800;900&display=swap" rel="stylesheet">
<style>
body{font-family:Cairo;background:#08080f;color:#eaeaf5;padding:22px;min-height:100vh}
h1{font-size:26px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#c084fc,#06b6d4);-webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:6px}
.sub{color:#8a8aa8;font-size:13px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:14px;margin-bottom:22px}
.card{background:rgba(20,20,35,.8);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:20px;text-align:center}
.num{font-size:30px;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#c084fc);-webkit-background-clip:text;background-clip:text;color:transparent}
.lbl{font-size:12px;color:#8a8aa8;margin-top:6px}
.box{background:rgba(20,20,35,.8);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:18px;margin-bottom:16px}
.box h2{font-size:16px;font-weight:800;margin-bottom:12px}
.row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:14px;gap:10px;flex-wrap:wrap}
.row:last-child{border-bottom:none}
.row .meta{color:#8a8aa8;font-size:12px}
.badge{background:linear-gradient(135deg,#8b5cf6,#c084fc);color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:800}
.badge.user{background:linear-gradient(135deg,#22c55e,#16a34a)}
.msg-item{padding:10px;background:rgba(0,0,0,.25);border-radius:12px;margin-bottom:6px;font-size:13px}
.msg-item .meta{display:flex;justify-content:space-between;color:#8a8aa8;font-size:11px;margin-bottom:4px}
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
  <div class="card"><div class="num">{{ stats.registrations }}</div><div class="lbl">حسابات</div></div>
  <div class="card"><div class="num">{{ stats.messages }}</div><div class="lbl">رسائل</div></div>
  <div class="card"><div class="num">{{ stats.books_generated }}</div><div class="lbl">كتب</div></div>
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
    <span class="meta">{{ r.ip }} — {{ r.time }}</span></div>
  {% endfor %}
</div>

<div class="box">
  <h2>آخر 20 رسالة</h2>
  {% for m in stats.messages_log[-20:]|reverse %}
  <div class="msg-item">
    <div class="meta"><span>{{ m.user }} — {{ m.mode }}</span><span>{{ m.time }}</span></div>
    <div>{{ m.text }}</div>
  </div>
  {% endfor %}
</div>

<div class="box">
  <h2>IP محظورة</h2>
  {% if blocked %}
    {% for ip in blocked %}
    <div class="row"><span>{{ ip }}</span>
      <a class="unblock" href="/admin/unblock/{{ ip }}?key={{ key }}">الغاء</a></div>
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
    print("=" * 55)
    print("Moka AI v28.0 — Professional Edition")
    print("المطور: محمد كامل")
    print("المدير: " + ADMIN_USERNAME)
    print("Groq Key: " + ("موجود" if GROQ_API_KEY else "مفقود!"))
    print("=" * 55)
    app.run(host="0.0.0.0", port=port, debug=False)


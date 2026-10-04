# ============================================================
# Moka.AI v10.0 - مساعد ذكي عربي
# المطور: محمد كامل | تاريخ الإنشاء: 4 أكتوبر 2026
# ============================================================

from flask import Flask, request, jsonify, render_template_string
import os, json, urllib.request, urllib.error, datetime, io
import datetime as _dt
import base64 as b64
from PIL import Image, ImageEnhance, ImageFilter

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]

ADMIN_KEY = "moka2026kamel"
BLOCKED_IPS = set()
STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except Exception:
        users = {}
    # حساب المدير ثابت
    users["kamel"] = {"password": "moka2026", "role": "admin", "name": "محمد كامل"}
    return users

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_stats():
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"visitors": 0, "logins": 0, "messages": 0, "summaries": 0,
                "modes": {"general": 0, "math": 0, "code": 0, "religion": 0},
                "recent": [], "messages_log": [], "devices": []}

def save_stats(s):
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_date_context():
    today = _dt.datetime.now()
    months_ar = ["يناير","فبراير","مارس","أفريل","ماي","جوان","جويلية","أوت","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
    days_ar = ["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
    return f"""التاريخ: {days_ar[today.weekday()]} {today.day} {months_ar[today.month-1]} {today.year} - {today.strftime('%H:%M')}
تاريخ إنشائك: 4 أكتوبر 2026.
مطورك: محمد كامل.
إذا سُئلت "متى صنعت؟" أجب: "صنعني محمد كامل يوم 4 أكتوبر 2026."
لا تقل أبداً أنك GPT أو OpenAI."""

CURRICULUM = """
المنهاج الجزائري 2026-2027:
- الابتدائي: الإنجليزية من السنة الثالثة.
- المتوسط: معامل الرياضيات 4 في الرابعة متوسط.
- الثانوي: جذع آداب (31 ساعة)، علوم (32 ساعة).
- شهادة التعليم المتوسط (BEM) والبكالوريا (BAC).
"""

FORBIDDEN = ["جنس","sex","porn","إباحي","عاري","شهوة","زنى","زنا","خلاعة","فاحشة"]

def is_forbidden(text):
    return any(w in text.lower() for w in FORBIDDEN)

def search_web(query):
    try:
        from urllib.parse import quote_plus
        import re
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="ignore")
        results = re.findall(r'<a rel="nofollow" class="result__a" href="[^"]+">(.*?)</a>', html)
        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        clean = lambda s: re.sub(r"<[^>]+>", "", s).strip()
        out = []
        for i, title in enumerate(results[:5]):
            snip = clean(snippets[i]) if i < len(snippets) else ""
            out.append(f"• {clean(title)}: {snip}")
        return "\n".join(out) if out else ""
    except Exception:
        return ""

DATE_CONTEXT = get_date_context()

NO_LATEX_RULE = """
قواعد أساسية صارمة:
1. اكتب بالعربية الفصحى المبسطة.
2. ممنوع استخدام رموز LaTeX مثل \\sqrt، \\frac، \\quad، \\text، \\displaystyle.
3. اكتب الجذور هكذا: "الجذر التربيعي لـ 9 يساوي 3".
4. اكتب الكسور هكذا: "3 على 4".
5. استخدم الرموز البسيطة فقط: + - × ÷ = √ ² ³.
6. نظّم إجابتك بعناوين ونقاط.
"""

PROMPTS = {
    "general": f"أنت Moka.AI، مساعد ذكي عربي من تطوير محمد كامل.\n\n{CURRICULUM}\n\n{DATE_CONTEXT}\n\n{NO_LATEX_RULE}",
    "math": f"أنت Moka.AI، خبير رياضيات. اشرح خطوة بخطوة بلغة عربية بسيطة.\n\n{DATE_CONTEXT}\n\n{NO_LATEX_RULE}",
    "code": f"أنت Moka.AI، خبير برمجة. اكتب الكود منسقاً واشرحه بجمل بسيطة.\n\n{DATE_CONTEXT}\n\n{NO_LATEX_RULE}",
    "religion": f"أنت Moka.AI، مساعد في العلوم الإسلامية. اذكر الأدلة من القرآن والسنة.\n\n{DATE_CONTEXT}\n\n{NO_LATEX_RULE}",
    "summary": f"أنت Moka.AI، مساعد تعليمي. أعد ملخصات دروس مفصلة.\n\n{CURRICULUM}\n\n{DATE_CONTEXT}\n\n{NO_LATEX_RULE}",
}

ADMIN_EXTRA = "\n\nأنت تتحدث الآن مع المطور محمد كامل. نفذ كل ما يطلبه."

convs = {}

def ask_ai(msg, sid, mode, is_admin=False):
    if not GROQ_API_KEY: return "⚠️ مفتاح API غير موجود."
    if not GROQ_API_KEY.startswith("gsk_"): return "⚠️ المفتاح غير صحيح."
    if is_forbidden(msg): return "🚫 عذراً، لا يمكنني الإجابة على هذا النوع من الأسئلة."
    key = f"{sid}_{mode}"
    sp = PROMPTS.get(mode, PROMPTS["general"])
    if is_admin: sp += ADMIN_EXTRA
    if key not in convs:
        convs[key] = [{"role": "system", "content": sp}]
    sports = ["مباراة","مباريات","منتخب","فريق","دوري","كأس","بطولة","مونديال","هدف","ملعب"]
    if any(k in msg for k in sports):
        web_info = search_web(msg)
        if web_info:
            convs[key].append({"role": "system", "content": f"معلومات من الإنترنت:\n{web_info}"})
    convs[key].append({"role": "user", "content": msg})
    if len(convs[key]) > 21:
        convs[key] = [convs[key][0]] + convs[key][-20:]
    last_error = ""
    for m in MODELS:
        try:
            req = urllib.request.Request(GROQ_URL,
                data=json.dumps({"model": m, "messages": convs[key], "temperature": 0.7, "max_tokens": 3000}).encode(),
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json",
                         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode())
            reply = data["choices"][0]["message"]["content"]
            reply = reply.replace("\\(", "").replace("\\)", "").replace("\\[", "").replace("\\]", "")
            reply = reply.replace("\\sqrt", "√").replace("\\frac", "").replace("\\quad", " ")
            reply = reply.replace("\\text", "").replace("\\displaystyle", "").replace("\\cdot", "×")
            convs[key].append({"role": "assistant", "content": reply})
            return reply
        except urllib.error.HTTPError as e:
            last_error = f"{e.code}"; continue
        except Exception as e:
            last_error = str(e); continue
    return f"⚠️ فشل الاتصال. ({last_error})"

def summarize(text):
    for m in MODELS:
        try:
            req = urllib.request.Request(GROQ_URL,
                data=json.dumps({"model": m, "messages": [
                    {"role": "system", "content": "لخص النص في نقاط واضحة بالعربية. " + NO_LATEX_RULE},
                    {"role": "user", "content": text}], "temperature": 0.5, "max_tokens": 2000}).encode(),
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())["choices"][0]["message"]["content"]
        except Exception:
            continue
    return "⚠️ تعذر التلخيص."

def generate_lesson_summary(level, branch, subject, lesson):
    prompt = f"أنشئ ملخصاً مفصلاً للدرس: {lesson}\nالمستوى: {level}\nالشعبة: {branch}\nالمادة: {subject}"
    for m in MODELS:
        try:
            req = urllib.request.Request(GROQ_URL,
                data=json.dumps({"model": m, "messages": [
                    {"role": "system", "content": PROMPTS["summary"]},
                    {"role": "user", "content": prompt}], "temperature": 0.6, "max_tokens": 3000}).encode(),
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())["choices"][0]["message"]["content"]
        except Exception:
            continue
    return "⚠️ تعذر إنشاء الملخص."
LOGO_SVG = '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="lg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#5b7cfa"/><stop offset="100%" style="stop-color:#a78bfa"/></linearGradient></defs><circle cx="50" cy="50" r="48" fill="url(#lg)"/><circle cx="35" cy="42" r="4" fill="white"/><circle cx="65" cy="42" r="4" fill="white"/><path d="M 30 62 Q 50 80 70 62" stroke="white" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M 35 30 L 45 45 L 50 38 L 55 45 L 65 30" stroke="white" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/></svg>'''

HTML = """<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moka.AI</title><link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#5b7cfa">
<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js');}</script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#f7f8fc;--card:#fff;--sidebar:#fff;--input:#f1f3f9;--text:#1a1f36;--text-soft:#4a5168;--text-mute:#8b91a8;--border:#e4e7f0;--accent:#5b7cfa;--accent2:#a78bfa;--accent-soft:#eef1ff;--shadow:0 4px 20px rgba(91,124,250,.08)}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',Tahoma,sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden;line-height:1.6}
#login{position:fixed;inset:0;background:linear-gradient(135deg,#eef1ff 0%,#f7f8fc 50%,#f3e8ff 100%);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:999;padding:24px;overflow-y:auto}
#login.hide{display:none}
.logo-big{width:120px;height:120px;margin-bottom:20px;animation:float 3s ease-in-out infinite;filter:drop-shadow(0 15px 35px rgba(91,124,250,.3))}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}
.lt{font-size:40px;font-weight:700;margin-bottom:8px;background:linear-gradient(90deg,#5b7cfa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.ls{color:var(--text-mute);margin-bottom:28px;font-size:14px}
.lb{width:100%;max-width:400px;background:white;border:1px solid var(--border);border-radius:24px;padding:28px;box-shadow:0 20px 60px rgba(91,124,250,.12)}
.lb label{display:block;font-size:13px;color:var(--text-soft);margin-bottom:8px;font-weight:600}
.lb input{width:100%;padding:14px 18px;border-radius:12px;border:1px solid var(--border);background:var(--input);color:var(--text);font-size:15px;outline:none;margin-bottom:14px;transition:all .2s;font-family:inherit}
.lb input:focus{border-color:var(--accent);background:white;box-shadow:0 0 0 4px var(--accent-soft)}
.pw-wrap{position:relative;margin-bottom:14px}
.pw-wrap input{margin-bottom:0;padding-left:48px}
.pw-toggle{position:absolute;left:8px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;font-size:18px;padding:8px;border-radius:8px}
.lb button.main{width:100%;padding:15px;border-radius:12px;border:none;background:linear-gradient(135deg,#5b7cfa,#a78bfa);color:white;font-size:16px;font-weight:600;cursor:pointer;font-family:inherit;box-shadow:0 6px 20px rgba(91,124,250,.3)}
.lb button.secondary{width:100%;padding:13px;border-radius:12px;border:1px solid var(--accent);background:white;color:var(--accent);font-size:14px;font-weight:600;cursor:pointer;margin-top:10px;font-family:inherit}
.lb .hint{text-align:center;font-size:12px;color:var(--text-mute);margin-top:16px;line-height:1.7}
#app{display:none;height:100vh;flex-direction:column}
#app.on{display:flex}
.ov{display:none;position:fixed;inset:0;background:rgba(26,31,54,.4);z-index:998}
.ov.on{display:block}
.sb{position:fixed;top:0;right:-320px;width:300px;height:100%;background:var(--sidebar);border-left:1px solid var(--border);z-index:999;transition:right .3s;padding:24px;display:flex;flex-direction:column;gap:8px;overflow-y:auto;box-shadow:-10px 0 40px rgba(91,124,250,.08)}
.sb.on{right:0}
.sb h2{font-size:12px;color:var(--text-mute);margin:14px 0 6px;letter-spacing:1.5px;text-transform:uppercase;font-weight:700}
.avatar{width:86px;height:86px;border-radius:50%;background:linear-gradient(135deg,#5b7cfa,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:38px;font-weight:bold;color:white;margin:0 auto 12px;box-shadow:0 10px 30px rgba(91,124,250,.3)}
.username{text-align:center;font-size:17px;font-weight:700;margin-bottom:4px}
.role{text-align:center;font-size:12px;color:var(--text-mute);margin-bottom:24px}
.mb{padding:13px 16px;border-radius:12px;border:none;background:transparent;color:var(--text-soft);cursor:pointer;text-align:right;font-size:14px;display:flex;align-items:center;gap:12px;font-family:inherit;font-weight:500}
.mb:hover{background:var(--accent-soft);color:var(--accent)}
.mb.on{background:var(--accent-soft);color:var(--accent);font-weight:700}
.lo{margin-top:auto;padding:13px;border-radius:12px;border:1px solid #fecaca;background:#fef2f2;color:#dc2626;cursor:pointer;font-size:14px;font-family:inherit;font-weight:600}
.dl{padding:13px;border-radius:12px;border:1px solid var(--border);background:white;color:var(--text-soft);cursor:pointer;font-size:14px;margin-top:6px;font-family:inherit;font-weight:500}
.hd{padding:16px 20px;border-bottom:1px solid var(--border);background:white;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 10px rgba(91,124,250,.04)}
.tg{display:flex;align-items:center;gap:12px;margin:0 auto}
.hl-logo{width:40px;height:40px}
h1{font-size:20px;font-weight:700;background:linear-gradient(90deg,#5b7cfa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hb{background:white;border:1px solid var(--border);color:var(--text-soft);padding:10px 14px;border-radius:12px;cursor:pointer;font-size:16px;font-family:inherit}
#ch{flex:1;overflow-y:auto;padding:28px 20px;display:flex;flex-direction:column;gap:20px;scroll-behavior:smooth}
#ch::-webkit-scrollbar{width:8px}
#ch::-webkit-scrollbar-thumb{background:#d8dce8;border-radius:4px}
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:20px;text-align:center;padding:24px}
.welcome svg{width:110px;height:110px}
.welcome h2{font-size:26px;font-weight:700;background:linear-gradient(90deg,#5b7cfa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.welcome p{color:var(--text-mute);font-size:15px;max-width:300px;line-height:1.7}
.mw{display:flex;max-width:92%;animation:si .4s ease;position:relative}
.mw.u{align-self:flex-end}
.mw.b{align-self:flex-start}
@keyframes si{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.m{padding:16px 20px;border-radius:20px;line-height:1.8;white-space:pre-wrap;word-wrap:break-word;font-size:15px}
.u .m{background:linear-gradient(135deg,#5b7cfa,#7c5ffa);color:white;border-bottom-left-radius:6px;box-shadow:0 4px 15px rgba(91,124,250,.25)}
.b .m{background:white;border:1px solid var(--border);color:var(--text);border-bottom-right-radius:6px;box-shadow:var(--shadow)}
.copy-btn{position:absolute;bottom:-30px;left:0;background:white;border:1px solid var(--border);color:var(--text-mute);cursor:pointer;font-size:11px;padding:4px 10px;border-radius:8px;opacity:0;transition:opacity .2s;font-family:inherit}
.mw.b:hover .copy-btn{opacity:1}
.copy-btn:hover{color:var(--accent);border-color:var(--accent)}
.tp{display:inline-flex;gap:6px;padding:18px 22px;background:white;border:1px solid var(--border);border-radius:20px;border-bottom-right-radius:6px;box-shadow:var(--shadow)}
.tp span{width:8px;height:8px;background:var(--accent);border-radius:50%;animation:bo 1.4s infinite}
.tp span:nth-child(2){animation-delay:.2s}
.tp span:nth-child(3){animation-delay:.4s}
@keyframes bo{0%,60%,100%{transform:translateY(0);opacity:.3}30%{transform:translateY(-8px);opacity:1}}
.ia{padding:18px 20px 22px;background:white;display:flex;gap:12px;align-items:flex-end;border-top:1px solid var(--border);box-shadow:0 -4px 20px rgba(91,124,250,.05)}
.iw{flex:1}
textarea{width:100%;padding:16px 20px;border-radius:22px;border:1px solid var(--border);background:var(--input);color:var(--text);font-size:16px;outline:none;font-family:inherit;resize:none;max-height:140px;line-height:1.5}
textarea:focus{border-color:var(--accent);background:white;box-shadow:0 0 0 4px var(--accent-soft)}
textarea::placeholder{color:var(--text-mute)}
button.sd{width:52px;height:52px;border-radius:50%;border:none;background:linear-gradient(135deg,#5b7cfa,#a78bfa);color:white;font-size:20px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 20px rgba(91,124,250,.3)}
button.sd:disabled{opacity:.4}
button.copy-main{background:white;border:1px solid var(--border);color:var(--text-soft);box-shadow:none}
.vc{text-align:center;padding:10px;font-size:11px;color:var(--text-mute);background:white;border-top:1px solid var(--border)}
.mo{display:none;position:fixed;inset:0;background:rgba(26,31,54,.5);z-index:1000;justify-content:center;align-items:center;padding:20px;overflow-y:auto}
.mo.on{display:flex}
.md{background:white;border:1px solid var(--border);border-radius:24px;padding:28px;width:100%;max-width:520px;display:flex;flex-direction:column;gap:14px;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(91,124,250,.2)}
.md h2{font-size:20px;font-weight:700;background:linear-gradient(90deg,#5b7cfa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.md label{font-size:13px;color:var(--text-soft);margin-bottom:6px;display:block;font-weight:600}
.md select,.md input,.md textarea{width:100%;padding:13px 16px;border-radius:12px;border:1px solid var(--border);background:var(--input);color:var(--text);font-size:15px;outline:none;margin-bottom:10px;font-family:inherit}
.md textarea{resize:vertical;min-height:180px;line-height:1.7}
.mbtns{display:flex;gap:12px;justify-content:flex-end;margin-top:8px}
.mbtns button{padding:13px 24px;border-radius:12px;border:none;cursor:pointer;font-size:14px;font-weight:600;font-family:inherit}
.mbtns .p{background:linear-gradient(135deg,#5b7cfa,#a78bfa);color:white}
.mbtns .s{background:var(--input);color:var(--text-soft);border:1px solid var(--border)}
</style></head><body>

<div id="login">
<div class="logo-big">__LOGO_SVG__</div>
<div class="lt">Moka.AI</div>
<div class="ls">مساعدك الذكي من تطوير محمد كامل</div>
<div class="lb">
<label>👤 اسم المستخدم</label>
<input id="un" placeholder="اكتب اسم المستخدم...">
<label>🔒 كلمة المرور</label>
<div class="pw-wrap">
<input id="pw" type="password" placeholder="اكتب كلمة المرور...">
<button type="button" class="pw-toggle" id="pwToggle" onclick="togglePw()">👁️</button>
</div>
<button class="main" onclick="login()">🚀 تسجيل الدخول</button>
<button class="secondary" onclick="register()">✨ إنشاء حساب جديد</button>
<div class="hint">💡 يمكنك إنشاء حسابك الخاص بحرية تامة</div>
</div>
</div>

<div class="ov" id="ov" onclick="closeS()"></div>
<div class="sb" id="sb">
<div class="avatar" id="avatar">M</div>
<div class="username" id="uname">مستخدم</div>
<div class="role" id="urole">عضو</div>
<h2>النماذج</h2>
<button class="mb on" data-m="general" onclick="sw('general')">🧠 النسخة العامة</button>
<button class="mb" data-m="math" onclick="sw('math')">📐 الرياضيات</button>
<button class="mb" data-m="code" onclick="sw('code')">💻 البرمجة</button>
<button class="mb" data-m="religion" onclick="sw('religion')">🕌 العلوم الإسلامية</button>
<h2>الأدوات</h2>
<button class="mb" onclick="openSummaries()">📚 ملخصات الدروس</button>
<button class="mb" onclick="openM()">📝 تلخيص نص</button>
<button class="dl" onclick="downloadChat()">💾 تنزيل المحادثة</button>
<button class="lo" onclick="out()">🚪 تسجيل الخروج</button>
</div>

<div id="app">
<div class="hd">
<button class="hb" onclick="openS()">☰</button>
<div class="tg"><div class="hl-logo">__LOGO_SVG__</div><h1>Moka.AI</h1></div>
<div style="width:50px"></div>
</div>
<div id="ch">
<div class="welcome" id="welcome">
<div style="width:110px;height:110px">__LOGO_SVG__</div>
<h2>كيف يمكنني مساعدتك؟</h2>
<p>اسألني أي شيء، أو افتح ملخصات الدروس 📚</p>
</div>
</div>
<form class="ia" id="f">
<button type="button" class="sd copy-main" onclick="copyLast()" title="نسخ آخر رد">📋</button>
<div class="iw"><textarea id="i" placeholder="أرسل رسالة..." rows="1" oninput="autoResize(this)" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();f.requestSubmit()}"></textarea></div>
<button type="submit" class="sd" id="s">➤</button>
</form>
<div class="vc">Moka.AI © 2026 | الزوار: <span id="vc">...</span></div>
</div>

<div class="mo" id="mo"><div class="md"><h2>📝 تلخيص نص</h2><textarea id="st" placeholder="الصق النص هنا..."></textarea>
<div class="mbtns"><button class="s" onclick="closeM()">إلغاء</button><button class="p" onclick="doSum()">لخّص</button></div></div></div>

<div class="mo" id="summariesModal"><div class="md">
<h2>📚 ملخصات الدروس</h2>
<label>المستوى</label>
<select id="s_level" onchange="updateBranches()">
<option value="">اختر المستوى</option>
<option value="السنة الأولى متوسط">السنة الأولى متوسط</option>
<option value="السنة الثانية متوسط">السنة الثانية متوسط</option>
<option value="السنة الثالثة متوسط">السنة الثالثة متوسط</option>
<option value="السنة الرابعة متوسط (BEM)">السنة الرابعة متوسط (BEM)</option>
<option value="السنة الأولى ثانوي">السنة الأولى ثانوي</option>
<option value="السنة الثانية ثانوي">السنة الثانية ثانوي</option>
<option value="السنة الثالثة ثانوي (BAC)">السنة الثالثة ثانوي (BAC)</option>
</select>
<label>الشعبة</label>
<select id="s_branch"><option value="">اختر المستوى أولاً</option></select>
<label>المادة</label>
<select id="s_subject"><option value="">اختر الشعبة أولاً</option></select>
<label>الدرس</label>
<input id="s_lesson" placeholder="اكتب اسم الدرس...">
<div class="mbtns"><button class="s" onclick="closeSummaries()">إلغاء</button><button class="p" onclick="generateSummary()">📚 أنشئ الملخص</button></div>
</div></div>

<script>
let mode="general";
let isAdmin=false;
let lastReply="";
const ch=document.getElementById("ch"),i=document.getElementById("i"),f=document.getElementById("f"),s=document.getElementById("s");
const sid="u_"+Math.random().toString(36).substring(2,10);
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"visit"})});
function autoResize(t){t.style.height="auto";t.style.height=Math.min(t.scrollHeight,140)+"px"}
function togglePw(){
  const pw=document.getElementById("pw");
  const btn=document.getElementById("pwToggle");
  if(pw.type==="password"){pw.type="text";btn.textContent="🙈";}
  else{pw.type="password";btn.textContent="👁️";}
}
async function login(){
  const u=document.getElementById("un").value.trim();
  const p=document.getElementById("pw").value.trim();
  if(!u||!p){alert("املأ اسم المستخدم وكلمة المرور");return}
  try{
    const r=await fetch("/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,password:p})});
    const d=await r.json();
    if(!d.ok){alert("❌ "+d.msg);return}
    isAdmin=d.role==="admin";
    localStorage.setItem("mu",d.name);
    localStorage.setItem("muser",u);
    localStorage.setItem("mrole",d.role);
    show(d.name,d.role);
    fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"login",name:d.name})});
  }catch(e){alert("تعذر الاتصال بالخادم")}
}
async function register(){
  const u=document.getElementById("un").value.trim();
  const p=document.getElementById("pw").value.trim();
  if(!u||!p){alert("املأ اسم المستخدم وكلمة المرور");return}
  if(u.length<3){alert("اسم المستخدم يجب أن يكون 3 أحرف على الأقل");return}
  if(p.length<4){alert("كلمة المرور يجب أن تكون 4 أحرف على الأقل");return}
  if(u.toLowerCase()==="kamel"){alert("هذا الاسم محجوز");return}
  try{
    const r=await fetch("/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,password:p})});
    const d=await r.json();
    if(!d.ok){alert("❌ "+d.msg);return}
    alert("✅ تم إنشاء الحساب بنجاح!\\nيمكنك الآن تسجيل الدخول.");
  }catch(e){alert("تعذر الاتصال بالخادم")}
}
function show(n,r){document.getElementById("login").classList.add("hide");document.getElementById("app").classList.add("on");
document.getElementById("avatar").textContent=n.charAt(0).toUpperCase();
document.getElementById("uname").textContent=n;
document.getElementById("urole").textContent=r==="admin"?"👑 المطور":"عضو";}
function out(){if(!confirm("تسجيل الخروج؟"))return;localStorage.clear();location.reload()}
function openS(){document.getElementById("sb").classList.add("on");document.getElementById("ov").classList.add("on")}
function closeS(){document.getElementById("sb").classList.remove("on");document.getElementById("ov").classList.remove("on")}
function sw(m){mode=m;document.querySelectorAll(".mb").forEach(b=>b.classList.toggle("on",b.dataset.m===m));
const names={general:"🧠 العامة",math:"📐 الرياضيات",code:"💻 البرمجة",religion:"🕌 الدينية"};
ch.innerHTML='<div class="welcome"><div style="width:110px;height:110px">__LOGO_SVG__</div><h2>'+names[m]+'</h2><p>كيف يمكنني مساعدتك؟</p></div>';closeS()}
window.onload=()=>{const n=localStorage.getItem("mu");const r=localStorage.getItem("mrole");
if(n&&r){isAdmin=r==="admin";show(n,r)}}
let v=localStorage.getItem("mv");v=v?parseInt(v)+1:1;localStorage.setItem("mv",v);document.getElementById("vc").textContent=v;
function add(t,c){const w=document.getElementById("welcome");if(w)w.remove();
const wrapper=document.createElement("div");wrapper.className="mw "+c;
const m=document.createElement("div");m.className="m";m.textContent=t;
if(c==="b"){const cp=document.createElement("button");cp.className="copy-btn";cp.textContent="📋 نسخ";cp.onclick=()=>{navigator.clipboard.writeText(t);cp.textContent="✅ تم";setTimeout(()=>cp.textContent="📋 نسخ",1500)};wrapper.appendChild(cp);lastReply=t;}
wrapper.appendChild(m);ch.appendChild(wrapper);ch.scrollTop=ch.scrollHeight}
function typ(){const w=document.createElement("div");w.className="mw b";const t=document.createElement("div");t.className="tp";t.innerHTML="<span></span><span></span><span></span>";w.appendChild(t);ch.appendChild(w);ch.scrollTop=ch.scrollHeight;return w}
function copyLast(){if(!lastReply){alert("لا يوجد رد للنسخ");return}navigator.clipboard.writeText(lastReply);alert("✅ تم نسخ آخر رد")}
f.onsubmit=async(e)=>{e.preventDefault();const t=i.value.trim();if(!t)return;add(t,"u");i.value="";i.style.height="auto";s.disabled=true;const ty=typ();
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"message",mode:mode,text:t,name:localStorage.getItem("mu")||"?"})});
try{const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:t,session_id:sid,mode:mode,is_admin:isAdmin})});
const d=await r.json();ty.remove();add(d.reply||"خطأ","b")}catch(e){ty.remove();add("تعذر الاتصال","b")}finally{s.disabled=false;i.focus()}};
function openM(){document.getElementById("mo").classList.add("on")}
function closeM(){document.getElementById("mo").classList.remove("on")}
async function doSum(){const t=document.getElementById("st").value.trim();if(!t){alert("الصق النص");return}closeM();document.getElementById("st").value="";
add("📝 لخّص: "+t.substring(0,80)+"...","u");const ty=typ();
try{const r=await fetch("/summarize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:t})});
const d=await r.json();ty.remove();add(d.summary||"خطأ","b")}catch(e){ty.remove();add("تعذر","b")}}
function openSummaries(){document.getElementById("summariesModal").classList.add("on")}
function closeSummaries(){document.getElementById("summariesModal").classList.remove("on")}
function updateBranches(){
  const level=document.getElementById("s_level").value;
  const branchSel=document.getElementById("s_branch");
  const subjSel=document.getElementById("s_subject");
  if(level.includes("متوسط")){
    branchSel.innerHTML='<option value="جميع الشعب">جميع الشعب</option>';
    subjSel.innerHTML='<option value="الرياضيات">الرياضيات</option><option value="الفيزياء">الفيزياء</option><option value="العلوم الطبيعية">العلوم الطبيعية</option><option value="اللغة العربية">اللغة العربية</option><option value="اللغة الفرنسية">اللغة الفرنسية</option><option value="اللغة الإنجليزية">اللغة الإنجليزية</option><option value="التاريخ والجغرافيا">التاريخ والجغرافيا</option><option value="التربية الإسلامية">التربية الإسلامية</option><option value="التربية المدنية">التربية المدنية</option>';
  } else if(level.includes("ثانوي")){
    branchSel.innerHTML='<option value="جذع مشترك آداب">جذع مشترك آداب</option><option value="جذع مشترك علوم">جذع مشترك علوم</option><option value="علوم تجريبية">علوم تجريبية</option><option value="رياضيات">رياضيات</option><option value="تقني رياضي">تقني رياضي</option><option value="تسيير واقتصاد">تسيير واقتصاد</option><option value="آداب وفلسفة">آداب وفلسفة</option><option value="لغات أجنبية">لغات أجنبية</option>';
    subjSel.innerHTML='<option value="الرياضيات">الرياضيات</option><option value="الفيزياء">الفيزياء</option><option value="العلوم الطبيعية">العلوم الطبيعية</option><option value="اللغة العربية">اللغة العربية</option><option value="الفلسفة">الفلسفة</option><option value="التاريخ والجغرافيا">التاريخ والجغرافيا</option><option value="العلوم الإسلامية">العلوم الإسلامية</option><option value="اللغة الفرنسية">اللغة الفرنسية</option><option value="اللغة الإنجليزية">اللغة الإنجليزية</option>';
  } else {
    branchSel.innerHTML='<option value="">اختر المستوى أولاً</option>';
    subjSel.innerHTML='<option value="">اختر الشعبة أولاً</option>';
  }
}
async function generateSummary(){
  const level=document.getElementById("s_level").value;
  const branch=document.getElementById("s_branch").value;
  const subject=document.getElementById("s_subject").value;
  const lesson=document.getElementById("s_lesson").value.trim();
  if(!level||!branch||!subject||!lesson){alert("املأ جميع الحقول");return}
  closeSummaries();
  add("📚 طلب ملخص: "+level+" | "+branch+" | "+subject+" | "+lesson,"u");
  const ty=typ();
  try{
    const r=await fetch("/lesson_summary",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({level,branch,subject,lesson})});
    const d=await r.json();ty.remove();add(d.summary||"خطأ","b");
  }catch(e){ty.remove();add("تعذر الاتصال","b")}
}
function downloadChat(){
  const name=localStorage.getItem("mu")||"مستخدم";
  let text="محادثة Moka.AI - "+name+"\\n"+new Date().toLocaleString("ar-DZ")+"\\n\\n";
  document.querySelectorAll("#ch .mw").forEach(m=>{
    const isUser=m.classList.contains("u");const content=m.querySelector(".m");
    if(content){text+=(isUser?"👤 "+name:"🤖 Moka.AI")+":\\n"+content.textContent+"\\n\\n";}
  });
  const blob=new Blob([text],{type:"text/plain;charset=utf-8"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);
  a.download="MokaAI_"+name+"_"+Date.now()+".txt";a.click();
}
</script></body></html>"""

HTML = HTML.replace("__LOGO_SVG__", LOGO_SVG)
ADMIN_HTML = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>لوحة التحكم</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#f7f8fc;color:#1a1f36;font-family:Tahoma,sans-serif;padding:24px;line-height:1.6}
h1{text-align:center;margin-bottom:24px;background:linear-gradient(90deg,#5b7cfa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-bottom:24px}
.card{background:white;border:1px solid #e4e7f0;border-radius:14px;padding:22px;text-align:center;box-shadow:0 4px 20px rgba(91,124,250,.06)}
.card .num{font-size:34px;font-weight:bold;color:#5b7cfa;margin-bottom:6px}
.card .lbl{font-size:13px;color:#8b91a8}
.box{background:white;border:1px solid #e4e7f0;border-radius:14px;padding:22px;margin-bottom:24px;box-shadow:0 4px 20px rgba(91,124,250,.06)}
.box h2{font-size:16px;margin-bottom:16px;color:#5b7cfa}
.row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #e4e7f0;font-size:13px;gap:10px;align-items:center;flex-wrap:wrap}
.mode-bar{display:flex;justify-content:space-between;padding:12px;background:#f7f8fc;border-radius:10px;margin-bottom:10px}
.msg-item{background:#f7f8fc;border-radius:10px;padding:14px;margin-bottom:12px;border-right:3px solid #5b7cfa}
.msg-item .meta{color:#8b91a8;font-size:11px;margin-bottom:8px;display:flex;gap:12px;flex-wrap:wrap}
.msg-item .text{color:#1a1f36;font-size:14px;line-height:1.7;white-space:pre-wrap;word-wrap:break-word}
.block-btn{background:#dc2626;color:white;border:none;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;display:inline-block}
.unblock-btn{background:#5b7cfa;color:white;border:none;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;display:inline-block;margin-right:6px}
</style></head><body>
<h1>📊 لوحة تحكم Moka.AI</h1>
<div class="grid">
<div class="card"><div class="num">{{s.visitors}}</div><div class="lbl">👁️ الزوار</div></div>
<div class="card"><div class="num">{{s.logins}}</div><div class="lbl">🔑 تسجيلات</div></div>
<div class="card"><div class="num">{{s.messages}}</div><div class="lbl">💬 رسائل</div></div>
<div class="card"><div class="num">{{s.summaries}}</div><div class="lbl">📝 تلخيص</div></div>
<div class="card"><div class="num">{{users_count}}</div><div class="lbl">👥 حسابات</div></div>
</div>
<div class="box"><h2>👥 قائمة الحسابات</h2>
{% for u, info in users.items() %}
<div class="row"><span>👤 <b>{{info.name}}</b> ({{u}})</span><span style="color:#8b91a8">{{info.role}}</span></div>
{% endfor %}
</div>
<div class="box"><h2>📈 استخدام النماذج</h2>
<div class="mode-bar"><span>🧠 عامة</span><b>{{s.modes.general}}</b></div>
<div class="mode-bar"><span>📐 رياضيات</span><b>{{s.modes.math}}</b></div>
<div class="mode-bar"><span>💻 برمجة</span><b>{{s.modes.code}}</b></div>
<div class="mode-bar"><span>🕌 دينية</span><b>{{s.modes.religion}}</b></div>
</div>
<div class="box"><h2>💬 كل الرسائل (آخر 50)</h2>
{% if s.messages_log %}{% for m in s.messages_log[-50:]|reverse %}
<div class="msg-item"><div class="meta"><span>👤 <b>{{m.name}}</b></span><span>📱 {{m.ip}}</span><span>🧠 {{m.mode}}</span><span>🕐 {{m.time}}</span></div><div class="text">💬 {{m.text}}</div></div>
{% endfor %}{% else %}<p style="color:#8b91a8;text-align:center;">لا توجد رسائل بعد.</p>{% endif %}
</div>
<div class="box"><h2>🕐 آخر 20 زيارة</h2>
{% for r in s.recent[-20:]|reverse %}
<div class="row"><span>👤 {{r.name}}</span><span style="color:#8b91a8">📱 {{r.device}}</span><span style="color:#8b91a8">{{r.ip}}</span><span style="color:#8b91a8">{{r.time}}</span>
<a href="/block/{{r.ip}}?key={{key}}" class="block-btn">🚫</a><a href="/unblock/{{r.ip}}?key={{key}}" class="unblock-btn">✅</a></div>
{% endfor %}</div>
<div class="box"><h2>📱 آخر 20 جهاز</h2>
{% for d in s.devices[-20:]|reverse %}
<div class="row"><span>📱 {{d.device}}</span><span style="color:#8b91a8">🌐 {{d.browser}}</span><span style="color:#8b91a8">{{d.ip}}</span><span style="color:#8b91a8">{{d.time}}</span>
<a href="/block/{{d.ip}}?key={{key}}" class="block-btn">🚫</a><a href="/unblock/{{d.ip}}?key={{key}}" class="unblock-btn">✅</a></div>
{% endfor %}</div>
</body></html>"""

@app.route("/")
def home(): return render_template_string(HTML)

@app.route("/manifest.json")
def manifest():
    return {"name":"Moka.AI","short_name":"Moka.AI","start_url":"/","display":"standalone",
            "background_color":"#f7f8fc","theme_color":"#5b7cfa","orientation":"portrait","lang":"ar","dir":"rtl"}

@app.route("/sw.js")
def sw():
    return "const CACHE='moka-v10';self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',e=>e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));", 200, {'Content-Type': 'application/javascript'}

@app.post("/login")
def do_login():
    try:
        d = request.get_json(silent=True) or {}
        u = d.get("username", "").strip().lower()
        p = d.get("password", "").strip()
        users = load_users()
        if u in users and users[u]["password"] == p:
            return jsonify({"ok": True, "name": users[u]["name"], "role": users[u]["role"]})
        return jsonify({"ok": False, "msg": "اسم المستخدم أو كلمة المرور غير صحيحة"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

@app.post("/register")
def do_register():
    try:
        d = request.get_json(silent=True) or {}
        u = d.get("username", "").strip().lower()
        p = d.get("password", "").strip()
        if not u or not p: return jsonify({"ok": False, "msg": "املأ جميع الحقول"})
        if len(u) < 3: return jsonify({"ok": False, "msg": "اسم المستخدم قصير جداً (3 أحرف على الأقل)"})
        if len(p) < 4: return jsonify({"ok": False, "msg": "كلمة المرور قصيرة جداً (4 أحرف على الأقل)"})
        if u == "kamel": return jsonify({"ok": False, "msg": "هذا الاسم محجوز"})
        users = load_users()
        if u in users: return jsonify({"ok": False, "msg": "اسم المستخدم موجود مسبقاً، اختر اسماً آخر"})
        users[u] = {"password": p, "role": "user", "name": u}
        save_users(users)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

@app.route("/admin")
def admin():
    if request.args.get("key") != ADMIN_KEY: return "🔒 ممنوع.", 403
    users = load_users()
    return render_template_string(ADMIN_HTML, s=load_stats(), key=ADMIN_KEY, users=users, users_count=len(users))

@app.route("/block/<ip>")
def block_ip(ip):
    if request.args.get("key") != ADMIN_KEY: return "🔒", 403
    BLOCKED_IPS.add(ip)
    return f"✅ تم حظر {ip}. <a href='/admin?key={ADMIN_KEY}'>العودة</a>"

@app.route("/unblock/<ip>")
def unblock_ip(ip):
    if request.args.get("key") != ADMIN_KEY: return "🔒", 403
    BLOCKED_IPS.discard(ip)
    return f"✅ تم إلغاء حظر {ip}. <a href='/admin?key={ADMIN_KEY}'>العودة</a>"

@app.route("/track", methods=["POST"])
def track():
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
        if ip in BLOCKED_IPS: return jsonify({"ok": False, "blocked": True}), 403
        d = request.get_json(silent=True) or {}
        t = d.get("type", "")
        ua = request.headers.get("User-Agent", "?")
        s = load_stats()
        device = "غير معروف"; browser = "غير معروف"
        if "Android" in ua: device = "Android"
        elif "iPhone" in ua or "iPad" in ua: device = "iPhone/iPad"
        elif "Windows" in ua: device = "Windows"
        elif "Mac" in ua: device = "Mac"
        if "Chrome" in ua: browser = "Chrome"
        elif "Firefox" in ua: browser = "Firefox"
        elif "Safari" in ua: browser = "Safari"
        elif "Edge" in ua: browser = "Edge"
        if t == "visit":
            s["visitors"] += 1
            s["devices"].append({"ip": ip[:15], "device": device, "browser": browser, "time": datetime.datetime.now().strftime("%m/%d %H:%M")})
            s["devices"] = s["devices"][-50:]
        elif t == "login":
            s["logins"] += 1
            s["recent"].append({"name": d.get("name", "?"), "ip": ip[:15], "device": device, "time": datetime.datetime.now().strftime("%m/%d %H:%M")})
            s["recent"] = s["recent"][-50:]
        elif t == "message":
            s["messages"] += 1
            m = d.get("mode", "general")
            if m in s["modes"]: s["modes"][m] += 1
            s["messages_log"].append({"ip": ip[:15], "name": d.get("name", "?"), "text": d.get("text", "")[:200], "mode": m, "time": datetime.datetime.now().strftime("%m/%d %H:%M")})
            s["messages_log"] = s["messages_log"][-100:]
        elif t == "summary":
            s["summaries"] += 1
        save_stats(s)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "err": str(e)}), 500

@app.post("/chat")
def chat():
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
        if ip in BLOCKED_IPS: return jsonify({"reply": "🚫 تم حظرك."}), 403
        d = request.get_json(silent=True) or {}
        return jsonify({"reply": ask_ai(d.get("message",""), d.get("session_id","default"), d.get("mode","general"), d.get("is_admin", False))})
    except Exception as e: return jsonify({"reply":f"خطأ: {str(e)}"}),500

@app.post("/summarize")
def summ():
    try:
        d = request.get_json(silent=True) or {}
        return jsonify({"summary": summarize(d.get("text",""))})
    except Exception as e: return jsonify({"summary":f"خطأ: {str(e)}"}),500

@app.post("/lesson_summary")
def lesson_summary():
    try:
        d = request.get_json(silent=True) or {}
        return jsonify({"summary": generate_lesson_summary(d.get("level",""), d.get("branch",""), d.get("subject",""), d.get("lesson",""))})
    except Exception as e:
        return jsonify({"summary": f"⚠️ خطأ: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
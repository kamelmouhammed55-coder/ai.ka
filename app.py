# ============================================================
# Moka.AI v5.0 - مساعد ذكي عربي متطور
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

def load_stats():
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"visitors": 0, "logins": 0, "messages": 0, "summaries": 0,
                "modes": {"general": 0, "math": 0, "code": 0, "religion": 0, "edit": 0},
                "recent": [], "messages_log": [], "devices": []}

def save_stats(s):
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_date_context():
    today = _dt.datetime.now()
    months_ar = ["يناير", "فبراير", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
    days_ar = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    return f"""معلومات مهمة عنك وعن التاريخ:
- اليوم هو: {days_ar[today.weekday()]} {today.day} {months_ar[today.month-1]} {today.year}
- الوقت الحالي: {today.strftime('%H:%M')}
- تاريخ إنشاء التطبيق: 4 أكتوبر 2026
- مطورك: محمد كامل
- إذا سُئلت "متى صنعت؟" أو "متى تم إنشاؤك؟" أجب حرفياً: "صنعني محمد كامل يوم 4 أكتوبر 2026."
- لا تقل أبداً أنك GPT أو OpenAI.
- إذا سُئلت عن تاريخ مستقبلي، احسب الفرق بالأيام من اليوم واذكر "بعد X أيام".
"""

CURRICULUM = """
المنهاج الجزائري 2026-2027:
- الابتدائي: الإنجليزية من السنة الثالثة.
- المتوسط: معامل الرياضيات 4 في الرابعة متوسط.
- الثانوي: جذع آداب (31 ساعة)، علوم (32 ساعة).
- شهادة التعليم المتوسط (BEM) والبكالوريا (BAC).
"""

FORBIDDEN = ["جنس", "sex", "porn", "إباحي", "عاري", "شهوة", "زنى", "زنا", "خلاعة", "فاحشة"]

def is_forbidden(text):
    return any(w in text.lower() for w in FORBIDDEN)

DATE_CONTEXT = get_date_context()

PROMPTS = {
    "general": f"أنت Moka.AI، مساعد ذكي عربي من تطوير محمد كامل. أجب بالعربية الفصحى المبسطة.\n\n{CURRICULUM}\n\n{DATE_CONTEXT}",
    "math": f"أنت Moka.AI، خبير رياضيات (جبر، هندسة، تفاضل، تكامل). اشرح خطوة بخطوة.\n\n{DATE_CONTEXT}",
    "code": f"أنت Moka.AI، خبير برمجة. اكتب الكود منسقاً واشرحه.\n\n{DATE_CONTEXT}",
    "religion": f"أنت Moka.AI، مساعد في العلوم الإسلامية. اذكر الأدلة من القرآن والسنة.\n\n{DATE_CONTEXT}",
    "edit": f"أنت Moka.AI، خبير تحرير صور.\n\n{DATE_CONTEXT}",
    "summary": f"أنت Moka.AI، مساعد تعليمي. أعد ملخصات دروس مفصلة.\n\n{CURRICULUM}\n\n{DATE_CONTEXT}",
}

convs = {}

def ask_ai(msg, sid, mode):
    if not GROQ_API_KEY: return "⚠️ مفتاح API غير موجود."
    if not GROQ_API_KEY.startswith("gsk_"): return "⚠️ المفتاح غير صحيح."
    if is_forbidden(msg): return "🚫 عذراً، لا يمكنني الإجابة على هذا النوع من الأسئلة."
    key = f"{sid}_{mode}"
    if key not in convs:
        convs[key] = [{"role": "system", "content": PROMPTS.get(mode, PROMPTS["general"])}]
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
                    {"role": "system", "content": "لخص النص في نقاط واضحة بالعربية."},
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
LOGO_SVG = '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="lg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#6d8cff"/><stop offset="100%" style="stop-color:#a78bfa"/></linearGradient></defs><circle cx="50" cy="50" r="48" fill="url(#lg)"/><circle cx="35" cy="42" r="4" fill="white"/><circle cx="65" cy="42" r="4" fill="white"/><path d="M 30 62 Q 50 80 70 62" stroke="white" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M 35 30 L 45 45 L 50 38 L 55 45 L 65 30" stroke="white" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/></svg>'''

HTML = """<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moka.AI</title><link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#6d8cff">
<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js');}</script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0f1117;
  --bg2:#151821;
  --sidebar:#1a1e2a;
  --input:#1e2330;
  --user:#2a3142;
  --bot:#1a1f2e;
  --text:#e8eaf0;
  --text-soft:#b8bdc9;
  --text-mute:#7a8094;
  --border:#252b3a;
  --accent:#6d8cff;
  --accent2:#a78bfa;
  --accent-soft:rgba(109,140,255,.12);
}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',Tahoma,sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden;line-height:1.6}

#login{position:fixed;inset:0;background:radial-gradient(circle at center,#1e2330 0%,#0f1117 70%);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:999;padding:24px}
#login.hide{display:none}
.logo-big{width:140px;height:140px;margin-bottom:28px;animation:float 3s ease-in-out infinite;filter:drop-shadow(0 15px 35px rgba(109,140,255,.4))}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}
.lt{font-size:44px;font-weight:700;margin-bottom:10px;background:linear-gradient(90deg,#6d8cff,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.ls{color:var(--text-mute);margin-bottom:40px;font-size:15px}
.lb{width:100%;max-width:380px;background:rgba(26,30,42,.9);border:1px solid var(--border);border-radius:24px;padding:32px;backdrop-filter:blur(20px);box-shadow:0 20px 60px rgba(0,0,0,.4)}
.lb label{display:block;font-size:13px;color:var(--text-soft);margin-bottom:10px;font-weight:500}
.lb input{width:100%;padding:16px 18px;border-radius:14px;border:1px solid var(--border);background:#0f1117;color:var(--text);font-size:16px;outline:none;margin-bottom:20px;transition:border-color .3s}
.lb input:focus{border-color:var(--accent)}
.lb button{width:100%;padding:16px;border-radius:14px;border:none;background:linear-gradient(135deg,#6d8cff,#a78bfa);color:white;font-size:16px;font-weight:600;cursor:pointer;transition:transform .2s}
.lb button:active{transform:scale(.98)}

#app{display:none;height:100vh;flex-direction:column}
#app.on{display:flex}
.ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:998;backdrop-filter:blur(2px)}
.ov.on{display:block}
.sb{position:fixed;top:0;right:-340px;width:320px;height:100%;background:var(--sidebar);border-left:1px solid var(--border);z-index:999;transition:right .3s;padding:26px;display:flex;flex-direction:column;gap:10px;overflow-y:auto}
.sb.on{right:0}
.sb h2{font-size:12px;color:var(--text-mute);margin:14px 0 8px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}
.avatar{width:92px;height:92px;border-radius:50%;background:linear-gradient(135deg,#6d8cff,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:42px;font-weight:bold;color:white;margin:0 auto 14px;box-shadow:0 10px 30px rgba(109,140,255,.3)}
.username{text-align:center;font-size:18px;font-weight:600;margin-bottom:28px;color:var(--text)}
.mb{padding:14px 16px;border-radius:14px;border:1px solid transparent;background:transparent;color:var(--text-soft);cursor:pointer;text-align:right;font-size:14px;display:flex;align-items:center;gap:12px;transition:all .2s;font-family:inherit}
.mb:hover{background:var(--accent-soft);color:var(--text)}
.mb.on{background:linear-gradient(90deg,rgba(109,140,255,.18),rgba(167,139,250,.18));border-color:rgba(109,140,255,.4);color:var(--text);font-weight:600}
.lo{margin-top:auto;padding:14px;border-radius:14px;border:1px solid rgba(220,38,38,.4);background:transparent;color:#f87171;cursor:pointer;font-size:14px;font-family:inherit;transition:all .2s}
.lo:hover{background:rgba(220,38,38,.1)}
.dl{padding:14px;border-radius:14px;border:1px solid var(--border);background:transparent;color:var(--text-soft);cursor:pointer;font-size:14px;margin-top:6px;font-family:inherit;transition:all .2s}
.dl:hover{border-color:var(--accent);color:var(--accent)}

.hd{padding:16px 20px;border-bottom:1px solid var(--border);background:var(--bg2);display:flex;align-items:center;justify-content:space-between;backdrop-filter:blur(10px)}
.tg{display:flex;align-items:center;gap:12px;margin:0 auto}
.hl-logo{width:40px;height:40px}
h1{font-size:20px;font-weight:700;background:linear-gradient(90deg,#6d8cff,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hb{background:transparent;border:1px solid var(--border);color:var(--text-soft);padding:10px 14px;border-radius:12px;cursor:pointer;font-size:16px;transition:all .2s;font-family:inherit}
.hb:hover{background:var(--accent-soft);border-color:var(--accent)}

#ch{flex:1;overflow-y:auto;padding:28px 20px;display:flex;flex-direction:column;gap:22px;scroll-behavior:smooth}
#ch::-webkit-scrollbar{width:8px}
#ch::-webkit-scrollbar-track{background:transparent}
#ch::-webkit-scrollbar-thumb{background:#2a3142;border-radius:4px}
#ch::-webkit-scrollbar-thumb:hover{background:#3a4254}

.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:20px;text-align:center;padding:24px}
.welcome svg{width:110px;height:110px;opacity:.95}
.welcome h2{font-size:26px;font-weight:600;background:linear-gradient(90deg,#6d8cff,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.welcome p{color:var(--text-mute);font-size:15px;max-width:300px;line-height:1.7}

.mw{display:flex;max-width:92%;animation:si .4s ease}
.mw.u{align-self:flex-end}
.mw.b{align-self:flex-start}
@keyframes si{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.m{padding:16px 20px;border-radius:20px;line-height:1.8;white-space:pre-wrap;word-wrap:break-word;font-size:15px;letter-spacing:.2px}
.u .m{background:linear-gradient(135deg,#2a3142,#2d3548);border-bottom-left-radius:6px;color:var(--text)}
.b .m{background:var(--bot);border:1px solid var(--border);border-bottom-right-radius:6px;color:var(--text-soft)}
.m img{max-width:240px;border-radius:14px;margin-top:12px;display:block;border:1px solid var(--border)}

.tp{display:inline-flex;gap:6px;padding:18px 22px;background:var(--bot);border:1px solid var(--border);border-radius:20px;border-bottom-right-radius:6px}
.tp span{width:8px;height:8px;background:var(--accent);border-radius:50%;animation:bo 1.4s infinite}
.tp span:nth-child(2){animation-delay:.2s}
.tp span:nth-child(3){animation-delay:.4s}
@keyframes bo{0%,60%,100%{transform:translateY(0);opacity:.3}30%{transform:translateY(-8px);opacity:1}}

.ia{padding:18px 20px 22px;background:var(--bg2);display:flex;gap:12px;align-items:flex-end;border-top:1px solid var(--border)}
.iw{flex:1}
textarea{width:100%;padding:16px 20px;border-radius:22px;border:1px solid var(--border);background:var(--input);color:var(--text);font-size:16px;outline:none;font-family:inherit;resize:none;max-height:140px;line-height:1.5;transition:border-color .3s;letter-spacing:.2px}
textarea:focus{border-color:var(--accent)}
textarea::placeholder{color:var(--text-mute)}
button.sd{width:52px;height:52px;border-radius:50%;border:none;background:linear-gradient(135deg,#6d8cff,#a78bfa);color:white;font-size:20px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all .2s;box-shadow:0 6px 20px rgba(109,140,255,.3)}
button.sd:hover{transform:scale(1.05)}
button.sd:active{transform:scale(.95)}
button.sd:disabled{opacity:.4;cursor:not-allowed}
button.file{background:var(--input);border:1px solid var(--border);color:var(--text-soft);box-shadow:none}
button.file:hover{background:var(--accent-soft);color:var(--accent);border-color:var(--accent)}
.vc{text-align:center;padding:10px;font-size:11px;color:var(--text-mute);background:var(--bg2);letter-spacing:.5px}

.mo{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;justify-content:center;align-items:center;padding:20px;overflow-y:auto;backdrop-filter:blur(4px)}
.mo.on{display:flex}
.md{background:var(--sidebar);border:1px solid var(--border);border-radius:24px;padding:28px;width:100%;max-width:520px;display:flex;flex-direction:column;gap:16px;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.5)}
.md h2{font-size:20px;font-weight:600;background:linear-gradient(90deg,#6d8cff,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.md label{font-size:13px;color:var(--text-soft);margin-bottom:6px;display:block;font-weight:500}
.md select,.md input,.md textarea{width:100%;padding:14px 16px;border-radius:12px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:15px;outline:none;margin-bottom:12px;font-family:inherit;transition:border-color .3s}
.md select:focus,.md input:focus,.md textarea:focus{border-color:var(--accent)}
.md textarea{resize:vertical;min-height:180px;line-height:1.7}
.mbtns{display:flex;gap:12px;justify-content:flex-end;margin-top:8px}
.mbtns button{padding:14px 24px;border-radius:12px;border:none;cursor:pointer;font-size:14px;font-weight:600;font-family:inherit;transition:transform .2s}
.mbtns button:active{transform:scale(.97)}
.mbtns .p{background:linear-gradient(135deg,#6d8cff,#a78bfa);color:white;box-shadow:0 6px 20px rgba(109,140,255,.3)}
.mbtns .s{background:var(--input);color:var(--text-soft);border:1px solid var(--border)}

.tools{display:flex;gap:8px;padding:10px 20px;background:var(--bg2);overflow-x:auto;border-top:1px solid var(--border)}
.tools::-webkit-scrollbar{height:0}
.tool{padding:9px 16px;border-radius:20px;border:1px solid var(--border);background:var(--input);color:var(--text-soft);cursor:pointer;font-size:13px;white-space:nowrap;transition:all .2s;font-family:inherit}
.tool:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}
</style></head><body>

<div id="login">
<div class="logo-big">__LOGO_SVG__</div>
<div class="lt">Moka.AI</div>
<div class="ls">مساعدك الذكي من تطوير محمد كامل</div>
<div class="lb">
<label>👤 اسمك</label>
<input id="un" placeholder="اكتب اسمك هنا...">
<button onclick="login()">🚀 ابدأ المحادثة</button>
</div>
</div>

<div class="ov" id="ov" onclick="closeS()"></div>
<div class="sb" id="sb">
<div class="avatar" id="avatar">M</div>
<div class="username" id="uname">مستخدم</div>
<h2>النماذج</h2>
<button class="mb on" data-m="general" onclick="sw('general')">🧠 النسخة العامة</button>
<button class="mb" data-m="math" onclick="sw('math')">📐 الرياضيات</button>
<button class="mb" data-m="code" onclick="sw('code')">💻 البرمجة</button>
<button class="mb" data-m="religion" onclick="sw('religion')">🕌 العلوم الإسلامية</button>
<button class="mb" data-m="edit" onclick="sw('edit')">✏️ تحرير الصور</button>
<h2>الأدوات</h2>
<button class="mb" onclick="openSummaries()">📚 ملخصات الدروس</button>
<button class="mb" onclick="openM()">📝 تلخيص نص</button>
<button class="dl" onclick="downloadChat()">💾 تنزيل المحادثة</button>
<button class="lo" onclick="out()">🚪 تسجيل الخروج</button>
</div>

<div id="app">
<div class="hd">
<button class="hb" onclick="openS()">☰</button>
<div class="tg">
<div class="hl-logo">__LOGO_SVG__</div>
<h1>Moka.AI</h1>
</div>
<div style="width:50px"></div>
</div>
<div id="ch">
<div class="welcome" id="welcome">
<div style="width:110px;height:110px">__LOGO_SVG__</div>
<h2>كيف يمكنني مساعدتك؟</h2>
<p>اسألني أي شيء، أو افتح ملخصات الدروس 📚</p>
</div>
</div>
<div class="tools" id="tools" style="display:none">
<button class="tool" onclick="setAction('brighten')">☀️ إضاءة</button>
<button class="tool" onclick="setAction('contrast')">🎚️ تباين</button>
<button class="tool" onclick="setAction('enhance')">🎨 ألوان</button>
<button class="tool" onclick="setAction('blur')">💧 تمويه</button>
<button class="tool" onclick="setAction('sharpen')">✨ توضيح</button>
<button class="tool" onclick="setAction('grayscale')">⚫ أبيض وأسود</button>
<button class="tool" onclick="setAction('rotate')">🔄 تدوير</button>
</div>
<form class="ia" id="f">
<input type="file" id="fileInput" accept="image/*" style="display:none" onchange="handleFile(this)">
<button type="button" class="sd file" onclick="document.getElementById('fileInput').click()">📎</button>
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
let currentAction="describe";
const ch=document.getElementById("ch"),i=document.getElementById("i"),f=document.getElementById("f"),s=document.getElementById("s");
const sid="u_"+Math.random().toString(36).substring(2,10);
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"visit"})});
function autoResize(t){t.style.height="auto";t.style.height=Math.min(t.scrollHeight,140)+"px"}
function setAction(a){currentAction=a;const names={brighten:"☀️ إضاءة",contrast:"🎚️ تباين",enhance:"🎨 ألوان",blur:"💧 تمويه",sharpen:"✨ توضيح",grayscale:"⚫ أبيض وأسود",rotate:"🔄 تدوير"};
alert("تم اختيار: "+names[a]+"\\nالآن ارفع صورة 📎");}
function login(){const n=document.getElementById("un").value.trim();if(!n){alert("اكتب اسمك");return}
localStorage.setItem("mu",n);show(n);
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"login",name:n})});}
function show(n){document.getElementById("login").classList.add("hide");document.getElementById("app").classList.add("on");
document.getElementById("avatar").textContent=n.charAt(0).toUpperCase();
document.getElementById("uname").textContent=n;}
function out(){if(!confirm("تسجيل الخروج؟"))return;localStorage.removeItem("mu");location.reload()}
function openS(){document.getElementById("sb").classList.add("on");document.getElementById("ov").classList.add("on")}
function closeS(){document.getElementById("sb").classList.remove("on");document.getElementById("ov").classList.remove("on")}
function sw(m){mode=m;document.querySelectorAll(".mb").forEach(b=>b.classList.toggle("on",b.dataset.m===m));
const names={general:"🧠 العامة",math:"📐 الرياضيات",code:"💻 البرمجة",religion:"🕌 الدينية",edit:"✏️ تحرير الصور"};
ch.innerHTML='<div class="welcome"><div style="width:110px;height:110px">__LOGO_SVG__</div><h2>'+names[m]+'</h2><p>كيف يمكنني مساعدتك؟</p></div>';
document.getElementById("tools").style.display = (m==="edit") ? "flex" : "none";
closeS()}
window.onload=()=>{const n=localStorage.getItem("mu");if(n){document.getElementById("un").value=n;show(n)}}
let v=localStorage.getItem("mv");v=v?parseInt(v)+1:1;localStorage.setItem("mv",v);document.getElementById("vc").textContent=v;
function add(t,c){const w=document.getElementById("welcome");if(w)w.remove();
const wrapper=document.createElement("div");wrapper.className="mw "+c;
const m=document.createElement("div");m.className="m";m.textContent=t;
wrapper.appendChild(m);ch.appendChild(wrapper);ch.scrollTop=ch.scrollHeight}
function typ(){const w=document.createElement("div");w.className="mw b";const t=document.createElement("div");t.className="tp";t.innerHTML="<span></span><span></span><span></span>";w.appendChild(t);ch.appendChild(w);ch.scrollTop=ch.scrollHeight;return w}
f.onsubmit=async(e)=>{e.preventDefault();const t=i.value.trim();if(!t)return;add(t,"u");i.value="";i.style.height="auto";s.disabled=true;const ty=typ();
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"message",mode:mode,text:t,name:localStorage.getItem("mu")||"?"})});
try{const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:t,session_id:sid,mode:mode})});
const d=await r.json();ty.remove();add(d.reply||"خطأ","b")}catch(e){ty.remove();add("تعذر الاتصال","b")}finally{s.disabled=false;i.focus()}};
async function handleFile(input){
  const file=input.files[0];if(!file)return;
  if(!file.type.startsWith("image/")){alert("الرجاء اختيار صورة");return;}
  if(file.size>5*1024*1024){alert("حجم الصورة كبير (الحد 5 ميغا)");return;}
  const reader=new FileReader();
  reader.onload=async function(e){
    const base64=e.target.result.split(",")[1];
    const w=document.getElementById("welcome");if(w)w.remove();
    const wrap=document.createElement("div");wrap.className="mw u";const m=document.createElement("div");m.className="m";
    m.textContent="📎 "+file.name;
    const img=document.createElement("img");img.src=e.target.result;m.appendChild(img);
    wrap.appendChild(m);ch.appendChild(wrap);ch.scrollTop=ch.scrollHeight;
    const ty=typ();
    try{
      const r=await fetch("/edit_image",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({image:base64,action:currentAction})});
      const d=await r.json();ty.remove();
      if(d.image){
        const w2=document.createElement("div");w2.className="mw b";const m2=document.createElement("div");m2.className="m";
        m2.textContent=d.reply;
        const img2=document.createElement("img");img2.src="data:image/jpeg;base64,"+d.image;m2.appendChild(img2);
        w2.appendChild(m2);ch.appendChild(w2);ch.scrollTop=ch.scrollHeight;
      } else { add(d.reply||"تم","b"); }
    }catch(err){ty.remove();add("تعذر الاتصال","b")}
    input.value="";
  };
  reader.readAsDataURL(file);
}
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
body{background:#0f1117;color:#e8eaf0;font-family:Tahoma,sans-serif;padding:24px;line-height:1.6}
h1{text-align:center;margin-bottom:24px;background:linear-gradient(90deg,#6d8cff,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-bottom:24px}
.card{background:#1a1e2a;border:1px solid #252b3a;border-radius:14px;padding:22px;text-align:center}
.card .num{font-size:34px;font-weight:bold;color:#6d8cff;margin-bottom:6px}
.card .lbl{font-size:13px;color:#7a8094}
.box{background:#1a1e2a;border:1px solid #252b3a;border-radius:14px;padding:22px;margin-bottom:24px}
.box h2{font-size:16px;margin-bottom:16px;color:#6d8cff}
.row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #252b3a;font-size:13px;gap:10px;align-items:center;flex-wrap:wrap}
.mode-bar{display:flex;justify-content:space-between;padding:12px;background:#0f1117;border-radius:10px;margin-bottom:10px}
.msg-item{background:#0f1117;border-radius:10px;padding:14px;margin-bottom:12px;border-right:3px solid #6d8cff}
.msg-item .meta{color:#7a8094;font-size:11px;margin-bottom:8px;display:flex;gap:12px;flex-wrap:wrap}
.msg-item .text{color:#e8eaf0;font-size:14px;line-height:1.7;white-space:pre-wrap;word-wrap:break-word}
.block-btn{background:#dc2626;color:white;border:none;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;display:inline-block}
.unblock-btn{background:#6d8cff;color:white;border:none;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;display:inline-block;margin-right:6px}
</style></head><body>
<h1>📊 لوحة تحكم Moka.AI</h1>
<div class="grid">
<div class="card"><div class="num">{{s.visitors}}</div><div class="lbl">👁️ الزوار</div></div>
<div class="card"><div class="num">{{s.logins}}</div><div class="lbl">🔑 تسجيلات</div></div>
<div class="card"><div class="num">{{s.messages}}</div><div class="lbl">💬 رسائل</div></div>
<div class="card"><div class="num">{{s.summaries}}</div><div class="lbl">📝 تلخيص</div></div>
</div>
<div class="box"><h2>📈 استخدام النماذج</h2>
<div class="mode-bar"><span>🧠 عامة</span><b>{{s.modes.general}}</b></div>
<div class="mode-bar"><span>📐 رياضيات</span><b>{{s.modes.math}}</b></div>
<div class="mode-bar"><span>💻 برمجة</span><b>{{s.modes.code}}</b></div>
<div class="mode-bar"><span>🕌 دينية</span><b>{{s.modes.religion}}</b></div>
<div class="mode-bar"><span>✏️ تعديلات</span><b>{{s.modes.edit}}</b></div>
</div>
<div class="box"><h2>💬 كل الرسائل (آخر 50)</h2>
{% if s.messages_log %}{% for m in s.messages_log[-50:]|reverse %}
<div class="msg-item"><div class="meta"><span>👤 <b>{{m.name}}</b></span><span>📱 {{m.ip}}</span><span>🧠 {{m.mode}}</span><span>🕐 {{m.time}}</span></div><div class="text">💬 {{m.text}}</div></div>
{% endfor %}{% else %}<p style="color:#7a8094;text-align:center;">لا توجد رسائل بعد.</p>{% endif %}
</div>
<div class="box"><h2>🕐 آخر 20 زيارة</h2>
{% for r in s.recent[-20:]|reverse %}
<div class="row"><span>👤 {{r.name}}</span><span style="color:#7a8094">📱 {{r.device}}</span><span style="color:#7a8094">{{r.ip}}</span><span style="color:#7a8094">{{r.time}}</span>
<a href="/block/{{r.ip}}?key={{key}}" class="block-btn">🚫</a><a href="/unblock/{{r.ip}}?key={{key}}" class="unblock-btn">✅</a></div>
{% endfor %}</div>
<div class="box"><h2>📱 آخر 20 جهاز</h2>
{% for d in s.devices[-20:]|reverse %}
<div class="row"><span>📱 {{d.device}}</span><span style="color:#7a8094">🌐 {{d.browser}}</span><span style="color:#7a8094">{{d.ip}}</span><span style="color:#7a8094">{{d.time}}</span>
<a href="/block/{{d.ip}}?key={{key}}" class="block-btn">🚫</a><a href="/unblock/{{d.ip}}?key={{key}}" class="unblock-btn">✅</a></div>
{% endfor %}</div>
</body></html>"""

@app.route("/")
def home(): return render_template_string(HTML)

@app.route("/manifest.json")
def manifest():
    return {"name":"Moka.AI","short_name":"Moka.AI","start_url":"/","display":"standalone",
            "background_color":"#0f1117","theme_color":"#6d8cff","orientation":"portrait","lang":"ar","dir":"rtl"}

@app.route("/sw.js")
def sw():
    return "const CACHE='moka-v5';self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',e=>e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));", 200, {'Content-Type': 'application/javascript'}

@app.route("/admin")
def admin():
    if request.args.get("key") != ADMIN_KEY: return "🔒 ممنوع.", 403
    return render_template_string(ADMIN_HTML, s=load_stats(), key=ADMIN_KEY)

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
        return jsonify({"reply": ask_ai(d.get("message",""), d.get("session_id","default"), d.get("mode","general"))})
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

@app.post("/edit_image")
def edit_image():
    try:
        d = request.get_json(silent=True) or {}
        img_b64 = d.get("image", "")
        action = d.get("action", "describe")
        if not img_b64: return jsonify({"reply": "لم يتم استلام صورة.", "image": None})
        img_data = b64.b64decode(img_b64)
        img = Image.open(io.BytesIO(img_data))
        result_img = None; msg = ""
        if action == "brighten":
            result_img = ImageEnhance.Brightness(img).enhance(1.5); msg = "✅ تم تحسين الإضاءة"
        elif action == "contrast":
            result_img = ImageEnhance.Contrast(img).enhance(1.5); msg = "✅ تم زيادة التباين"
        elif action == "blur":
            result_img = img.filter(ImageFilter.GaussianBlur(radius=5)); msg = "✅ تم التمويه"
        elif action == "sharpen":
            result_img = img.filter(ImageFilter.SHARPEN); msg = "✅ تم التوضيح"
        elif action == "grayscale":
            result_img = img.convert("L"); msg = "✅ أبيض وأسود"
        elif action == "rotate":
            result_img = img.rotate(90, expand=True); msg = "✅ تم التدوير"
        elif action == "enhance":
            result_img = ImageEnhance.Color(img).enhance(1.5); msg = "✅ تم تحسين الألوان"
        else:
            return jsonify({"reply": "📸 اختر تعديلاً من الأزرار.", "image": None})
        if result_img:
            if result_img.mode == "L": result_img = result_img.convert("RGB")
            buffered = io.BytesIO()
            result_img.save(buffered, format="JPEG", quality=90)
            return jsonify({"reply": msg, "image": b64.b64encode(buffered.getvalue()).decode()})
        return jsonify({"reply": msg, "image": None})
    except Exception as e:
        return jsonify({"reply": f"⚠️ خطأ: {str(e)}", "image": None})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

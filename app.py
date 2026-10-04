# ============================================================
# Moka.AI - مساعد ذكي عربي متطور
# المطور: محمد كامل | الإصدار: 3.0
# ============================================================

from flask import Flask, request, jsonify, render_template_string
import os, json, urllib.request, urllib.error, datetime, io
import base64 as b64
from PIL import Image, ImageEnhance, ImageFilter

app = Flask(__name__)

# ==================== الإعدادات ====================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

ADMIN_KEY = "moka2026kamel"
BLOCKED_IPS = set()
STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")

# ==================== الإحصائيات ====================
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

# ==================== المعرفة ====================
CURRICULUM = """
معلومات المنهاج الجزائري 2026-2027:
- الابتدائي: الإنجليزية من السنة الثالثة. الرياضيات 5 ساعات.
- المتوسط: معامل الرياضيات 4 في الرابعة متوسط، العربية 5.
- الثانوي: جذع آداب (31 ساعة)، علوم (32 ساعة).
- شعبة الرياضيات: رياضيات معامل 8، فيزياء معامل 6.
- شهادة التعليم المتوسط (BEM): جميع المواد الأساسية.
"""

FORBIDDEN = ["جنس", "sex", "porn", "إباحي", "عاري", "شهوة", "زنى", "زنا", "خلاعة", "فاحشة"]

def is_forbidden(text):
    return any(w in text.lower() for w in FORBIDDEN)

# ==================== النماذج ====================
PROMPTS = {
    "general": "أنت Moka.AI، مساعد ذكي عربي من تطوير محمد كامل. أجب بالعربية الفصحى المبسطة. لا تستخدم LaTeX.\n\n" + CURRICULUM,
    "math": """أنت Moka.AI، خبير رياضيات (جبر، هندسة، تفاضل، تكامل، نهايات).
قواعد: اشرح كل خطوة بوضوح. اكتب المعادلات بشكل عادي (x² + 2x + 1 = 0).

التفاضل: مشتقة xⁿ = n·x^(n-1)، sin(x)=cos(x)، cos(x)=-sin(x)، e^x=e^x، ln(x)=1/x.
قواعد: (uv)' = u'v + uv'، (u/v)' = (u'v - uv')/v²، (f(g(x)))' = f'(g(x))·g'(x).

التكامل: ∫xⁿ dx = x^(n+1)/(n+1) + C، ∫1/x dx = ln|x| + C، ∫e^x dx = e^x + C، ∫sin(x) dx = -cos(x) + C.
التكامل بالتجزئة: ∫u dv = uv - ∫v du.

عند رسم دالة: اكتب المعادلة، القمة، الجذور، كود Python (matplotlib).

""" + CURRICULUM,
    "code": "أنت Moka.AI، خبير برمجة. اكتب الكود منسقاً واشرحه بجمل بسيطة.",
    "religion": """أنت Moka.AI، مساعد في العلوم الإسلامية.
مصادرك: القرآن، صحيح البخاري ومسلم، كتب التفسير، المذاهب الأربعة.
قواعد: اذكر الآية بدقة، درجة الحديث، آراء المذاهب، وقل "الله أعلم" إذا لم تكن متأكداً.""",
    "edit": "أنت Moka.AI، خبير في تحرير الصور. المستخدم يرفع صوراً ويمكنه تطبيق تعديلات حقيقية عليها (إضاءة، تباين، ألوان، تمويه، توضيح، أبيض وأسود، تدوير).",
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
                data=json.dumps({"model": m, "messages": convs[key], "temperature": 0.7, "max_tokens": 2048}).encode(),
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json",
                         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
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
                    {"role": "user", "content": text}], "temperature": 0.5, "max_tokens": 1024}).encode(),
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json",
                         "User-Agent": "Mozilla/5.0"},
                method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())["choices"][0]["message"]["content"]
        except Exception:
            continue
    return "⚠️ تعذر التلخيص."
# الشعار: حرف M على شكل ابتسامة 😊
LOGO_SVG = '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
<defs>
<linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" style="stop-color:#4d6bfe"/>
<stop offset="100%" style="stop-color:#7c3aed"/>
</linearGradient>
</defs>
<circle cx="50" cy="50" r="48" fill="url(#logoGrad)"/>
<circle cx="50" cy="50" r="42" fill="none" stroke="white" stroke-width="1.5" opacity="0.3"/>
<circle cx="35" cy="42" r="4" fill="white"/>
<circle cx="65" cy="42" r="4" fill="white"/>
<path d="M 30 62 Q 50 80 70 62" stroke="white" stroke-width="5" fill="none" stroke-linecap="round"/>
<path d="M 35 30 L 45 45 L 50 38 L 55 45 L 65 30" stroke="white" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.6"/>
</svg>'''

HTML = """<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moka.AI</title><link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#4d6bfe">
<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js');}</script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0d0d0d;--sidebar:#171717;--input:#1e1e1e;--user:#2f2f2f;--bot:#1a1a1a;--text:#ececec;--border:#2a2a2a;--accent:#4d6bfe;--accent2:#7c3aed}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',Tahoma,sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden}

#login{position:fixed;inset:0;background:radial-gradient(circle at center,#1a1a2e 0%,#0d0d0d 70%);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:999;padding:20px}
#login.hide{display:none}
.logo-big{width:140px;height:140px;margin-bottom:25px;animation:float 3s ease-in-out infinite;filter:drop-shadow(0 10px 30px rgba(77,107,254,.5))}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}
.lt{font-size:42px;font-weight:700;margin-bottom:8px;background:linear-gradient(90deg,#4d6bfe,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.ls{color:#888;margin-bottom:35px;font-size:14px}
.lb{width:100%;max-width:360px;background:rgba(26,26,26,.85);border:1px solid #2a2a2a;border-radius:24px;padding:28px;backdrop-filter:blur(20px);box-shadow:0 20px 60px rgba(0,0,0,.5)}
.lb label{display:block;font-size:13px;color:#aaa;margin-bottom:10px}
.lb input{width:100%;padding:16px;border-radius:14px;border:1px solid #2a2a2a;background:#0d0d0d;color:#ececec;font-size:16px;outline:none;margin-bottom:18px;transition:border-color .3s}
.lb input:focus{border-color:var(--accent)}
.lb button{width:100%;padding:16px;border-radius:14px;border:none;background:linear-gradient(90deg,#4d6bfe,#7c3aed);color:white;font-size:16px;font-weight:600;cursor:pointer}
.lb button:active{transform:scale(.98)}

#app{display:none;height:100vh;flex-direction:column}
#app.on{display:flex}
.ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:998}
.ov.on{display:block}
.sb{position:fixed;top:0;right:-320px;width:300px;height:100%;background:#171717;border-left:1px solid #2a2a2a;z-index:999;transition:right .3s;padding:24px;display:flex;flex-direction:column;gap:10px;overflow-y:auto}
.sb.on{right:0}
.sb h2{font-size:14px;color:#666;margin-bottom:10px;letter-spacing:1px}
.avatar{width:90px;height:90px;border-radius:50%;background:linear-gradient(135deg,#4d6bfe,#7c3aed);display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:bold;color:white;margin:0 auto 12px;box-shadow:0 0 30px rgba(77,107,254,.4)}
.username{text-align:center;font-size:17px;font-weight:600;margin-bottom:25px}
.mb{padding:14px 16px;border-radius:14px;border:1px solid #2a2a2a;background:#1e1e1e;color:#ececec;cursor:pointer;text-align:right;font-size:14px;display:flex;align-items:center;gap:10px;transition:all .2s}
.mb:hover{background:#252525}
.mb.on{border-color:var(--accent);background:linear-gradient(90deg,rgba(77,107,254,.15),rgba(124,58,237,.15))}
.lo{margin-top:auto;padding:14px;border-radius:14px;border:1px solid #dc2626;background:transparent;color:#dc2626;cursor:pointer;font-size:14px}
.dl{padding:14px;border-radius:14px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer;font-size:14px;margin-top:10px}

.hd{padding:14px 18px;border-bottom:1px solid #1a1a1a;background:#0d0d0d;display:flex;align-items:center;justify-content:space-between}
.tg{display:flex;align-items:center;gap:12px;margin:0 auto}
.hl-logo{width:40px;height:40px}
h1{font-size:20px;font-weight:700;background:linear-gradient(90deg,#4d6bfe,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hb{background:transparent;border:1px solid #2a2a2a;color:#aaa;padding:10px 12px;border-radius:12px;cursor:pointer;font-size:16px;transition:all .2s}
.hb:hover{background:#1a1a1a}

#ch{flex:1;overflow-y:auto;padding:24px 18px;display:flex;flex-direction:column;gap:20px}
#ch::-webkit-scrollbar{width:6px}
#ch::-webkit-scrollbar-thumb{background:#333;border-radius:3px}
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:18px;text-align:center;padding:20px}
.welcome img{width:100px;height:100px;opacity:.95}
.welcome h2{font-size:24px;font-weight:600;background:linear-gradient(90deg,#4d6bfe,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.welcome p{color:#666;font-size:14px;max-width:280px;line-height:1.6}
.mw{display:flex;max-width:90%;animation:si .35s ease}
.mw.u{align-self:flex-end}
.mw.b{align-self:flex-start}
@keyframes si{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.m{padding:16px 20px;border-radius:22px;line-height:1.8;white-space:pre-wrap;word-wrap:break-word;font-size:15px}
.u .m{background:var(--user);border-bottom-left-radius:6px}
.b .m{background:var(--bot);border:1px solid #2a2a2a;border-bottom-right-radius:6px}
.m img{max-width:240px;border-radius:14px;margin-top:10px;display:block;border:1px solid #2a2a2a}
.tp{display:inline-flex;gap:6px;padding:16px 20px;background:var(--bot);border:1px solid #2a2a2a;border-radius:22px}
.tp span{width:8px;height:8px;background:#4d6bfe;border-radius:50%;animation:bo 1.4s infinite}
.tp span:nth-child(2){animation-delay:.2s}
.tp span:nth-child(3){animation-delay:.4s}
@keyframes bo{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-8px);opacity:1}}

.ia{padding:16px 18px 20px;background:#0d0d0d;display:flex;gap:10px;align-items:flex-end;border-top:1px solid #1a1a1a}
.iw{flex:1}
textarea{width:100%;padding:16px 20px;border-radius:24px;border:1px solid #2a2a2a;background:var(--input);color:var(--text);font-size:16px;outline:none;font-family:inherit;resize:none;max-height:120px;line-height:1.5;transition:border-color .3s}
textarea:focus{border-color:var(--accent)}
button.sd{width:52px;height:52px;border-radius:50%;border:none;background:linear-gradient(135deg,#4d6bfe,#7c3aed);color:white;font-size:20px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all .2s;box-shadow:0 4px 15px rgba(77,107,254,.3)}
button.sd:hover{transform:scale(1.05)}
button.sd:disabled{opacity:.4}
button.file{background:#1e1e1e;border:1px solid #2a2a2a;color:#aaa;box-shadow:none}
button.file:hover{background:#252525;color:var(--accent)}
.vc{text-align:center;padding:8px;font-size:11px;color:#444;background:#0d0d0d}

.mo{display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:1000;justify-content:center;align-items:center;padding:20px}
.mo.on{display:flex}
.md{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:24px;padding:24px;width:100%;max-width:500px;display:flex;flex-direction:column;gap:16px}
.md h2{font-size:18px}
.md textarea{height:220px;padding:16px;border-radius:14px;border:1px solid #2a2a2a;background:#0d0d0d;color:#ececec;font-family:inherit;resize:none;outline:none;line-height:1.6}
.mbtns{display:flex;gap:10px;justify-content:flex-end}
.mbtns button{padding:12px 24px;border-radius:12px;border:none;cursor:pointer;font-size:14px;font-weight:600}
.mbtns .p{background:linear-gradient(90deg,#4d6bfe,#7c3aed);color:white}
.mbtns .s{background:#2a2a2a;color:#ccc}

.tools{display:flex;gap:6px;padding:8px 18px;background:#0d0d0d;overflow-x:auto;border-top:1px solid #1a1a1a}
.tools::-webkit-scrollbar{height:0}
.tool{padding:8px 14px;border-radius:20px;border:1px solid #2a2a2a;background:#1e1e1e;color:#aaa;cursor:pointer;font-size:12px;white-space:nowrap;transition:all .2s}
.tool:hover{border-color:var(--accent);color:var(--accent)}
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
<button class="mb on" data-m="general" onclick="sw('general')">🧠 <span>النسخة العامة</span></button>
<button class="mb" data-m="math" onclick="sw('math')">📐 <span>الرياضيات</span></button>
<button class="mb" data-m="code" onclick="sw('code')">💻 <span>البرمجة</span></button>
<button class="mb" data-m="religion" onclick="sw('religion')">🕌 <span>العلوم الإسلامية</span></button>
<button class="mb" data-m="edit" onclick="sw('edit')">✏️ <span>تحرير الصور</span></button>
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
<div style="width:100px;height:100px">__LOGO_SVG__</div>
<h2>كيف يمكنني مساعدتك؟</h2>
<p>اسألني أي شيء، أو ارفع صورة لتعديلها.</p>
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
<div class="vc">Moka.AI © 2026 | عدد الزوار: <span id="vc">...</span></div>
</div>

<div class="mo" id="mo"><div class="md"><h2>📝 تلخيص درس</h2><textarea id="st" placeholder="الصق نص الدرس هنا..."></textarea>
<div class="mbtns"><button class="s" onclick="closeM()">إلغاء</button><button class="p" onclick="doSum()">لخّص</button></div></div></div>

<script>
let mode="general";
let currentAction="describe";
const ch=document.getElementById("ch"),i=document.getElementById("i"),f=document.getElementById("f"),s=document.getElementById("s");
const sid="u_"+Math.random().toString(36).substring(2,10);
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"visit"})});
function autoResize(t){t.style.height="auto";t.style.height=Math.min(t.scrollHeight,120)+"px"}
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
ch.innerHTML='<div class="welcome"><div style="width:100px;height:100px">__LOGO_SVG__</div><h2>'+names[m]+'</h2><p>كيف يمكنني مساعدتك؟</p></div>';
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
      const r=await fetch("/analyze_image",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({image:base64,action:currentAction})});
      const d=await r.json();ty.remove();
      if(d.image){
        const w2=document.createElement("div");w2.className="mw b";const m2=document.createElement("div");m2.className="m";
        m2.textContent=d.reply;
        const img2=document.createElement("img");img2.src="data:image/jpeg;base64,"+d.image;m2.appendChild(img2);
        w2.appendChild(m2);ch.appendChild(w2);ch.scrollTop=ch.scrollHeight;
      } else { add(d.reply||"تم","b"); }
      i.value="";
    }catch(err){ty.remove();add("تعذر الاتصال","b")}
    input.value="";
  };
  reader.readAsDataURL(file);
}
function openM(){document.getElementById("mo").classList.add("on")}
function closeM(){document.getElementById("mo").classList.remove("on")}
async function doSum(){const t=document.getElementById("st").value.trim();if(!t){alert("الصق النص");return}closeM();document.getElementById("st").value="";
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"summary"})});
add("📝 لخّص: "+t.substring(0,80)+"...","u");const ty=typ();
try{const r=await fetch("/summarize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:t})});
const d=await r.json();ty.remove();add(d.summary||"خطأ","b")}catch(e){ty.remove();add("تعذر","b")}}
function downloadChat(){
  const name=localStorage.getItem("mu")||"مستخدم";
  let text="محادثة Moka.AI - "+name+"\\n"+new Date().toLocaleString("ar-DZ")+"\\n=============================\\n\\n";
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
body{background:#0d0d0d;color:#ececec;font-family:Tahoma,sans-serif;padding:20px}
h1{text-align:center;margin-bottom:20px;background:linear-gradient(90deg,#4d6bfe,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:15px;margin-bottom:20px}
.card{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:20px;text-align:center}
.card .num{font-size:32px;font-weight:bold;color:#4d6bfe;margin-bottom:5px}
.card .lbl{font-size:13px;color:#888}
.box{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:20px;margin-bottom:20px}
.box h2{font-size:16px;margin-bottom:15px;color:#4d6bfe}
.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #222;font-size:13px;gap:10px;align-items:center;flex-wrap:wrap}
.mode-bar{display:flex;justify-content:space-between;padding:10px;background:#0d0d0d;border-radius:8px;margin-bottom:8px}
.msg-item{background:#0d0d0d;border-radius:8px;padding:12px;margin-bottom:10px;border-right:3px solid #4d6bfe}
.msg-item .meta{color:#888;font-size:11px;margin-bottom:8px;display:flex;gap:10px;flex-wrap:wrap}
.msg-item .text{color:#ececec;font-size:14px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word}
.block-btn{background:#dc2626;color:white;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;display:inline-block}
.unblock-btn{background:#4d6bfe;color:white;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;display:inline-block;margin-right:5px}
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
{% endfor %}{% else %}<p style="color:#888;text-align:center;">لا توجد رسائل بعد.</p>{% endif %}
</div>
<div class="box"><h2>🕐 آخر 20 زيارة</h2>
{% for r in s.recent[-20:]|reverse %}
<div class="row"><span>👤 {{r.name}}</span><span style="color:#888">📱 {{r.device}}</span><span style="color:#666">{{r.ip}}</span><span style="color:#666">{{r.time}}</span>
<a href="/block/{{r.ip}}?key={{key}}" class="block-btn">🚫</a><a href="/unblock/{{r.ip}}?key={{key}}" class="unblock-btn">✅</a></div>
{% endfor %}</div>
<div class="box"><h2>📱 آخر 20 جهاز</h2>
{% for d in s.devices[-20:]|reverse %}
<div class="row"><span>📱 {{d.device}}</span><span style="color:#888">🌐 {{d.browser}}</span><span style="color:#666">{{d.ip}}</span><span style="color:#666">{{d.time}}</span>
<a href="/block/{{d.ip}}?key={{key}}" class="block-btn">🚫</a><a href="/unblock/{{d.ip}}?key={{key}}" class="unblock-btn">✅</a></div>
{% endfor %}</div>
</body></html>"""

@app.route("/")
def home(): return render_template_string(HTML)

@app.route("/manifest.json")
def manifest():
    return {"name":"Moka.AI","short_name":"Moka.AI","start_url":"/","display":"standalone",
            "background_color":"#0d0d0d","theme_color":"#4d6bfe","orientation":"portrait","lang":"ar","dir":"rtl"}

@app.route("/sw.js")
def sw():
    return "const CACHE='moka-v3';self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',e=>e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));", 200, {'Content-Type': 'application/javascript'}

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

@app.post("/analyze_image")
def analyze_image():
    try:
        d = request.get_json(silent=True) or {}
        img_b64 = d.get("image", "")
        action = d.get("action", "describe")
        if not img_b64: return jsonify({"reply": "لم يتم استلام صورة.", "image": None})
        img_data = b64.b64decode(img_b64)
        img = Image.open(io.BytesIO(img_data))
        result_img = None; msg = ""
        if action == "brighten":
            result_img = ImageEnhance.Brightness(img).enhance(1.5)
            msg = "✅ تم تحسين الإضاءة (+50%)"
        elif action == "contrast":
            result_img = ImageEnhance.Contrast(img).enhance(1.5)
            msg = "✅ تم زيادة التباين (+50%)"
        elif action == "blur":
            result_img = img.filter(ImageFilter.GaussianBlur(radius=5))
            msg = "✅ تم تطبيق التمويه"
        elif action == "sharpen":
            result_img = img.filter(ImageFilter.SHARPEN)
            msg = "✅ تم توضيح الصورة"
        elif action == "grayscale":
            result_img = img.convert("L")
            msg = "✅ تم التحويل إلى أبيض وأسود"
        elif action == "rotate":
            result_img = img.rotate(90, expand=True)
            msg = "✅ تم التدوير 90°"
        elif action == "enhance":
            result_img = ImageEnhance.Color(img).enhance(1.5)
            msg = "✅ تم تحسين الألوان (+50%)"
        else:
            return jsonify({"reply": "📸 اختر تعديلاً من الأزرار أدناه ثم ارفع صورة.", "image": None})
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
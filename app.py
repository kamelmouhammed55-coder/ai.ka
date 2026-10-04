from flask import Flask, request, jsonify, render_template_string
import os, json, urllib.request, datetime

app = Flask(__name__)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]

# ====== مفتاح لوحة التحكم السرية ======
ADMIN_KEY = "moka2026kamel"  # غيّره إلى أي كلمة سر تريدها

STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")

def load_stats():
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"visitors": 0, "logins": 0, "messages": 0, "summaries": 0,
                "modes": {"general": 0, "math": 0, "code": 0, "religion": 0},
                "recent": []}

def save_stats(s):
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

CURRICULUM = """
معلومات المنهاج الجزائري 2026-2027:
- الابتدائي: الإنجليزية من السنة الثالثة. الرياضيات 5 ساعات.
- المتوسط: معامل الرياضيات 4 في الرابعة متوسط، العربية 5.
- الثانوي: جذع آداب (31 ساعة)، علوم (32 ساعة).
- شعبة الرياضيات (3 ثانوي): رياضيات معامل 8، فيزياء معامل 6.
"""

PROMPTS = {
    "general": "أنت Moka.AI، مساعد ذكي عربي من تطوير محمد كامل. أجب بالعربية البسيطة. لا تستخدم LaTeX. لا تقل أنك GPT.\n\n" + CURRICULUM,
    "math": "أنت Moka.AI، خبير رياضيات. اشرح خطوة بخطوة بلغة بسيطة. لا تستخدم LaTeX.\n\n" + CURRICULUM,
    "code": "أنت Moka.AI، خبير برمجة. اكتب واشرح الأكواد بوضوح.",
    "religion": "أنت Moka.AI، مساعد في العلوم الإسلامية. أجب بالقرآن والسنة. اذكر الأدلة.",
}

convs = {}

def ask_ai(msg, sid, mode):
    if not GROQ_API_KEY: return "⚠️ مفتاح API غير موجود."
    key = f"{sid}_{mode}"
    if key not in convs:
        convs[key] = [{"role": "system", "content": PROMPTS.get(mode, PROMPTS["general"])}]
    convs[key].append({"role": "user", "content": msg})
    if len(convs[key]) > 21:
        convs[key] = [convs[key][0]] + convs[key][-20:]
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
        except Exception:
            continue
    return "⚠️ فشل الاتصال."

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

HTML = """<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moka.AI</title><link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#10a37f">
<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js');}</script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d0d0d;color:#ececec;font-family:Tahoma,sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden}
#login{position:fixed;inset:0;background:linear-gradient(135deg,#0d0d0d,#1a1a2e,#0d0d0d);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:999;padding:20px}
#login.hide{display:none}
.lg{width:100px;height:100px;background:linear-gradient(135deg,#10a37f,#7c3aed);border-radius:24px;display:flex;align-items:center;justify-content:center;font-size:50px;font-weight:bold;color:white;margin-bottom:20px;box-shadow:0 0 30px rgba(16,163,127,.4)}
.lt{font-size:34px;font-weight:bold;margin-bottom:8px;background:linear-gradient(90deg,#10a37f,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.ls{color:#888;margin-bottom:30px;font-size:14px}
.lb{width:100%;max-width:340px;background:#1a1a1a;border:1px solid #333;border-radius:20px;padding:24px}
.lb label{display:block;font-size:13px;color:#aaa;margin-bottom:8px}
.lb input{width:100%;padding:14px;border-radius:12px;border:1px solid #333;background:#0d0d0d;color:#ececec;font-size:16px;outline:none;margin-bottom:16px}
.lb input:focus{border-color:#10a37f}
.lb button{width:100%;padding:14px;border-radius:12px;border:none;background:linear-gradient(90deg,#10a37f,#7c3aed);color:white;font-size:16px;font-weight:bold;cursor:pointer}
#app{display:none;height:100vh;flex-direction:column}
#app.on{display:flex}
.ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:998}
.ov.on{display:block}
.sb{position:fixed;top:0;right:-300px;width:280px;height:100%;background:#171717;border-left:1px solid #333;z-index:999;transition:right .3s;padding:20px;display:flex;flex-direction:column;gap:10px}
.sb.on{right:0}
.sb h2{font-size:16px;color:#aaa;margin-bottom:10px}
.mb{padding:14px;border-radius:12px;border:1px solid #333;background:#1e1e1e;color:#ececec;cursor:pointer;text-align:right;font-size:14px}
.mb.on{border-color:#10a37f;background:rgba(16,163,127,.1)}
.lo{margin-top:auto;padding:14px;border-radius:12px;border:1px solid #dc2626;background:transparent;color:#dc2626;cursor:pointer}
.hd{padding:14px;border-bottom:1px solid #333;background:#171717;display:flex;align-items:center;justify-content:space-between}
.tg{display:flex;align-items:center;gap:10px;margin:0 auto}
.hl{width:32px;height:32px;background:linear-gradient(135deg,#10a37f,#7c3aed);border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:bold;color:white}
h1{font-size:18px;background:linear-gradient(90deg,#10a37f,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hb{background:transparent;border:1px solid #333;color:#aaa;padding:8px 10px;border-radius:8px;cursor:pointer;font-size:14px}
#ch{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:16px}
.mw{display:flex;max-width:88%;animation:si .3s}
.mw.u{align-self:flex-end}
.mw.b{align-self:flex-start}
@keyframes si{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.m{padding:14px 18px;border-radius:18px;line-height:1.7;white-space:pre-wrap;word-wrap:break-word;font-size:15px}
.u .m{background:#2f2f2f;border-bottom-left-radius:6px}
.b .m{background:#1a1a1a;border:1px solid #333;border-bottom-right-radius:6px}
.tp{display:inline-flex;gap:5px;padding:14px 18px;background:#1a1a1a;border:1px solid #333;border-radius:18px}
.tp span{width:7px;height:7px;background:#888;border-radius:50%;animation:bo 1.2s infinite}
.tp span:nth-child(2){animation-delay:.2s}
.tp span:nth-child(3){animation-delay:.4s}
@keyframes bo{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
.ia{padding:16px;background:#0d0d0d;display:flex;gap:10px;border-top:1px solid #333;align-items:center}
.iw{flex:1}
input{width:100%;padding:16px 20px;border-radius:28px;border:1px solid #333;background:#1e1e1e;color:#ececec;font-size:16px;outline:none}
input:focus{border-color:#10a37f}
button.sd{width:52px;height:52px;border-radius:50%;border:none;background:#10a37f;color:white;font-size:20px;cursor:pointer;flex-shrink:0}
button.sd:disabled{opacity:.4}
.vc{text-align:center;padding:8px;font-size:12px;color:#666;border-top:1px solid #333;background:#171717}
.mo{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;justify-content:center;align-items:center}
.mo.on{display:flex}
.md{background:#1a1a1a;border:1px solid #333;border-radius:16px;padding:20px;width:90%;max-width:500px;display:flex;flex-direction:column;gap:12px}
.md textarea{width:100%;height:200px;padding:14px;border-radius:12px;border:1px solid #333;background:#0d0d0d;color:#ececec;font-family:inherit;resize:vertical;outline:none}
.mbtns{display:flex;gap:10px;justify-content:flex-end}
.mbtns button{padding:10px 20px;border-radius:10px;border:none;cursor:pointer}
.mbtns .p{background:#10a37f;color:white}
.mbtns .s{background:#333;color:#ccc}
</style></head><body>
<div id="login"><div class="lg">M</div><div class="lt">Moka.AI</div><div class="ls">مساعدك الذكي من تطوير محمد كامل</div>
<div class="lb"><label>👤 اسمك</label><input id="un" placeholder="اكتب اسمك..."><button onclick="login()">🚀 دخول</button></div></div>
<div class="ov" id="ov" onclick="closeS()"></div>
<div class="sb" id="sb"><h2>📋 اختر النسخة</h2>
<button class="mb on" data-m="general" onclick="sw('general')">🧠 النسخة العامة</button>
<button class="mb" data-m="math" onclick="sw('math')">📐 نسخة الرياضيات</button>
<button class="mb" data-m="code" onclick="sw('code')">💻 نسخة البرمجة</button>
<button class="mb" data-m="religion" onclick="sw('religion')">🕌 نسخة دينية</button>
<button class="lo" onclick="out()">🚪 تسجيل الخروج</button></div>
<div id="app"><div class="hd"><button class="hb" onclick="openS()">☰</button>
<div class="tg"><div class="hl">M</div><h1>Moka.AI</h1></div><div style="width:50px"></div></div>
<div id="ch"><div class="mw b"><div class="m" id="wm">👋 مرحباً!</div></div></div>
<form class="ia" id="f"><div class="iw"><input id="i" placeholder="اسأل Moka.AI..." autocomplete="off"></div><button class="sd" id="s">➤</button></form>
<div class="vc">👁️ عدد الزوار: <span id="vc">...</span></div></div>
<div class="mo" id="mo"><div class="md"><h2>📝 تلخيص درس</h2><textarea id="st" placeholder="الصق النص..."></textarea>
<div class="mbtns"><button class="s" onclick="closeM()">إلغاء</button><button class="p" onclick="doSum()">📝 لخّص</button></div></div></div>
<script>
let mode="general";
const ch=document.getElementById("ch"),i=document.getElementById("i"),f=document.getElementById("f"),s=document.getElementById("s");
const sid="u_"+Math.random().toString(36).substring(2,10);
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"visit"})});
function login(){const n=document.getElementById("un").value.trim();if(!n){alert("اكتب اسمك");return}
localStorage.setItem("mu",n);show(n);
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"login",name:n})});}
function show(n){document.getElementById("login").classList.add("hide");document.getElementById("app").classList.add("on");document.getElementById("wm").innerHTML="👋 مرحباً <b>"+n+"</b>! أنا Moka.AI. اختر النسخة من ☰"}
function out(){if(!confirm("تسجيل الخروج؟"))return;localStorage.removeItem("mu");location.reload()}
function openS(){document.getElementById("sb").classList.add("on");document.getElementById("ov").classList.add("on")}
function closeS(){document.getElementById("sb").classList.remove("on");document.getElementById("ov").classList.remove("on")}
function sw(m){mode=m;document.querySelectorAll(".mb").forEach(b=>b.classList.toggle("on",b.dataset.m===m));
const names={general:"🧠 العامة",math:"📐 الرياضيات",code:"💻 البرمجة",religion:"🕌 الدينية"};
ch.innerHTML='<div class="mw b"><div class="m">✅ تم التبديل إلى '+names[m]+'</div></div>';closeS()}
window.onload=()=>{const n=localStorage.getItem("mu");if(n){document.getElementById("un").value=n;show(n)}}
let v=localStorage.getItem("mv");v=v?parseInt(v)+1:1;localStorage.setItem("mv",v);document.getElementById("vc").textContent=v;
function add(t,c){const w=document.createElement("div");w.className="mw "+c;const m=document.createElement("div");m.className="m";m.textContent=t;w.appendChild(m);ch.appendChild(w);ch.scrollTop=ch.scrollHeight}
function typ(){const w=document.createElement("div");w.className="mw b";const t=document.createElement("div");t.className="tp";t.innerHTML="<span></span><span></span><span></span>";w.appendChild(t);ch.appendChild(w);ch.scrollTop=ch.scrollHeight;return w}
f.onsubmit=async(e)=>{e.preventDefault();const t=i.value.trim();if(!t)return;add(t,"u");i.value="";s.disabled=true;const ty=typ();
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"message",mode:mode})});
try{const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:t,session_id:sid,mode:mode})});
const d=await r.json();ty.remove();add(d.reply||"خطأ","b")}catch(e){ty.remove();add("تعذر الاتصال","b")}finally{s.disabled=false;i.focus()}};
function openM(){document.getElementById("mo").classList.add("on")}
function closeM(){document.getElementById("mo").classList.remove("on")}
async function doSum(){const t=document.getElementById("st").value.trim();if(!t){alert("الصق النص");return}closeM();document.getElementById("st").value="";
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"summary"})});
add("📝 لخّص: "+t.substring(0,80)+"...","u");const ty=typ();
try{const r=await fetch("/summarize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:t})});
const d=await r.json();ty.remove();add(d.summary||"خطأ","b")}catch(e){ty.remove();add("تعذر","b")}}
</script></body></html>"""

ADMIN_HTML = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>لوحة التحكم - Moka.AI</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d0d0d;color:#ececec;font-family:Tahoma,sans-serif;padding:20px}
h1{text-align:center;margin-bottom:20px;background:linear-gradient(90deg,#10a37f,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:20px}
.card{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:20px;text-align:center}
.card .num{font-size:32px;font-weight:bold;color:#10a37f;margin-bottom:5px}
.card .lbl{font-size:13px;color:#888}
.box{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:20px;margin-bottom:20px}
.box h2{font-size:16px;margin-bottom:15px;color:#10a37f}
.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #222;font-size:14px}
.row:last-child{border:0}
.mode-bar{display:flex;justify-content:space-between;padding:10px;background:#0d0d0d;border-radius:8px;margin-bottom:8px}
</style></head><body>
<h1>📊 لوحة تحكم Moka.AI</h1>
<div class="grid">
<div class="card"><div class="num">{{s.visitors}}</div><div class="lbl">👁️ الزوار الكلي</div></div>
<div class="card"><div class="num">{{s.logins}}</div><div class="lbl">🔑 تسجيلات الدخول</div></div>
<div class="card"><div class="num">{{s.messages}}</div><div class="lbl">💬 الرسائل المُرسلة</div></div>
<div class="card"><div class="num">{{s.summaries}}</div><div class="lbl">📝 عمليات التلخيص</div></div>
</div>
<div class="box"><h2>📈 استخدام النسخ</h2>
<div class="mode-bar"><span>🧠 عامة</span><b>{{s.modes.general}}</b></div>
<div class="mode-bar"><span>📐 رياضيات</span><b>{{s.modes.math}}</b></div>
<div class="mode-bar"><span>💻 برمجة</span><b>{{s.modes.code}}</b></div>
<div class="mode-bar"><span>🕌 دينية</span><b>{{s.modes.religion}}</b></div>
</div>
<div class="box"><h2>🕐 آخر 20 زيارة</h2>
{% for r in s.recent[-20:]|reverse %}
<div class="row"><span>{{r.name}}</span><span style="color:#666">{{r.time}}</span></div>
{% endfor %}
</div>
</body></html>"""

@app.route("/")
def home(): return render_template_string(HTML)

@app.route("/manifest.json")
def manifest():
    return {
        "name": "Moka.AI - مساعدك الذكي", "short_name": "Moka.AI",
        "start_url": "/", "display": "standalone",
        "background_color": "#0d0d0d", "theme_color": "#10a37f",
        "orientation": "portrait", "lang": "ar", "dir": "rtl",
        "icons": [{"src": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImciIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMTAwJSIgeTI9IjEwMCUiPjxzdG9wIG9mZnNldD0iMCUiIHN0eWxlPSJzdG9wLWNvbG9yOiMxMGEzN2Y7c3RvcC1vcGFjaXR5OjEiLz48c3RvcCBvZmZzZXQ9IjEwMCUiIHN0eWxlPSJzdG9wLWNvbG9yOiM3YzNhZWQ7c3RvcC1vcGFjaXR5OjEiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48cG9seWdvbiBwb2ludHM9IjUwLDUgOTAsMjcuNSA5MCw3Mi41IDUwLDk1IDEwLDcyLjUgMTAsMjcuNSIgZmlsbD0idXJsKCNnKSIvPjx0ZXh0IHg9IjUwIiB5PSI2NSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjQ1IiBmb250LXdlaWdodD0iYm9sZCIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPk08L3RleHQ+PC9zdmc+", "sizes": "192x192", "type": "image/svg+xml", "purpose": "any maskable"}]
    }

@app.route("/sw.js")
def sw():
    return """
const CACHE='moka-v1';
self.addEventListener('install',e=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('fetch',e=>e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));
""", 200, {'Content-Type': 'application/javascript'}

@app.route("/admin")
def admin():
    if request.args.get("key") != ADMIN_KEY:
        return "🔒 ممنوع. استخدم المفتاح السري.", 403
    s = load_stats()
    return render_template_string(ADMIN_HTML, s=s)

@app.route("/track", methods=["POST"])
def track():
    try:
        d = request.get_json(silent=True) or {}
        t = d.get("type", "")
        s = load_stats()
        if t == "visit":
            s["visitors"] += 1
        elif t == "login":
            s["logins"] += 1
            s["recent"].append({"name": d.get("name", "?"), "time": datetime.datetime.now().strftime("%m/%d %H:%M")})
            s["recent"] = s["recent"][-50:]
        elif t == "message":
            s["messages"] += 1
            m = d.get("mode", "general")
            if m in s["modes"]: s["modes"][m] += 1
        elif t == "summary":
            s["summaries"] += 1
        save_stats(s)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "err": str(e)}), 500

@app.post("/chat")
def chat():
    try:
        d = request.get_json(silent=True) or {}
        return jsonify({"reply": ask_ai(d.get("message",""), d.get("session_id","default"), d.get("mode","general"))})
    except Exception as e: return jsonify({"reply":f"خطأ: {str(e)}"}),500

@app.post("/summarize")
def summ():
    try:
        d = request.get_json(silent=True) or {}
        return jsonify({"summary": summarize(d.get("text",""))})
    except Exception as e: return jsonify({"summary":f"خطأ: {str(e)}"}),500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
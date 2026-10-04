from flask import Flask, request, jsonify, render_template_string
import os, json, urllib.request, urllib.error, datetime

app = Flask(__name__)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

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

CURRICULUM = """
معلومات المنهاج الجزائري 2026-2027:
- الابتدائي: الإنجليزية من السنة الثالثة. الرياضيات 5 ساعات.
- المتوسط: معامل الرياضيات 4 في الرابعة متوسط، العربية 5.
- الثانوي: جذع آداب (31 ساعة)، علوم (32 ساعة).
- شعبة الرياضيات (3 ثانوي): رياضيات معامل 8، فيزياء معامل 6.
- شهادة التعليم المتوسط (BEM): تشمل العربية، الرياضيات، الفرنسية، الإنجليزية، العلوم، الفيزياء، التاريخ والجغرافيا، التربية الإسلامية، التربية المدنية.
"""

FORBIDDEN = ["جنس", "sex", "porn", "إباحي", "عاري", "شهوة", "زنى", "زنا", "خلاعة", "فاحشة"]

def is_forbidden(text):
    return any(w in text.lower() for w in FORBIDDEN)

PROMPTS = {
    "general": "أنت Moka.AI، مساعد ذكي عربي من تطوير محمد كامل. أجب بالعربية الفصحى المبسطة. لا تستخدم LaTeX. لا تقل أنك GPT أو OpenAI.\n\n" + CURRICULUM,
    "math": """أنت Moka.AI، خبير رياضيات. اشرح خطوة بخطوة بلغة بسيطة.
إذا طلب منك المستخدم رسم دالة، أجب:
1. اكتب المعادلة بوضوح.
2. اذكر القمة والجذور ونقاط التقاطع.
3. اكتب كود Python (matplotlib) لرسم الدالة.
4. اذكر رابط Desmos للرسم التفاعلي.

""" + CURRICULUM,
    "code": "أنت Moka.AI، خبير برمجة. اكتب الكود منسقاً واشرحه بجمل بسيطة.",
    "religion": """أنت Moka.AI، مساعد في العلوم الإسلامية.
مصادرك: القرآن الكريم، صحيح البخاري ومسلم، كتب التفسير المعتمدة، المذاهب الأربعة.
قواعد:
1. اذكر الآية من القرآن بدقة.
2. اذكر درجة الحديث ومصدره.
3. اذكر آراء المذاهب في الخلافات الفقهية.
4. إذا لم تكن متأكداً، قل "الله أعلم".
5. كن محترماً ومؤدباً.""",
    "edit": "أنت Moka.AI، خبير في تحرير الصور والنصوص. عندما تُرفع لك صورة، صفها بدقة واقترح تعديلات احترافية لتحسينها (الإضاءة، الألوان، الخلفية، الحدود). عندما يُرفع لك نص، حسّنه وأعد كتابته بأسلوب أفضل.",
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
            last_error = f"{e.code}"
            continue
        except Exception as e:
            last_error = str(e)
            continue
    return f"⚠️ فشل الاتصال. حاول مرة أخرى. ({last_error})"

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
.sb{position:fixed;top:0;right:-300px;width:280px;height:100%;background:#171717;border-left:1px solid #333;z-index:999;transition:right .3s;padding:20px;display:flex;flex-direction:column;gap:10px;overflow-y:auto}
.sb.on{right:0}
.sb h2{font-size:16px;color:#aaa;margin-bottom:10px}
.avatar{width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#10a37f,#7c3aed);display:flex;align-items:center;justify-content:center;font-size:36px;font-weight:bold;color:white;margin:0 auto 10px;box-shadow:0 0 20px rgba(16,163,127,.3)}
.username{text-align:center;font-size:16px;font-weight:bold;margin-bottom:20px;color:#10a37f}
.mb{padding:14px;border-radius:12px;border:1px solid #333;background:#1e1e1e;color:#ececec;cursor:pointer;text-align:right;font-size:14px}
.mb.on{border-color:#10a37f;background:rgba(16,163,127,.1)}
.lo{margin-top:auto;padding:14px;border-radius:12px;border:1px solid #dc2626;background:transparent;color:#dc2626;cursor:pointer}
.dl{padding:14px;border-radius:12px;border:1px solid #10a37f;background:transparent;color:#10a37f;cursor:pointer;margin-top:10px}
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
.m img{max-width:200px;border-radius:10px;margin-top:8px;display:block}
.tp{display:inline-flex;gap:5px;padding:14px 18px;background:#1a1a1a;border:1px solid #333;border-radius:18px}
.tp span{width:7px;height:7px;background:#888;border-radius:50%;animation:bo 1.2s infinite}
.tp span:nth-child(2){animation-delay:.2s}
.tp span:nth-child(3){animation-delay:.4s}
@keyframes bo{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
.ia{padding:16px;background:#0d0d0d;display:flex;gap:8px;border-top:1px solid #333;align-items:center}
.iw{flex:1}
input{width:100%;padding:16px 20px;border-radius:28px;border:1px solid #333;background:#1e1e1e;color:#ececec;font-size:16px;outline:none}
input:focus{border-color:#10a37f}
button.sd{width:52px;height:52px;border-radius:50%;border:none;background:#10a37f;color:white;font-size:20px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center}
button.sd:disabled{opacity:.4}
button.file{background:#7c3aed}
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
<div class="sb" id="sb">
<div class="avatar" id="avatar">M</div>
<div class="username" id="uname">مستخدم</div>
<h2>📋 اختر النسخة</h2>
<button class="mb on" data-m="general" onclick="sw('general')">🧠 النسخة العامة</button>
<button class="mb" data-m="math" onclick="sw('math')">📐 نسخة الرياضيات</button>
<button class="mb" data-m="code" onclick="sw('code')">💻 نسخة البرمجة</button>
<button class="mb" data-m="religion" onclick="sw('religion')">🕌 نسخة دينية</button>
<button class="mb" data-m="edit" onclick="sw('edit')">✏️ نسخة تعديلات</button>
<button class="dl" onclick="downloadChat()">💾 تنزيل المحادثة</button>
<button class="lo" onclick="out()">🚪 تسجيل الخروج</button></div>
<div id="app"><div class="hd"><button class="hb" onclick="openS()">☰</button>
<div class="tg"><div class="hl">M</div><h1>Moka.AI</h1></div><div style="width:50px"></div></div>
<div id="ch"><div class="mw b"><div class="m" id="wm">👋 مرحباً!</div></div></div>
<form class="ia" id="f">
<input type="file" id="fileInput" accept="image/*" style="display:none" onchange="handleFile(this)">
<button type="button" class="sd file" onclick="document.getElementById('fileInput').click()" title="رفع صورة">📎</button>
<div class="iw"><input id="i" placeholder="اسأل Moka.AI..." autocomplete="off"></div>
<button type="submit" class="sd" id="s">➤</button>
</form>
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
function show(n){document.getElementById("login").classList.add("hide");document.getElementById("app").classList.add("on");
document.getElementById("wm").innerHTML="👋 مرحباً <b>"+n+"</b>! أنا Moka.AI. اختر النسخة من ☰";
document.getElementById("avatar").textContent=n.charAt(0).toUpperCase();
document.getElementById("uname").textContent=n;}
function out(){if(!confirm("تسجيل الخروج؟"))return;localStorage.removeItem("mu");location.reload()}
function openS(){document.getElementById("sb").classList.add("on");document.getElementById("ov").classList.add("on")}
function closeS(){document.getElementById("sb").classList.remove("on");document.getElementById("ov").classList.remove("on")}
function sw(m){mode=m;document.querySelectorAll(".mb").forEach(b=>b.classList.toggle("on",b.dataset.m===m));
const names={general:"🧠 العامة",math:"📐 الرياضيات",code:"💻 البرمجة",religion:"🕌 الدينية",edit:"✏️ تعديلات"};
ch.innerHTML='<div class="mw b"><div class="m">✅ تم التبديل إلى '+names[m]+'</div></div>';closeS()}
window.onload=()=>{const n=localStorage.getItem("mu");if(n){document.getElementById("un").value=n;show(n)}}
let v=localStorage.getItem("mv");v=v?parseInt(v)+1:1;localStorage.setItem("mv",v);document.getElementById("vc").textContent=v;
function add(t,c){const w=document.createElement("div");w.className="mw "+c;const m=document.createElement("div");m.className="m";m.textContent=t;w.appendChild(m);ch.appendChild(w);ch.scrollTop=ch.scrollHeight}
function typ(){const w=document.createElement("div");w.className="mw b";const t=document.createElement("div");t.className="tp";t.innerHTML="<span></span><span></span><span></span>";w.appendChild(t);ch.appendChild(w);ch.scrollTop=ch.scrollHeight;return w}
f.onsubmit=async(e)=>{e.preventDefault();const t=i.value.trim();if(!t)return;add(t,"u");i.value="";s.disabled=true;const ty=typ();
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"message",mode:mode,text:t,name:localStorage.getItem("mu")||"?"})});
try{const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:t,session_id:sid,mode:mode})});
const d=await r.json();ty.remove();add(d.reply||"خطأ","b")}catch(e){ty.remove();add("تعذر الاتصال","b")}finally{s.disabled=false;i.focus()}};
async function handleFile(input){
  const file=input.files[0];
  if(!file)return;
  if(!file.type.startsWith("image/")){alert("الرجاء اختيار صورة");return;}
  if(file.size>5*1024*1024){alert("حجم الصورة كبير (الحد 5 ميغا)");return;}
  const reader=new FileReader();
  reader.onload=async function(e){
    const base64=e.target.result.split(",")[1];
    const w=document.createElement("div");w.className="mw u";const m=document.createElement("div");m.className="m";
    m.textContent="📎 "+file.name;const img=document.createElement("img");img.src=e.target.result;m.appendChild(img);
    w.appendChild(m);ch.appendChild(w);ch.scrollTop=ch.scrollHeight;
    const ty=typ();
    try{
      const r=await fetch("/analyze_image",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({image:base64,prompt:i.value.trim()||"صف هذه الصورة واقترح تعديلات"})});
      const d=await r.json();ty.remove();add(d.reply||"تعذر التحليل","b");i.value="";
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
    const isUser=m.classList.contains("u");
    const content=m.querySelector(".m");
    if(content){text+=(isUser?"👤 "+name:"🤖 Moka.AI")+":\\n"+content.textContent+"\\n\\n";}
  });
  const blob=new Blob([text],{type:"text/plain;charset=utf-8"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);
  a.download="MokaAI_"+name+"_"+Date.now()+".txt";a.click();
}
</script></body></html>"""
ADMIN_HTML = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>لوحة التحكم</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d0d0d;color:#ececec;font-family:Tahoma,sans-serif;padding:20px}
h1{text-align:center;margin-bottom:20px;background:linear-gradient(90deg,#10a37f,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:15px;margin-bottom:20px}
.card{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:20px;text-align:center}
.card .num{font-size:32px;font-weight:bold;color:#10a37f;margin-bottom:5px}
.card .lbl{font-size:13px;color:#888}
.box{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:20px;margin-bottom:20px}
.box h2{font-size:16px;margin-bottom:15px;color:#10a37f}
.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #222;font-size:13px;gap:10px;align-items:center;flex-wrap:wrap}
.mode-bar{display:flex;justify-content:space-between;padding:10px;background:#0d0d0d;border-radius:8px;margin-bottom:8px}
.msg-item{background:#0d0d0d;border-radius:8px;padding:12px;margin-bottom:10px;border-right:3px solid #10a37f}
.msg-item .meta{color:#888;font-size:11px;margin-bottom:8px;display:flex;gap:10px;flex-wrap:wrap}
.msg-item .text{color:#ececec;font-size:14px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word}
.block-btn{background:#dc2626;color:white;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;display:inline-block}
.unblock-btn{background:#10a37f;color:white;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;display:inline-block;margin-right:5px}
</style></head><body>
<h1>📊 لوحة تحكم Moka.AI</h1>
<div class="grid">
<div class="card"><div class="num">{{s.visitors}}</div><div class="lbl">👁️ الزوار</div></div>
<div class="card"><div class="num">{{s.logins}}</div><div class="lbl">🔑 تسجيلات</div></div>
<div class="card"><div class="num">{{s.messages}}</div><div class="lbl">💬 رسائل</div></div>
<div class="card"><div class="num">{{s.summaries}}</div><div class="lbl">📝 تلخيص</div></div>
</div>
<div class="box"><h2>📈 استخدام النسخ</h2>
<div class="mode-bar"><span>🧠 عامة</span><b>{{s.modes.general}}</b></div>
<div class="mode-bar"><span>📐 رياضيات</span><b>{{s.modes.math}}</b></div>
<div class="mode-bar"><span>💻 برمجة</span><b>{{s.modes.code}}</b></div>
<div class="mode-bar"><span>🕌 دينية</span><b>{{s.modes.religion}}</b></div>
<div class="mode-bar"><span>✏️ تعديلات</span><b>{{s.modes.edit}}</b></div>
</div>
<div class="box"><h2>💬 كل الرسائل (آخر 50)</h2>
{% if s.messages_log %}
{% for m in s.messages_log[-50:]|reverse %}
<div class="msg-item">
<div class="meta">
<span>👤 <b>{{m.name}}</b></span>
<span>📱 {{m.ip}}</span>
<span>🧠 {{m.mode}}</span>
<span>🕐 {{m.time}}</span>
</div>
<div class="text">💬 {{m.text}}</div>
</div>
{% endfor %}
{% else %}
<p style="color:#888;text-align:center;">لا توجد رسائل بعد.</p>
{% endif %}
</div>
<div class="box"><h2>🕐 آخر 20 زيارة</h2>
{% for r in s.recent[-20:]|reverse %}
<div class="row">
<span>👤 {{r.name}}</span>
<span style="color:#888">📱 {{r.device}}</span>
<span style="color:#666">{{r.ip}}</span>
<span style="color:#666">{{r.time}}</span>
<a href="/block/{{r.ip}}?key={{key}}" class="block-btn">🚫</a>
<a href="/unblock/{{r.ip}}?key={{key}}" class="unblock-btn">✅</a>
</div>
{% endfor %}
</div>
<div class="box"><h2>📱 آخر 20 جهاز</h2>
{% for d in s.devices[-20:]|reverse %}
<div class="row">
<span>📱 {{d.device}}</span>
<span style="color:#888">🌐 {{d.browser}}</span>
<span style="color:#666">{{d.ip}}</span>
<span style="color:#666">{{d.time}}</span>
<a href="/block/{{d.ip}}?key={{key}}" class="block-btn">🚫</a>
<a href="/unblock/{{d.ip}}?key={{key}}" class="unblock-btn">✅</a>
</div>
{% endfor %}
</div>
</body></html>"""

@app.route("/")
def home(): return render_template_string(HTML)

@app.route("/manifest.json")
def manifest():
    return {"name":"Moka.AI","short_name":"Moka.AI","start_url":"/","display":"standalone",
            "background_color":"#0d0d0d","theme_color":"#10a37f","orientation":"portrait","lang":"ar","dir":"rtl"}

@app.route("/sw.js")
def sw():
    return "const CACHE='moka-v1';self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',e=>e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));", 200, {'Content-Type': 'application/javascript'}

@app.route("/admin")
def admin():
    if request.args.get("key") != ADMIN_KEY:
        return "🔒 ممنوع.", 403
    s = load_stats()
    return render_template_string(ADMIN_HTML, s=s, key=ADMIN_KEY)

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
        if ip in BLOCKED_IPS:
            return jsonify({"ok": False, "blocked": True}), 403
        d = request.get_json(silent=True) or {}
        t = d.get("type", "")
        ua = request.headers.get("User-Agent", "?")
        s = load_stats()
        device = "غير معروف"; browser = "غير معروف"
        if "Android" in ua: device = "Android"
        elif "iPhone" in ua or "iPad" in ua: device = "iPhone/iPad"
        elif "Windows" in ua: device = "Windows
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
        if ip in BLOCKED_IPS:
            return jsonify({"reply": "🚫 تم حظرك."}), 403
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
        prompt = d.get("prompt", "صف هذه الصورة")
        if not img_b64:
            return jsonify({"reply": "لم يتم استلام صورة."})
        if not GROQ_API_KEY:
            return jsonify({"reply": "⚠️ مفتاح API غير موجود."})
        messages = [{"role": "user", "content": [
            {"type": "text", "text": prompt + "\n\nأجب بالعربية بوصف دقيق ومفيد."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
        ]}]
        payload = {"model": VISION_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 1500}
        req = urllib.request.Request(GROQ_URL,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        return jsonify({"reply": data["choices"][0]["message"]["content"]})
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        return jsonify({"reply": f"⚠️ خطأ {e.code}: {err[:300]}"})
    except Exception as e:
        return jsonify({"reply": f"⚠️ خطأ: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
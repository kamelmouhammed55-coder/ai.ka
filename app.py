from flask import Flask, request, jsonify, render_template_string
import re, math, datetime, json, os, urllib.request

app = Flask(__name__)

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

try:
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)
except Exception:
    memory = {}

def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def norm(s):
    s = str(s or "")
    s = re.sub(r"[\u064B-\u0652\u0640]", "", s)
    s = re.sub(r"[أإآ]", "ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه")
    s = s.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return re.sub(r"\s+", " ", s).strip().lower()

CHAT = {
    "مرحبا": "أهلاً وسهلاً بك! كيف أساعدك؟",
    "اهلا": "أهلاً بك! كيف أساعدك؟",
    "سلام": "وعليكم السلام ورحمة الله وبركاته.",
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته.",
    "صباح الخير": "صباح النور!",
    "مساء الخير": "مساء النور!",
    "كيف حالك": "بخير والحمد لله. كيف أساعدك؟",
    "واش راك": "الحمد لله بخير! كيف نقدر نساعدك؟",
    "كيراك": "الحمد لله بخير! كيف نقدر نساعدك؟",
    "شكرا": "العفو! 🌟",
    "من انت": "أنا مساعد ذكي بسيط مبني ببايثون. أقدر أساعدك في الحساب وبعض الأسئلة العامة.",
    "شكون انت": "أنا مساعد ذكي بسيط مبني ببايثون.",
    "ما اسمك": "اسمي مساعد.",
    "وداعا": "في أمان الله!",
}

KB = [
    (["عدد", "سور", "القران"], "عدد سور القرآن الكريم 114 سورة."),
    (["عدد", "اجزاء", "القران"], "القرآن الكريم ثلاثون جزءاً."),
    (["اطول", "سوره"], "أطول سورة في القرآن هي سورة البقرة، وعدد آياتها 286 آية."),
    (["اقصر", "سوره"], "أقصر سورة في القرآن هي سورة الكوثر، وعدد آياتها ثلاث آيات."),
    (["اركان", "الاسلام"], "أركان الإسلام خمسة: الشهادتان، الصلاة، الزكاة، الصوم، والحج لمن استطاع إليه سبيلاً."),
    (["اركان", "الايمان"], "أركان الإيمان ستة: الإيمان بالله وملائكته وكتبه ورسله واليوم الآخر والقدر خيره وشره."),
    (["عدد", "قارات"], "عدد القارات سبع."),
    (["اكبر", "قاره"], "أكبر قارات العالم هي آسيا."),
    (["اكبر", "دوله"], "أكبر دولة في العالم مساحةً هي روسيا."),
    (["اكبر", "دوله", "عربيه"], "أكبر دولة عربية مساحةً هي الجزائر."),
    (["عدد", "كواكب"], "عدد كواكب المجموعة الشمسية ثمانية."),
    (["اكبر", "كوكب"], "أكبر كواكب المجموعة الشمسية هو المشتري."),
    (["اقرب", "كوكب", "شمس"], "أقرب كوكب إلى الشمس هو عطارد."),
    (["سرعه", "ضوء"], "سرعة الضوء في الفراغ نحو 300 ألف كيلومتر في الثانية."),
    (["عدد", "عظام", "انسان"], "يملك الإنسان البالغ عادةً 206 عظمات."),
    (["عدد", "اسنان"], "عدد أسنان الإنسان البالغ عادةً 32 سناً."),
    (["درجه", "غليان", "ماء"], "يغلي الماء عند 100 درجة مئوية تقريباً عند مستوى سطح البحر."),
    (["درجه", "تجمد", "ماء"], "يتجمد الماء عند 0 درجة مئوية تقريباً."),
    (["استقلت", "جزائر"], "استقلت الجزائر في 5 جويلية 1962."),
    (["ثوره", "جزائريه"], "اندلعت الثورة التحريرية الجزائرية في 1 نوفمبر 1954."),
    (["عمله", "جزائر"], "عملة الجزائر هي الدينار الجزائري."),
    (["اكبر", "حيوان"], "أكبر حيوان على وجه الأرض هو الحوت الأزرق."),
    (["اسرع", "حيوان"], "الفهد الصياد من أسرع الحيوانات البرية."),
]

def calculate(text):
    s = norm(text)
    s = s.replace("×", "*").replace("÷", "/")
    replacements = [
        ("زائد", "+"), ("زايد", "+"), ("جمع", "+"),
        ("ناقص", "-"), ("طرح", "-"),
        ("مضروب في", "*"), ("ضرب", "*"),
        ("مقسوم على", "/"), ("قسمة", "/"),
    ]
    for word, op in replacements:
        s = s.replace(word, op)

    s = re.sub(r"[^0-9+\-*/().%^ ]", "", s)
    if not re.search(r"\d", s):
        return None

    if len(s) > 120 or re.search(r"[^0-9+\-*/().%^ ]", s):
        return None

    try:
        if "^" in s:
            s = s.replace("^", "**")
        if "%" in s:
            m = re.fullmatch(r"([0-9.]+)\s*%\s*([0-9.]+)", s)
            if m:
                return float(m.group(1)) * float(m.group(2)) / 100
        if "**" in s and re.search(r"\*\*\s*\d{4,}", s):
            return None
        result = eval(s, {"__builtins__": {}}, {})
        if isinstance(result, (int, float)) and math.isfinite(result):
            return result
    except Exception:
        return None
    return None

def knowledge(text):
    words = set(norm(text).split())
    for keys, answer in KB:
        if all(k in words for k in keys):
            return answer
    return None

def quran_answer(text):
    n = norm(text)
    m = re.search(r"(?:ايه|اية)\s+([^\d]+)\s+(\d+)", n)
    if not m:
        return None
    surah = m.group(1).strip()
    ayah = int(m.group(2))
    names = {
        "الفاتحه": 1, "البقره": 2, "ال عمران": 3, "النساء": 4,
        "المائده": 5, "الانعام": 6, "الاعراف": 7, "الكهف": 18,
        "مريم": 19, "طه": 20, "يس": 36, "الرحمن": 55,
        "الملك": 67, "الاخلاص": 112, "الفلق": 113, "الناس": 114
    }
    if surah not in names:
        return "اكتب اسم السورة بشكل واضح، مثل: آية البقرة 255."
    try:
        url = f"https://api.alquran.cloud/v1/ayah/{names[surah]}:{ayah}/quran-uthmani"
        req = urllib.request.Request(url, headers={"User-Agent": "simple-python-assistant"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["data"]["text"]
    except Exception:
        return "تعذر جلب الآية حالياً. تأكد من اتصال الإنترنت."

def reply(text):
    raw = str(text or "").strip()
    n = norm(raw)

    if not raw:
        return "اكتب سؤالك أولاً."

    if n in {"كم الساعة", "ما الوقت", "قداه الساعة", "شحال الساعة"}:
        return "الساعة الآن " + datetime.datetime.now().strftime("%H:%M")

    if n in {"ما التاريخ", "ما اليوم", "كم التاريخ", "ما تاريخ اليوم"}:
        return "اليوم " + datetime.datetime.now().strftime("%Y/%m/%d")

    m = re.match(r"اسمي\s+(.+)", n)
    if m:
        memory["name"] = m.group(1).strip()
        save_memory()
        return "تم حفظ اسمك في الذاكرة."

    if n in {"ما اسمي", "واش اسمي", "شكون اسمي"}:
        if memory.get("name"):
            return "اسمك هو " + memory["name"] + "."
        return "مازال ما قلتليش اسمك."

    if n in CHAT:
        return CHAT[n]

    q = quran_answer(raw)
    if q:
        return q

    k = knowledge(raw)
    if k:
        return k

    result = calculate(raw)
    if result is not None:
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"الناتج: {result}"

    return (
        "ما فهمتش السؤال بشكل كافٍ. جرّب مثلاً:\n"
        "• 25 + 17\n"
        "• شحال 8 × 7\n"
        "• عدد سور القرآن\n"
        "• ما هي أكبر قارة؟\n"
        "• كم الساعة؟"
    )

HTML = r"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>مساعدي الذكي</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#10131a;color:#fff;font-family:Arial,sans-serif}
.app{max-width:760px;margin:auto;height:100vh;display:flex;flex-direction:column}
header{padding:18px;text-align:center;background:#171b24;border-bottom:1px solid #2a3040}
header h1{margin:0 0 6px;font-size:23px}
header p{margin:0;color:#aeb7c8;font-size:13px}
#chat{flex:1;overflow-y:auto;padding:18px}
.msg{max-width:85%;padding:12px 15px;margin:10px 0;border-radius:16px;white-space:pre-wrap;line-height:1.6}
.user{margin-right:auto;background:#2563eb}
.bot{margin-left:auto;background:#222938}
.bar{display:flex;gap:8px;padding:12px;background:#171b24}
input{flex:1;border:0;border-radius:14px;padding:13px;background:#fff;color:#111;font-size:16px;outline:0}
button{border:0;border-radius:14px;padding:0 18px;background:#2563eb;color:white;font-size:16px}
button:active{transform:scale(.98)}
</style>
</head>
<body>
<div class="app">
<header>
<h1>🤖 مساعدي الذكي</h1>
<p>مساعد عربي بسيط للحساب والأسئلة العامة</p>
</header>
<div id="chat">
<div class="msg bot">أهلاً بك! 👋 اكتب سؤالك وسأحاول مساعدتك.</div>
</div>
<form class="bar" id="form">
<input id="input" autocomplete="off" placeholder="اكتب رسالتك هنا...">
<button>إرسال</button>
</form>
</div>
<script>
const chat=document.getElementById("chat");
const input=document.getElementById("input");
function add(text,cls){
  const d=document.createElement("div");
  d.className="msg "+cls;
  d.textContent=text;
  chat.appendChild(d);
  chat.scrollTop=chat.scrollHeight;
}
document.getElementById("form").addEventListener("submit",async e=>{
  e.preventDefault();
  const text=input.value.trim();
  if(!text)return;
  add(text,"user");
  input.value="";
  try{
    const r=await fetch("/chat",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:text})
    });
    const data=await r.json();
    add(data.reply||"حدث خطأ.","bot");
  }catch(err){
    add("تعذر الاتصال بالخادم.","bot");
  }
});
</script>

<script type="text/javascript">
var sc_project=13358120; 
var sc_invisible=1; 
var sc_security="83ce6869"; 
</script>
<script type="text/javascript"
src="https://www.statcounter.com/counter/counter.js" async></script>

</body>
</html>
"""

@app.get("/")
def home():
    return render_template_string(HTML)

@app.post("/chat")
def chat_api():
    try:
        data = request.get_json(silent=True) or {}
        message = data.get("message", "")
        return jsonify({"reply": reply(message)})
    except Exception:
        return jsonify({"reply": "حدث خطأ غير متوقع."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
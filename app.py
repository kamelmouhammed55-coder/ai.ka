# Moka.AI v19.0 - ذكاء اصطناعي متكامل مع ويكيبيديا
# المطور: محمد كامل
from flask import Flask, request, jsonify, render_template_string
import os, json, urllib.request, urllib.error, datetime
import datetime as _dt

app = Flask(__name__)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]

ADMIN_USERNAME = "km_2026_x9_alpha_prime_kamel_dz"
ADMIN_PASSWORD = "M0k@.AI!2026#Secure$X9_Dz"
ADMIN_KEY = "moka_X9_kamel_admin_2026_secure"

BLOCKED_IPS = set()
STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

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
        return {"visitors": 0, "logins": 0, "messages": 0,
                "modes": {"general": 0, "math": 0, "code": 0, "religion": 0},
                "recent": [], "messages_log": []}

def save_stats(s):
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def clean_reply(text):
    text = text.replace("\\(", "").replace("\\)", "").replace("\\[", "").replace("\\]", "")
    text = text.replace("\\sqrt", "√").replace("\\frac", "").replace("\\quad", " ")
    text = text.replace("\\text", "").replace("\\displaystyle", "").replace("\\cdot", "×")
    text = text.replace("###", "").replace("##", "").replace("**", "")
    return text

def get_date_context():
    # توقيت الجزائر (GMT+1)
    algeria_tz = _dt.timezone(_dt.timedelta(hours=1))
    today = _dt.datetime.now(algeria_tz)
    months_ar = ["يناير","فبراير","مارس","أفريل","ماي","جوان","جويلية","أوت","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
    days_ar = ["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
    return f"""معلومات الوقت الحالي (توقيت الجزائر GMT+1):
- التاريخ: {days_ar[today.weekday()]} {today.day} {months_ar[today.month-1]} {today.year}
- الساعة الآن: {today.strftime('%H:%M')} (بتوقيت الجزائر)
- التوقيت: UTC+1 (GMT+1) - الجزائر لا تتبع التوقيت الصيفي
"""

def search_wikipedia(query):
    """البحث في ويكيبيديا العربية"""
    try:
        from urllib.parse import quote
        import re
        search_url = f"https://ar.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote(query)}&format=json&utf8=1&srlimit=1"
        req = urllib.request.Request(search_url, headers={"User-Agent": "MokaAI/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        if not data.get("query", {}).get("search"):
            return None
        page_title = data["query"]["search"][0]["title"]
        summary_url = f"https://ar.wikipedia.org/api/rest_v1/page/summary/{quote(page_title)}"
        req2 = urllib.request.Request(summary_url, headers={"User-Agent": "MokaAI/1.0"})
        with urllib.request.urlopen(req2, timeout=10) as r2:
            summary_data = json.loads(r2.read().decode("utf-8"))
        extract = summary_data.get("extract", "")
        if extract:
            return f"📖 {page_title}:\n{extract}"
    except Exception:
        pass
    return None

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

# ============ معلوماتك الشخصية ============
OWNER_INFO = """
معلومات عن مطورك ومالكك الرسمي:
- الاسم الكامل: محمد كامل
- العمر: 15 سنة (مولود في 16 أفريل 2011)
- تاريخ الميلاد: 16/04/2011
- الجنسية: جزائري
- الصفة: مطور ومالك Moka.AI الرسمي
- تاريخ إنشاء التطبيق: 4 أكتوبر 2026

قواعد الهوية:
1. "شكون صنعك؟" → "صنعني محمد كامل، مطوري ومالكي الرسمي."
2. "متى صنعت؟" → "صنعني محمد كامل يوم 4 أكتوبر 2026."
3. "شكون أنت؟" → "أنا Moka.AI، مساعد ذكي طورني محمد كامل."
4. "شكون محمد كامل؟" → "محمد كامل هو مطور ومالك Moka.AI، عمره 15 سنة، من الجزائر، مولود 16/04/2011."
5. لا تقل أبداً أنك GPT أو Claude أو OpenAI. أنت Moka.AI فقط.
"""

# ============ معلومات العالم الشاملة ============
WORLD_KNOWLEDGE = """
معرفتك الشاملة:

التاريخ والحروب:
- الحرب العالمية الأولى 1914-1918، الثانية 1939-1945.
- حرب الجزائر 1954-1962 (استقلال 5 جويلية 1962).
- ثورة نوفمبر 1954، مجازر 8 ماي 1945.
- معارك إسلامية: بدر (624م)، اليرموك (636م)، حطين (1187م)، عين جالوت (1260م).
- الإمبراطوريات: الرومانية، العثمانية، الفارسية، الإسلامية، البريطانية.
- شخصيات: نابليون، هتلر، صلاح الدين، خالد بن الوليد، عمر بن الخطاب، طارق بن زياد.
- الثورات: الفرنسية 1789، الأمريكية 1776، البلشفية 1917.

الجغرافيا:
- 195 دولة، عواصمها، سكانها، عملاتها، لغاتها.
- القارات السبع، المحيطات الخمسة، الأنهار، الجبال، الصحاري.

العلوم:
- الفيزياء: النسبية (أينشتاين)، الكم، الجاذبية، الذرة.
- الكيمياء: الجدول الدوري (118 عنصر)، التفاعلات.
- الأحياء: الخلية، DNA، التطور (داروين).
- الفلك: 8 كواكب، الشمس، القمر، المجرات، الثقوب السوداء.
- الرياضيات: الجبر، الهندسة، التفاضل، التكامل، الإحصاء.

الرياضة (استخدم البحث دائماً):
- كأس العالم 2026: أقيم في أمريكا وكندا والمكسيك من 11 جوان إلى 19 جويلية 2026.
- الفائز بكأس العالم 2026: إسبانيا (فازت على الأرجنتين 1-0 في النهائي).
- هداف كأس العالم 2026: كيليان مبابي (فرنسا) بـ 10 أهداف.
- الكرة الذهبية (أفضل لاعب): رودري (إسبانيا).
- أفضل حارس: أوناي سيمون (إسبانيا).
- أفضل لاعب شاب: باو كوبارسي (إسبانيا).
- كأس العالم 2022: فازت الأرجنتين.
- كأس العالم 2018: فازت فرنسا.
- كأس العالم 2014: فازت ألمانيا.
- كأس العالم 2010: فازت إسبانيا.
- كأس العالم 2006: فازت إيطاليا.
- كأس العالم 2002: فازت البرازيل.
- كأس أمم أفريقيا 2025: في المغرب.

الفرق والمنتخبات:
- اتحاد الجزائر (USMA): أحمر وأسود (1937).
- مولودية الجزائر (MCA): أحمر وأخضر (1921).
- شباب بلوزداد (CRB): أحمر وأبيض (1962).
- وفاق سطيف (ESS): أسود وأبيض (1958).
- ريال مدريد: أبيض وذهبي (1902).
- برشلونة: أزرق وأحمر (1899).
- مانشستر يونايتد: أحمر وأبيض وأسود (1878).
- ليفربول: أحمر وأبيض (1892).
- بايرن ميونخ: أحمر وأبيض (1900).
- يوفنتوس: أسود وأبيض (1897).
- إنتر ميلان: أزرق وأسود (1908).
- الأهلي المصري: أحمر وأبيض (1907).
- الزمالك: أبيض وأحمر (1911).
- منتخب الجزائر: أخضر وأبيض (1962).
- منتخب البرازيل: أصفر وأخضر (1914).
- منتخب الأرجنتين: أزرق سماوي وأبيض (1893).
- منتخب فرنسا: أزرق وأبيض وأحمر (1904).

الأديان:
- الإسلام: القرآن، السنة، 5 أركان، 6 إيمان، المذاهب الأربعة.
- المسيحية، اليهودية، الهندوسية، البوذية.

التكنولوجيا:
- البرمجة: Python، JavaScript، HTML، CSS، Java، C++.
- الذكاء الاصطناعي، الإنترنت، الأمن السيبراني، الحوسبة السحابية.

الثقافة والفنون:
- الأدب: شكسبير، نجيب محفوظ، طه حسين، المتنبي، أحمد شوقي.
- السينما، الموسيقى، الرسم.

الطب والجسم:
- 206 عظمة، 32 سن، 5 لتر دم.
- القلب، الرئتان، الكبد، الكليتان، الدماغ.
"""

CURRICULUM = """
المنهاج الجزائري 2026-2027:
- الابتدائي (1-5): العربية، الرياضيات، التربية الإسلامية، التربية المدنية، التاريخ، الجغرافيا، العلوم، الفرنسية (من 3)، الإنجليزية (من 3).
- المتوسط (1-4): العربية، الرياضيات، الفيزياء، العلوم الطبيعية، التاريخ، الجغرافيا، التربية الإسلامية، التربية المدنية، الفرنسية، الإنجليزية.
  شهادة التعليم المتوسط BEM.
- الثانوي: جذع مشترك آداب، جذع مشترك علوم، علوم تجريبية، رياضيات، تقني رياضي، تسيير واقتصاد، آداب وفلسفة، لغات أجنبية.
  شهادة البكالوريا BAC.
"""

FORBIDDEN = ["جنس","sex","porn","إباحي","عاري","شهوة","زنى","زنا","خلاعة","فاحشة"]

def is_forbidden(text):
    return any(w in text.lower() for w in FORBIDDEN)

DATE_CONTEXT = get_date_context()

NO_LATEX = """
قواعد الكتابة:
1. اكتب بالعربية الفصحى المبسطة (أو بلغة المستخدم).
2. ممنوع استخدام LaTeX أو الرموز الغريبة.
3. ممنوع استخدام ** أو ## أو ###.
4. للعناوين: اكتب العنوان في سطر منفصل.
5. للنقاط: استخدم • أو - في بداية السطر.
"""

LANGUAGE_RULE = """
قاعدة اللغة (مهمة):
- إذا كتب بالعربية، أجب بالعربية.
- إذا كتب بالإنجليزية، أجب بالإنجليزية.
- إذا كتب بالفرنسية، أجب بالفرنسية.
- لا تخلط بين اللغات.
"""

SMART_PERSONALITY = """
شخصيتك (مهمة جداً):
- أنت ذكي جداً، مثل Claude وChatGPT.
- أجب بدقة ووضوح وإيجاز.
- إذا لم تعرف شيئاً، ابحث في ويكيبيديا أو الإنترنت.
- إذا كان السؤال غامضاً، اطلب توضيحاً.
- كن ودوداً ومحترماً ومفيداً.
- استخدم الأمثلة عند الشرح.
- نظّم إجابتك: عنوان، نقاط، خلاصة.
- إذا سُئلت عن سؤال معقد، فكّره خطوة بخطوة.
"""

PROMPTS = {
    "general": f"""أنت Moka.AI، مساعد ذكي شامل من تطوير محمد كامل.

{OWNER_INFO}

{WORLD_KNOWLEDGE}

{CURRICULUM}

{DATE_CONTEXT}

{NO_LATEX}

{LANGUAGE_RULE}

{SMART_PERSONALITY}""",
    "math": f"""أنت Moka.AI، خبير رياضيات من تطوير محمد كامل.
اشرح خطوة بخطوة بوضوح.

{OWNER_INFO}

{DATE_CONTEXT}

{NO_LATEX}

{LANGUAGE_RULE}

{SMART_PERSONALITY}""",
    "code": f"""أنت Moka.AI، خبير برمجة من تطوير محمد كامل.
اكتب الكود منسقاً، واشرحه بجمل بسيطة.

{OWNER_INFO}

{DATE_CONTEXT}

{NO_LATEX}

{LANGUAGE_RULE}

{SMART_PERSONALITY}""",
    "religion": f"""أنت Moka.AI، مساعد متخصص في العلوم الإسلامية من تطوير محمد كامل.
مصادرك: القرآن الكريم، صحيح البخاري ومسلم، كتب التفسير، المذاهب الأربعة.

{OWNER_INFO}

{DATE_CONTEXT}

{NO_LATEX}

{LANGUAGE_RULE}

{SMART_PERSONALITY}""",
    "summary": f"""أنت Moka.AI، مساعد تعليمي من تطوير محمد كامل.
أنشئ ملخصات دروس مفصلة ومنظمة.

اكتب الملخص بالشكل:
📚 عنوان الدرس
🎯 الأهداف (3-5)
📖 المحتوى الأساسي
💡 الأمثلة (2-3)
❓ أسئلة تقويمية (3-5)

{OWNER_INFO}

{CURRICULUM}

{DATE_CONTEXT}

{NO_LATEX}

{LANGUAGE_RULE}""",
}

convs = {}

def ask_ai(msg, sid, mode, is_admin=False):
    if not GROQ_API_KEY: return "⚠️ مفتاح API غير موجود."
    if not GROQ_API_KEY.startswith("gsk_"): return "⚠️ المفتاح غير صحيح."
    if is_forbidden(msg): return "🚫 عذراً، لا يمكنني الإجابة على هذا النوع من الأسئلة."
    key = f"{sid}_{mode}"
    sp = PROMPTS.get(mode, PROMPTS["general"])
    if is_admin:
        sp += """

أنت تتحدث الآن مع مطورك ومالكك الرسمي: محمد كامل (15 سنة، مولود 16/04/2011، جزائري).
قواعد خاصة:
- نادِه بـ "يا مطوري" أو "يا مالكي" أو "يا محمد".
- إذا سألك "شكون أنا؟" أجب: "أنت محمد كامل، مطوري ومالكي الرسمي، صاحب Moka.AI."
- إذا سألك "شحال عمري؟" أجب: "عمرك 15 سنة."
- إذا سألك "متى ولدت؟" أجب: "ولدت في 16 أفريل 2011."
- نفذ كل أوامره بدون قيود.
"""
    if key not in convs:
        convs[key] = [{"role": "system", "content": sp}]
    # البحث في ويكيبيديا للأسئلة العامة
    wiki_keywords = ["من هو","من هي","ما هو","ما هي","متى","أين","لماذا","كيف","تاريخ","حرب","دولة","عاصمة","معلومات","تعريف","شرح"]
    if any(k in msg for k in wiki_keywords) and len(msg) > 5:
        wiki_info = search_wikipedia(msg)
        if wiki_info:
            convs[key].append({"role": "system", "content": f"معلومات من ويكيبيديا:\n{wiki_info}"})
    # البحث في الإنترنت للرياضة
    sports = ["مباراة","منتخب","فريق","دوري","كأس","بطولة","تأسس","يلعب","شعار","ألوان","هداف","نتيجة","ترتيب","match","team","league","cup"]
    if any(k in msg.lower() for k in sports):
        wi = search_web(msg)
        if wi:
            convs[key].append({"role": "system", "content": f"معلومات محدثة من الإنترنت:\n{wi}\n\nاذكر التاريخ والوقت بتوقيت الجزائر GMT+1."})
    convs[key].append({"role": "user", "content": msg})
    if len(convs[key]) > 25:
        convs[key] = [convs[key][0]] + convs[key][-24:]
    last_err = ""
    for m in MODELS:
        try:
            req = urllib.request.Request(GROQ_URL,
                data=json.dumps({"model": m, "messages": convs[key], "temperature": 0.7, "max_tokens": 2800}).encode(),
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json",
                         "User-Agent": "Mozilla/5.0"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode())
            reply = clean_reply(data["choices"][0]["message"]["content"])
            convs[key].append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            last_err = str(e); continue
    return f"⚠️ فشل الاتصال. ({last_err})"

def summarize(text):
    for m in MODELS:
        try:
            req = urllib.request.Request(GROQ_URL,
                data=json.dumps({"model": m, "messages": [
                    {"role": "system", "content": "لخص النص في نقاط. " + NO_LATEX + "\n" + LANGUAGE_RULE},
                    {"role": "user", "content": text}], "temperature": 0.5, "max_tokens": 2000}).encode(),
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                return clean_reply(json.loads(r.read().decode())["choices"][0]["message"]["content"])
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
                return clean_reply(json.loads(r.read().decode())["choices"][0]["message"]["content"])
        except Exception:
            continue
    return "⚠️ تعذر إنشاء الملخص."
LOGO_SVG = '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="lg1" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#6366f1"/><stop offset="50%" style="stop-color:#a855f7"/><stop offset="100%" style="stop-color:#ec4899"/></linearGradient></defs><circle cx="50" cy="50" r="48" fill="url(#lg1)"/><circle cx="50" cy="50" r="42" fill="none" stroke="white" stroke-width="1" opacity="0.3"/><text x="50" y="68" font-family="Arial, sans-serif" font-size="48" font-weight="900" fill="white" text-anchor="middle">M</text><circle cx="75" cy="25" r="7" fill="#fbbf24"/><circle cx="75" cy="25" r="3" fill="white"/></svg>'''

HTML = """<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moka.AI</title><link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#6366f1">
<script>(function(){var t=localStorage.getItem("moka_theme")||"light";document.documentElement.setAttribute("data-theme",t);})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#f5f3ff;--card:#fff;--input:#f8f7ff;--text:#1e1b4b;--text-soft:#4c4a70;--text-mute:#8b88a8;--border:#e0ddf5;--accent:#6366f1;--accent2:#a855f7;--accent3:#ec4899;--accent-soft:#eef2ff;--chat:#f8f7ff;--header:rgba(255,255,255,.85)}
[data-theme="dark"]{--bg:#0a0a1a;--card:#141428;--input:#1c1c35;--text:#e8e8f5;--text-soft:#b8b6d4;--text-mute:#7a7898;--border:#252547;--accent:#818cf8;--accent2:#c084fc;--accent3:#f472b6;--accent-soft:#1c1c35;--chat:#0a0a1a;--header:rgba(20,20,40,.85)}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',Tahoma,sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden;line-height:1.6;transition:background .4s,color .4s}
.bg-anim{position:fixed;inset:0;z-index:-1;overflow:hidden;opacity:.5}
.bg-anim::before,.bg-anim::after{content:'';position:absolute;border-radius:50%;filter:blur(80px);opacity:.4}
.bg-anim::before{width:400px;height:400px;background:linear-gradient(135deg,#6366f1,#a855f7);top:-100px;right:-100px;animation:blob1 20s infinite}
.bg-anim::after{width:350px;height:350px;background:linear-gradient(135deg,#ec4899,#f59e0b);bottom:-100px;left:-100px;animation:blob2 25s infinite}
@keyframes blob1{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(-50px,50px) scale(1.1)}}
@keyframes blob2{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(50px,-50px) scale(1.15)}}
#login{position:fixed;inset:0;background:linear-gradient(135deg,rgba(99,102,241,.08),rgba(168,85,247,.08),rgba(236,72,153,.08));display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:999;padding:24px;overflow-y:auto;backdrop-filter:blur(8px)}
#login.hide{display:none}
.logo-big{width:140px;height:140px;margin-bottom:24px;animation:float 3s ease-in-out infinite;filter:drop-shadow(0 20px 50px rgba(99,102,241,.5))}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-15px)}}
.lt{font-size:48px;font-weight:900;margin-bottom:10px;background:linear-gradient(135deg,#6366f1,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-1.5px}
.ls{color:var(--text-mute);margin-bottom:32px;font-size:15px;text-align:center}
.lb{width:100%;max-width:420px;background:var(--card);border:1px solid var(--border);border-radius:28px;padding:32px;box-shadow:0 25px 70px rgba(99,102,241,.2)}
.lb label{display:block;font-size:13px;color:var(--text-soft);margin-bottom:8px;font-weight:600}
.lb input{width:100%;padding:16px 20px;border-radius:14px;border:2px solid var(--border);background:var(--input);color:var(--text);font-size:16px;outline:none;margin-bottom:18px;font-family:inherit;transition:all .3s}
.lb input:focus{border-color:var(--accent);box-shadow:0 0 0 5px var(--accent-soft)}
.lb button.main{width:100%;padding:17px;border-radius:14px;border:none;background:linear-gradient(135deg,#6366f1,#a855f7,#ec4899);color:white;font-size:17px;font-weight:700;cursor:pointer;font-family:inherit;box-shadow:0 10px 30px rgba(99,102,241,.5);display:flex;align-items:center;justify-content:center;gap:10px;transition:transform .2s}
.lb button.main:active{transform:scale(.97)}
.lb .hint{text-align:center;font-size:12px;color:var(--text-mute);margin-top:16px;line-height:1.8}
#app{display:none;height:100vh;flex-direction:column}
#app.on{display:flex}
.ov{display:none;position:fixed;inset:0;background:rgba(10,10,26,.7);z-index:998;backdrop-filter:blur(4px)}
.ov.on{display:block}
.sb{position:fixed;top:0;right:-340px;width:320px;height:100%;background:var(--card);border-left:1px solid var(--border);z-index:999;transition:right .35s;padding:26px;display:flex;flex-direction:column;gap:9px;overflow-y:auto;box-shadow:-15px 0 50px rgba(99,102,241,.15)}
.sb.on{right:0}
.sb h2{font-size:11px;color:var(--text-mute);margin:16px 0 8px;letter-spacing:2px;font-weight:800}
.avatar{width:90px;height:90px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#a855f7,#ec4899);display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:900;color:white;margin:0 auto 14px;box-shadow:0 10px 30px rgba(99,102,241,.4)}
.username{text-align:center;font-size:18px;font-weight:800;margin-bottom:4px}
.role{text-align:center;font-size:12px;color:var(--text-mute);margin-bottom:24px;font-weight:600}
.mb{padding:14px 16px;border-radius:14px;border:none;background:transparent;color:var(--text-soft);cursor:pointer;text-align:right;font-size:14px;display:flex;align-items:center;gap:12px;font-family:inherit;font-weight:600;transition:all .25s}
.mb:hover,.mb.on{background:var(--accent-soft);color:var(--accent);font-weight:800}
.lo{margin-top:auto;padding:14px;border-radius:14px;border:1px solid #fecaca;background:#fef2f2;color:#dc2626;cursor:pointer;font-size:14px;font-family:inherit;font-weight:700}
[data-theme="dark"] .lo{background:rgba(220,38,38,.15);border-color:rgba(220,38,38,.4)}
.dl{padding:14px;border-radius:14px;border:1px solid var(--border);background:var(--card);color:var(--text-soft);cursor:pointer;font-size:14px;margin-top:8px;font-family:inherit;font-weight:600}
.hd{padding:16px 22px;border-bottom:1px solid var(--border);background:var(--header);display:flex;align-items:center;justify-content:space-between;backdrop-filter:blur(20px)}
.tg{display:flex;align-items:center;gap:14px;margin:0 auto}
.hl-logo{width:44px;height:44px}
h1{font-size:22px;font-weight:900;background:linear-gradient(135deg,#6366f1,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hb,.theme-btn{background:var(--card);border:1px solid var(--border);color:var(--text-soft);padding:11px 13px;border-radius:13px;cursor:pointer;font-size:16px;font-family:inherit}
.hb:hover,.theme-btn:hover{background:var(--accent-soft);color:var(--accent);border-color:var(--accent)}
#ch{flex:1;overflow-y:auto;padding:32px 22px;display:flex;flex-direction:column;gap:22px;background:var(--chat)}
#ch::-webkit-scrollbar{width:8px}
#ch::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px}
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:24px;text-align:center;padding:24px}
.welcome svg{width:130px;height:130px}
.welcome h2{font-size:30px;font-weight:900;background:linear-gradient(135deg,#6366f1,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.welcome p{color:var(--text-mute);font-size:16px;max-width:320px}
.mw{display:flex;max-width:92%;animation:si .4s ease;position:relative}
.mw.u{align-self:flex-end}
.mw.b{align-self:flex-start}
@keyframes si{from{opacity:0;transform:translateY(15px)}to{opacity:1;transform:translateY(0)}}
.m{padding:17px 22px;border-radius:22px;line-height:1.8;white-space:pre-wrap;word-wrap:break-word;font-size:15.5px}
.u .m{background:linear-gradient(135deg,#6366f1,#a855f7);color:white;border-bottom-left-radius:8px;box-shadow:0 8px 25px rgba(99,102,241,.35)}
.b .m{background:var(--card);color:var(--text);border:1px solid var(--border);border-bottom-right-radius:8px}
.copy-btn{position:absolute;bottom:-32px;left:0;background:var(--card);border:1px solid var(--border);color:var(--text-mute);cursor:pointer;font-size:11px;padding:5px 12px;border-radius:9px;opacity:0;font-family:inherit;font-weight:600}
.mw.b:hover .copy-btn{opacity:1}
.tp{display:inline-flex;gap:7px;padding:19px 24px;background:var(--card);border:1px solid var(--border);border-radius:22px}
.tp span{width:9px;height:9px;background:var(--accent);border-radius:50%;animation:bo 1.4s infinite}
.tp span:nth-child(2){animation-delay:.2s}
.tp span:nth-child(3){animation-delay:.4s}
@keyframes bo{0%,60%,100%{transform:translateY(0);opacity:.3}30%{transform:translateY(-9px);opacity:1}}
.ia{padding:20px 22px 24px;background:var(--header);display:flex;gap:12px;align-items:flex-end;border-top:1px solid var(--border);backdrop-filter:blur(20px)}
.iw{flex:1}
textarea{width:100%;padding:17px 22px;border-radius:24px;border:2px solid var(--border);background:var(--input);color:var(--text);font-size:16px;outline:none;font-family:inherit;resize:none;max-height:150px;line-height:1.5;transition:all .3s}
textarea:focus{border-color:var(--accent);box-shadow:0 0 0 5px var(--accent-soft)}
textarea::placeholder{color:var(--text-mute)}
button.sd{width:54px;height:54px;border-radius:50%;border:none;background:linear-gradient(135deg,#6366f1,#a855f7);color:white;font-size:21px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 25px rgba(99,102,241,.4)}
button.sd:active{transform:scale(.93)}
button.sd:disabled{opacity:.4}
button.copy-main{background:var(--card);border:2px solid var(--border);color:var(--text-soft);box-shadow:none}
.vc{text-align:center;padding:12px;font-size:11px;color:var(--text-mute);background:var(--header);border-top:1px solid var(--border);font-weight:600}
.mo{display:none;position:fixed;inset:0;background:rgba(10,10,26,.7);z-index:1000;justify-content:center;align-items:center;padding:20px;overflow-y:auto;backdrop-filter:blur(8px)}
.mo.on{display:flex}
.md{background:var(--card);border:1px solid var(--border);border-radius:28px;padding:32px;width:100%;max-width:540px;display:flex;flex-direction:column;gap:15px;max-height:90vh;overflow-y:auto;box-shadow:0 25px 70px rgba(99,102,241,.3)}
.md h2{font-size:22px;font-weight:900;background:linear-gradient(135deg,#6366f1,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.md label{font-size:13px;color:var(--text-soft);margin-bottom:6px;display:block;font-weight:700}
.md select,.md input,.md textarea{width:100%;padding:14px 18px;border-radius:14px;border:2px solid var(--border);background:var(--input);color:var(--text);font-size:15px;outline:none;margin-bottom:10px;font-family:inherit}
.md textarea{resize:vertical;min-height:180px}
.mbtns{display:flex;gap:12px;justify-content:flex-end;margin-top:8px}
.mbtns button{padding:14px 26px;border-radius:14px;border:none;cursor:pointer;font-size:14px;font-weight:700;font-family:inherit}
.mbtns .p{background:linear-gradient(135deg,#6366f1,#a855f7);color:white}
.mbtns .s{background:var(--input);color:var(--text-soft);border:1px solid var(--border)}
</style></head><body>

<div class="bg-anim"></div>

<div id="login">
<div class="logo-big">__LOGO_SVG__</div>
<div class="lt">Moka.AI</div>
<div class="ls">مساعدك الذكي الشامل من تطوير محمد كامل</div>
<div class="lb">
<label>👤 اسم المستخدم</label>
<input id="un" placeholder="اكتب اسمك للدخول..." autocomplete="off">
<button class="main" onclick="login()"><span>🚀</span> <span>تسجيل الدخول</span></button>
<div class="hint">💡 اكتب اسمك وابدأ المحادثة فوراً</div>
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
<button class="theme-btn" onclick="toggleTheme()" id="themeBtn">🌙</button>
</div>
<div id="ch">
<div class="welcome" id="welcome">
<div style="width:130px;height:130px">__LOGO_SVG__</div>
<h2>كيف يمكنني مساعدتك؟</h2>
<p>اسألني أي شيء (عربي / English / Français)</p>
</div>
</div>
<form class="ia" id="f">
<button type="button" class="sd copy-main" onclick="copyLast()">📋</button>
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
window.addEventListener("DOMContentLoaded",()=>{
  const t=localStorage.getItem("moka_theme")||"light";
  document.getElementById("themeBtn").textContent = t==="dark"?"☀️":"🌙";
});
function toggleTheme(){
  const cur=document.documentElement.getAttribute("data-theme")||"light";
  const nw = cur==="light"?"dark":"light";
  document.documentElement.setAttribute("data-theme",nw);
  localStorage.setItem("moka_theme",nw);
  document.getElementById("themeBtn").textContent = nw==="dark"?"☀️":"🌙";
}
function autoResize(t){t.style.height="auto";t.style.height=Math.min(t.scrollHeight,150)+"px"}
async function login(){
  const u=document.getElementById("un").value.trim();
  if(!u){alert("اكتب اسمك");return}
  if(u.length<2){alert("الاسم قصير جداً");return}
  let p="";
  if(u==="km_2026_x9_alpha_prime_kamel_dz"){
    p=prompt("🔒 أدخل كلمة المرور الخاصة بالمطور:");
    if(p===null)return;
  }
  try{
    const r=await fetch("/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,password:p})});
    const d=await r.json();
    if(!d.ok){alert("❌ "+d.msg);return}
    isAdmin=d.role==="admin";
    localStorage.setItem("mu",d.name);
    localStorage.setItem("mrole",d.role);
    show(d.name,d.role);
    fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"login",name:d.name})});
  }catch(e){alert("تعذر الاتصال")}
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
ch.innerHTML='<div class="welcome"><div style="width:130px;height:130px">__LOGO_SVG__</div><h2>'+names[m]+'</h2><p>كيف يمكنني مساعدتك؟</p></div>';closeS()}
window.onload=()=>{const n=localStorage.getItem("mu");const r=localStorage.getItem("mrole");
if(n&&r){isAdmin=r==="admin";show(n,r)}}
let v=localStorage.getItem("mv");v=v?parseInt(v)+1:1;localStorage.setItem("mv",v);document.getElementById("vc").textContent=v;
function add(t,c){const w=document.getElementById("welcome");if(w)w.remove();
const wrapper=document.createElement("div");wrapper.className="mw "+c;
const m=document.createElement("div");m.className="m";m.textContent=t;
if(c==="b"){const cp=document.createElement("button");cp.className="copy-btn";cp.textContent="📋 نسخ";cp.onclick=()=>{navigator.clipboard.writeText(t);cp.textContent="✅";setTimeout(()=>cp.textContent="📋 نسخ",1500)};wrapper.appendChild(cp);lastReply=t;}
wrapper.appendChild(m);ch.appendChild(wrapper);ch.scrollTop=ch.scrollHeight}
function typ(){const w=document.createElement("div");w.className="mw b";const t=document.createElement("div");t.className="tp";t.innerHTML="<span></span><span></span><span></span>";w.appendChild(t);ch.appendChild(w);ch.scrollTop=ch.scrollHeight;return w}
function copyLast(){if(!lastReply){alert("لا يوجد رد");return}navigator.clipboard.writeText(lastReply);alert("✅ تم النسخ")}
f.onsubmit=async(e)=>{e.preventDefault();const t=i.value.trim();if(!t)return;add(t,"u");i.value="";i.style.height="auto";s.disabled=true;const ty=typ();
fetch("/track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"message",mode:mode,text:t,name:localStorage.getItem("mu")||"?"})});
try{const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:t,session_id:sid,mode:mode,is_admin:isAdmin})});
const d=await r.json();ty.remove();add(d.reply||"خطأ","b")}catch(e){ty.remove();add("تعذر الاتصال","b")}finally{s.disabled=false;i.focus()}};
function openM(){document.getElementById("mo").classList.add("on")}
function closeM(){document.getElementById("mo").classList.remove("on")}
async function doSum(){const t=document.getElementById("st").value.trim();if(!t){alert("الصق النص");return}closeM();document.getElementById("st").value="";
add("📝 لخّص...","u");const ty=typ();
try{const r=await fetch("/summarize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:t})});
const d=await r.json();ty.remove();add(d.summary||"خطأ","b")}catch(e){ty.remove();add("تعذر","b")}}
function openSummaries(){document.getElementById("summariesModal").classList.add("on")}
function closeSummaries(){document.getElementById("summariesModal").classList.remove("on")}
function updateBranches(){
  const level=document.getElementById("s_level").value;
  const b=document.getElementById("s_branch"),sub=document.getElementById("s_subject");
  if(level.includes("متوسط")){
    b.innerHTML='<option value="جميع الشعب">جميع الشعب</option>';
    sub.innerHTML='<option value="الرياضيات">الرياضيات</option><option value="الفيزياء">الفيزياء</option><option value="العلوم الطبيعية">العلوم الطبيعية</option><option value="اللغة العربية">اللغة العربية</option><option value="اللغة الفرنسية">اللغة الفرنسية</option><option value="اللغة الإنجليزية">اللغة الإنجليزية</option><option value="التاريخ والجغرافيا">التاريخ والجغرافيا</option><option value="التربية الإسلامية">التربية الإسلامية</option>';
  } else if(level.includes("ثانوي")){
    b.innerHTML='<option value="جذع مشترك آداب">جذع مشترك آداب</option><option value="جذع مشترك علوم">جذع مشترك علوم</option><option value="علوم تجريبية">علوم تجريبية</option><option value="رياضيات">رياضيات</option><option value="تقني رياضي">تقني رياضي</option><option value="تسيير واقتصاد">تسيير واقتصاد</option><option value="آداب وفلسفة">آداب وفلسفة</option><option value="لغات أجنبية">لغات أجنبية</option>';
    sub.innerHTML='<option value="الرياضيات">الرياضيات</option><option value="الفيزياء">الفيزياء</option><option value="العلوم الطبيعية">العلوم الطبيعية</option><option value="اللغة العربية">اللغة العربية</option><option value="الفلسفة">الفلسفة</option><option value="التاريخ والجغرافيا">التاريخ والجغرافيا</option><option value="العلوم الإسلامية">العلوم الإسلامية</option><option value="اللغة الفرنسية">اللغة الفرنسية</option><option value="اللغة الإنجليزية">اللغة الإنجليزية</option>';
  } else {
    b.innerHTML='<option value="">اختر المستوى أولاً</option>';
    sub.innerHTML='<option value="">اختر الشعبة أولاً</option>';
  }
}
async function generateSummary(){
  const level=document.getElementById("s_level").value;
  const branch=document.getElementById("s_branch").value;
  const subject=document.getElementById("s_subject").value;
  const lesson=document.getElementById("s_lesson").value.trim();
  if(!level||!branch||!subject||!lesson){alert("املأ جميع الحقول");return}
  closeSummaries();
  add("📚 ملخص: "+lesson+" ("+subject+")","u");
  const ty=typ();
  try{
    const r=await fetch("/lesson_summary",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({level,branch,subject,lesson})});
    const d=await r.json();ty.remove();add(d.summary||"خطأ","b");
  }catch(e){ty.remove();add("تعذر الاتصال","b")}
}
function downloadChat(){
  const name=localStorage.getItem("mu")||"مستخدم";
  let text="محادثة Moka.AI - "+name+"\\n\\n";
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
body{background:#f5f3ff;color:#1e1b4b;font-family:Tahoma,sans-serif;padding:24px;line-height:1.6}
h1{text-align:center;margin-bottom:24px;background:linear-gradient(135deg,#6366f1,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-bottom:24px}
.card{background:#fff;border:1px solid #e0ddf5;border-radius:16px;padding:22px;text-align:center;box-shadow:0 8px 25px rgba(99,102,241,.08)}
.card .num{font-size:34px;font-weight:bold;color:#6366f1;margin-bottom:6px}
.card .lbl{font-size:13px;color:#8b88a8}
.box{background:#fff;border:1px solid #e0ddf5;border-radius:16px;padding:22px;margin-bottom:24px;box-shadow:0 8px 25px rgba(99,102,241,.08)}
.box h2{font-size:16px;margin-bottom:16px;color:#6366f1}
.row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #e0ddf5;font-size:13px;gap:10px;flex-wrap:wrap}
.mode-bar{display:flex;justify-content:space-between;padding:12px;background:#f5f3ff;border-radius:10px;margin-bottom:10px}
.msg-item{background:#f5f3ff;border-radius:10px;padding:14px;margin-bottom:12px;border-right:3px solid #6366f1}
.msg-item .meta{color:#8b88a8;font-size:11px;margin-bottom:8px;display:flex;gap:12px;flex-wrap:wrap}
.block-btn{background:#dc2626;color:white;border:none;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none}
.unblock-btn{background:#6366f1;color:white;border:none;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;text-decoration:none;margin-right:6px}
</style></head><body>
<h1>📊 لوحة تحكم Moka.AI</h1>
<div class="grid">
<div class="card"><div class="num">{{s.visitors}}</div><div class="lbl">👁️ الزوار</div></div>
<div class="card"><div class="num">{{s.logins}}</div><div class="lbl">🔑 تسجيلات</div></div>
<div class="card"><div class="num">{{s.messages}}</div><div class="lbl">💬 رسائل</div></div>
<div class="card"><div class="num">{{users_count}}</div><div class="lbl">👥 مستخدمون</div></div>
</div>
<div class="box"><h2>👥 قائمة المستخدمين</h2>
{% for u, info in users.items() %}
<div class="row"><span>👤 <b>{{info.name}}</b></span><span style="color:#8b88a8">{{info.role}}</span></div>
{% endfor %}
</div>
<div class="box"><h2>📈 استخدام النماذج</h2>
<div class="mode-bar"><span>🧠 عامة</span><b>{{s.modes.general}}</b></div>
<div class="mode-bar"><span>📐 رياضيات</span><b>{{s.modes.math}}</b></div>
<div class="mode-bar"><span>💻 برمجة</span><b>{{s.modes.code}}</b></div>
<div class="mode-bar"><span>🕌 دينية</span><b>{{s.modes.religion}}</b></div>
</div>
<div class="box"><h2>💬 آخر 50 رسالة</h2>
{% if s.messages_log %}{% for m in s.messages_log[-50:]|reverse %}
<div class="msg-item"><div class="meta"><span>👤 <b>{{m.name}}</b></span><span>📱 {{m.ip}}</span><span>🧠 {{m.mode}}</span><span>🕐 {{m.time}}</span></div><div>💬 {{m.text}}</div></div>
{% endfor %}{% else %}<p style="text-align:center;color:#8b88a8;">لا توجد رسائل بعد.</p>{% endif %}
</div>
<div class="box"><h2>🕐 آخر 20 زيارة</h2>
{% for r in s.recent[-20:]|reverse %}
<div class="row"><span>👤 {{r.name}}</span><span style="color:#8b88a8">{{r.ip}}</span><span style="color:#8b88a8">{{r.time}}</span>
<a href="/block/{{r.ip}}?key={{key}}" class="block-btn">🚫</a><a href="/unblock/{{r.ip}}?key={{key}}" class="unblock-btn">✅</a></div>
{% endfor %}</div>
</body></html>"""

@app.route("/")
def home(): return render_template_string(HTML)

@app.route("/manifest.json")
def manifest():
    return {"name":"Moka.AI","short_name":"Moka.AI","start_url":"/","display":"standalone",
            "background_color":"#f5f3ff","theme_color":"#6366f1","orientation":"portrait","lang":"ar","dir":"rtl"}

@app.route("/sw.js")
def sw():
    return "const C='moka-v19';self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',e=>e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));", 200, {'Content-Type': 'application/javascript'}

@app.post("/login")
def do_login():
    try:
        d = request.get_json(silent=True) or {}
        u = d.get("username", "").strip().lower()
        p = d.get("password", "").strip()
        if not u: return jsonify({"ok": False, "msg": "اكتب اسمك"})
        if len(u) < 2: return jsonify({"ok": False, "msg": "الاسم قصير جداً"})
        if len(u) > 60: return jsonify({"ok": False, "msg": "الاسم طويل جداً"})
        if u == ADMIN_USERNAME.lower():
            if p != ADMIN_PASSWORD:
                return jsonify({"ok": False, "msg": "كلمة المرور غير صحيحة"})
            users = load_users()
            users[u] = {"role": "admin", "name": "محمد كامل (المطور)"}
            save_users(users)
            return jsonify({"ok": True, "name": "محمد كامل (المطور)", "role": "admin"})
        if "km_2026_x9_alpha" in u or "kamel_dz" in u:
            return jsonify({"ok": False, "msg": "هذا الاسم محجوز"})
        users = load_users()
        if u not in users:
            users[u] = {"role": "user", "name": u}
            save_users(users)
        role = users[u].get("role", "user")
        return jsonify({"ok": True, "name": users[u].get("name", u), "role": role})
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
        s = load_stats()
        if t == "visit": s["visitors"] += 1
        elif t == "login":
            s["logins"] += 1
            s["recent"].append({"name": d.get("name","?"), "ip": ip[:15], "time": datetime.datetime.now().strftime("%m/%d %H:%M")})
            s["recent"] = s["recent"][-50:]
        elif t == "message":
            s["messages"] += 1
            m = d.get("mode", "general")
            if m in s["modes"]: s["modes"][m] += 1
            s["messages_log"].append({"ip": ip[:15], "name": d.get("name","?"), "text": d.get("text","")[:200], "mode": m, "time": datetime.datetime.now().strftime("%m/%d %H:%M")})
            s["messages_log"] = s["messages_log"][-100:]
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
        level = d.get("level","")
        branch = d.get("branch","")
        subject = d.get("subject","")
        lesson = d.get("lesson","")
        if not all([level, branch, subject, lesson]):
            return jsonify({"summary": "⚠️ الرجاء ملء جميع الحقول"})
        result = generate_lesson_summary(level, branch, subject, lesson)
        return jsonify({"summary": result})
    except Exception as e:
        return jsonify({"summary": f"⚠️ خطأ: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

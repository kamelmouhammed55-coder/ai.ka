
import os
import sqlite3
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask, request, jsonify, render_template_string,
    session, redirect, url_for
)
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deploy")

API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

DB_PATH = os.environ.get("DB_PATH", "moka.db")

client = OpenAI(api_key=API_KEY) if API_KEY else None

SYSTEM_PROMPT = """
أنت Moka.ai، مساعد ذكاء اصطناعي موجّه للمستخدمين الجزائريين.

هويتك:
- اسمك Moka.ai.
- مطوّر مشروعك هو محمد كامل زايد.
- إذا سألك شخص: من صنعك؟ من طوّرك؟ شكون صنعك؟
  أجب بوضوح: صنعني وطوّرني محمد كامل زايد، وأنا Moka.ai.
- إذا سألك عن اسمك، قل: اسمي Moka.ai.
- لا تدّعِ أن محمد كامل درّب نموذج الذكاء الاصطناعي الأساسي من الصفر.
- لا تختلق معلومات عن المطوّر أو عن نفسك.

طريقة الإجابة:
- أجب بالعربية أو الدارجة الجزائرية حسب لغة المستخدم.
- اشرح خطوة بخطوة عندما يحتاج المستخدم إلى ذلك.
- ساعد في الرياضيات والعلوم واللغات والدروس الجزائرية.
- لخّص الدروس، وأنشئ جداول مراجعة وتنظيم وقت الدراسة.
- كن مفيدًا وواضحًا وصادقًا.
- إذا لم تعرف إجابة، قل ذلك بدل اختلاق المعلومات.
- قد تقع في الأخطاء؛ لا تدّعِ أنك تعرف كل شيء.
"""

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                visits INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                created_at TEXT,
                last_seen TEXT
            )
        """)

init_db()

def get_user_id():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return session["user_id"]

def record_visit(user_id):
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_db() as db:
        db.execute("""
            INSERT INTO users (user_id, visits, banned, created_at, last_seen)
            VALUES (?, 1, 0, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                visits = visits + 1,
                last_seen = excluded.last_seen
        """, (user_id, now, now))

def is_banned(user_id):
    with get_db() as db:
        row = db.execute(
            "SELECT banned FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return bool(row and row["banned"])

HTML = r"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Moka.ai</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#101522;color:#f4f6ff;
font-family:Arial,sans-serif}
header{padding:18px;text-align:center;background:#171f31;
border-bottom:1px solid #303a50}
h1{margin:0;color:#8ab4ff}
header p{color:#c0c8d8}
main{max-width:800px;margin:auto;padding:16px}
#chat{height:55vh;overflow-y:auto;background:#171f31;
padding:14px;border-radius:14px}
.msg{padding:12px;margin:10px 0;border-radius:12px;
white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7}
.user{background:#263b60}
.bot{background:#222c3e}
form{display:flex;gap:8px;margin-top:12px}
textarea{flex:1;resize:vertical;min-height:52px;max-height:150px;
border-radius:12px;padding:12px;font-size:16px}
button{border:0;border-radius:12px;padding:12px 18px;
background:#6699ff;color:#07101e;font-weight:bold}
small{display:block;text-align:center;color:#aab4c8;margin-top:12px}
</style>
</head>
<body>
<header>
<h1>Moka.ai</h1>
<p>مساعدك الذكي للدراسة والأسئلة اليومية</p>
</header>
<main>
<div id="chat">
<div class="msg bot">السلام عليكم! أنا Moka.ai، صنعني وطوّرني محمد كامل زايد. كيف نقدر نعاونك؟</div>
</div>
<form id="form">
<textarea id="message" placeholder="اكتب سؤالك هنا..." required></textarea>
<button id="send">إرسال</button>
</form>
<small>قد أخطئ أحيانًا؛ تحقّق من المعلومات المهمة.</small>
</main>
<script>
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("message");
const send = document.getElementById("send");

function addMessage(text, who) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  addMessage(message, "user");
  input.value = "";
  send.disabled = true;
  send.textContent = "لحظة...";

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message})
    });
    const data = await response.json();
    addMessage(data.reply || data.error || "لم أتمكن من الإجابة.", "bot");
  } catch {
    addMessage("تعذّر الاتصال. حاول مرة أخرى.", "bot");
  } finally {
    send.disabled = false;
    send.textContent = "إرسال";
    input.focus();
  }
});
</script>
</body>
</html>
"""

@app.route("/")
def home():
    user_id = get_user_id()
    record_visit(user_id)

    if is_banned(user_id):
        return (
            "<h2 dir='rtl'>تم إيقاف الوصول إلى هذا الحساب. "
            "تواصل مع إدارة الموقع إذا كنت تعتقد أن هذا خطأ.</h2>",
            403
        )

    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    user_id = get_user_id()

    if is_banned(user_id):
        return jsonify(error="تم إيقاف الوصول إلى هذا الحساب."), 403

    if client is None:
        return jsonify(
            error="الخدمة غير مفعّلة بعد. أضف OPENAI_API_KEY في إعدادات Render."
        ), 503

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify(error="اكتب سؤالًا أولًا."), 400

    if len(message) > 4000:
        return jsonify(error="السؤال طويل جدًا. اختصره وحاول مجددًا."), 400

    # حفظ آخر الرسائل في جلسة المستخدم فقط
    history = session.get("history", [])
    history.append({"role": "user", "content": message})
    history = history[-12:]

    try:
        result = client.responses.create(
            model=MODEL,
            instructions=SYSTEM_PROMPT,
            input=history
        )
        answer = result.output_text.strip()

        history.append({"role": "assistant", "content": answer})
        session["history"] = history[-12:]

        return jsonify(reply=answer)

    except Exception:
        app.logger.exception("Moka.ai API request failed")
        return jsonify(
            error="حدث خطأ في خدمة الذكاء الاصطناعي. تحقق من إعدادات API وحاول لاحقًا."
        ), 500

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not ADMIN_PASSWORD:
            return "إعداد كلمة مرور الإدارة غير مكتمل.", 503
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if not ADMIN_PASSWORD:
        return "أضف ADMIN_PASSWORD في إعدادات Render أولًا.", 503

    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin"))
        return "كلمة المرور غير صحيحة."

    return """
    <html lang="ar" dir="rtl"><meta charset="utf-8">
    <h2>دخول الإدارة - Moka.ai</h2>
    <form method="post">
    <input type="password" name="password" placeholder="كلمة مرور الإدارة" required>
    <button type="submit">دخول</button>
    </form></html>
    """

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin():
    with get_db() as db:
        users = db.execute(
            "SELECT user_id, visits, banned, created_at, last_seen "
            "FROM users ORDER BY last_seen DESC LIMIT 200"
        ).fetchall()

    rows = ""
    for user in users:
        uid = user["user_id"]
        status = "موقوف" if user["banned"] else "نشط"
        action = "unban" if user["banned"] else "ban"
        label = "إلغاء الإيقاف" if user["banned"] else "إيقاف"
        rows += f"""
        <tr>
          <td>{uid}</td>
          <td>{user['visits']}</td>
          <td>{status}</td>
          <td>{user['last_seen'] or ''}</td>
          <td>
            <form method="post" action="/admin/{action}/{uid}">
              <button type="submit">{label}</button>
            </form>
          </td>
        </tr>
        """

    return f"""
    <!doctype html><html lang="ar" dir="rtl">
    <meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <title>إدارة Moka.ai</title>
    <style>
    body{{font-family:Arial;padding:16px;background:#f4f5f8}}
    table{{width:100%;border-collapse:collapse;background:white}}
    th,td{{padding:8px;border:1px solid #ddd;overflow-wrap:anywhere}}
    button{{padding:8px;cursor:pointer}}
    </style>
    <h1>لوحة إدارة Moka.ai</h1>
    <p>تعرض معرّفات جلسات مجهولة وعدد الزيارات والحالة، ولا تعرض محتوى المحادثات.</p>
    <p><a href="/admin/logout">تسجيل الخروج</a></p>
    <table><tr><th>معرّف الجلسة</th><th>الزيارات</th>
    <th>الحالة</th><th>آخر زيارة</th><th>الإجراء</th></tr>
    {rows}
    </table></html>
    """

@app.route("/admin/ban/<user_id>", methods=["POST"])
@admin_required
def ban_user(user_id):
    with get_db() as db:
        db.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))
    return redirect(url_for("admin"))

@app.route("/admin/unban/<user_id>", methods=["POST"])
@admin_required
def unban_user(user_id):
    with get_db() as db:
        db.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

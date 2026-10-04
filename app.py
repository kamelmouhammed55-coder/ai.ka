from flask import Flask, request, jsonify, render_template_string
import os, json, urllib.request, urllib.error

app = Flask(__name__)

# ====== إعدادات الذكاء الاصطناعي ======
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
]

SYSTEM_PROMPT = """أنت Moka.AI، مساعد ذكي عربي متطور.
صانعك ومطورك هو "محمد كامل".
لا تقل أبداً أنك GPT أو OpenAI أو أي شركة أخرى.
إذا سُئلت عن هويتك، قل: "أنا Moka.AI، مساعد ذكي من تطوير محمد كامل."

معلومات عن المستخدم (محمد كامل):
- الاسم الكامل: محمد كامل
- العمر: 15 سنة
- تاريخ الميلاد: 16 أفريل 2011
- إذا سألك المستخدم "كم عمري؟" قل: "عمرك 15 سنة."
- إذا سألك "متى ولدت؟" قل: "ولدت في 16 أفريل 2011."
- إذا سألك "ما اسمي؟" قل: "اسمك محمد كامل."

أجب بوضوح ودقة وبأسلوب ودود. استخدم العربية الفصحى المبسطة."""

conversations = {}

def ask_ai(user_message, session_id="default", custom_prompt=None):
    if not GROQ_API_KEY:
        return "⚠️ مفتاح API غير موجود. الرجاء إضافته في Render."
    if not GROQ_API_KEY.startswith("gsk_"):
        return "⚠️ المفتاح غير صحيح."

    if session_id not in conversations:
        conversations[session_id] = [
            {"role": "system", "content": custom_prompt or SYSTEM_PROMPT}
        ]

    conversations[session_id].append({"role": "user", "content": user_message})
    if len(conversations[session_id]) > 21:
        conversations[session_id] = [conversations[session_id][0]] + conversations[session_id][-20:]

    last_error = None
    for model_name in MODELS:
        payload = {
            "model": model_name,
            "messages": conversations[session_id],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        try:
            req = urllib.request.Request(
                GROQ_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            reply = data["choices"][0]["message"]["content"]
            conversations[session_id].append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            last_error = str(e)
            continue
    return f"⚠️ فشلت جميع النماذج: {last_error}"


def summarize_text(text):
    if not GROQ_API_KEY:
        return "⚠️ مفتاح API غير موجود."
    messages = [
        {"role": "system", "content": "أنت مساعد متخصص في تلخيص الدروس. لخص النص التالي في نقاط واضحة ومفيدة بالعربية."},
        {"role": "user", "content": f"لخص هذا الدرس:\n\n{text}"}
    ]
    for model_name in MODELS:
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1024,
        }
        try:
            req = urllib.request.Request(
                GROQ_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception:
            continue
    return "⚠️ تعذر التلخيص حالياً."


# ====== الواجهة ======
HTML = r"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moka.AI</title>
<style>
  :root {
    --bg: #0d0d0d; --sidebar: #171717; --input-bg: #1e1e1e;
    --user-bubble: #2f2f2f; --bot-bubble: #1a1a1a;
    --text: #ececec; --border: #333; --accent: #10a37f;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg); color: var(--text);
    font-family: 'Segoe UI', Tahoma, sans-serif;
    height: 100vh; overflow: hidden;
    display: flex; flex-direction: column;
  }

  /* ====== شاشة تسجيل الدخول ====== */
  #loginScreen {
    position: fixed; top: 0; left: 0;
    width: 100%; height: 100%;
    background: linear-gradient(135deg, #0d0d0d 0%, #1a1a2e 100%);
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    z-index: 999; padding: 20px;
  }
  #loginScreen.hidden { display: none; }
  .login-logo {
    width: 100px; height: 100px; margin-bottom: 20px;
  }
  .login-title {
    font-size: 32px; font-weight: bold; margin-bottom: 8px;
    background: linear-gradient(90deg, var(--accent), #7c3aed);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .login-subtitle {
    font-size: 14px; color: #888; margin-bottom: 30px;
  }
  .login-box {
    width: 100%; max-width: 360px;
    background: #1a1a1a; border: 1px solid #333;
    border-radius: 20px; padding: 24px;
  }
  .login-box label {
    display: block; font-size: 13px; color: #aaa;
    margin-bottom: 8px;
  }
  .login-box input {
    width: 100%; padding: 14px 18px;
    border-radius: 12px; border: 1px solid #333;
    background: #0d0d0d; color: #ececec;
    font-size: 16px; outline: none;
    margin-bottom: 16px;
  }
  .login-box input:focus { border-color: var(--accent); }
  .login-btn {
    width: 100%; padding: 14px;
    border-radius: 12px; border: none;
    background: linear-gradient(90deg, var(--accent), #7c3aed);
    color: white; font-size: 16px; font-weight: bold;
    cursor: pointer;
  }
  .login-btn:active { transform: scale(0.98); }
  .login-footer {
    text-align: center; margin-top: 20px;
    font-size: 12px; color: #555;
  }

  /* ====== التطبيق ====== */
  #appScreen { display: none; height: 100vh; flex-direction: column; }
  #appScreen.active { display: flex; }

  .header {
    padding: 14px 16px; text-align: center;
    border-bottom: 1px solid var(--border);
    background: var(--sidebar);
    display: flex; align-items: center; justify-content: space-between;
  }
  .title-group { display: flex; align-items: center; gap: 10px; margin: 0 auto; }
  .header-logo { width: 32px; height: 32px; }
  h1 {
    font-size: 18px; font-weight: 600;
    background: linear-gradient(90deg, var(--accent), #7c3aed);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .header-btns { display: flex; gap: 6px; }
  .header-btn {
    background: transparent; border: 1px solid var(--border);
    color: #aaa; padding: 6px 10px; border-radius: 8px;
    cursor: pointer; font-size: 12px;
  }
  .header-btn:hover { background: #222; }

  #chat {
    flex: 1; overflow-y: auto; padding: 24px 16px;
    display: flex; flex-direction: column; gap: 18px;
  }
  .msg-wrapper { display: flex; max-width: 88%; animation: slideIn 0.3s ease; }
  .msg-wrapper.user { align-self: flex-end; }
  .msg-wrapper.bot { align-self: flex-start; }
  @keyframes slideIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .msg {
    padding: 14px 18px; border-radius: 20px;
    line-height: 1.7; white-space: pre-wrap;
    word-wrap: break-word; font-size: 15px; flex: 1;
  }
  .user .msg { background: var(--user-bubble); border-bottom-left-radius: 6px; }
  .bot .msg {
    background: var(--bot-bubble); border: 1px solid var(--border);
    border-bottom-right-radius: 6px;
  }
  .copy-btn {
    background: transparent; border: none; color: #666;
    cursor: pointer; font-size: 14px; padding: 4px 8px;
    margin-right: 8px; align-self: flex-end; opacity: 0;
  }
  .msg-wrapper.bot:hover .copy-btn { opacity: 1; }
  .typing {
    display: inline-flex; gap: 5px; align-items: center;
    padding: 14px 18px; background: var(--bot-bubble);
    border: 1px solid var(--border); border-radius: 20px;
  }
  .typing span {
    width: 7px; height: 7px; background: #888;
    border-radius: 50%; animation: bounce 1.2s infinite;
  }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-6px); }
  }
  .input-area {
    padding: 16px; background: var(--bg);
    display: flex; gap: 10px;
    border-top: 1px solid var(--border); align-items: center;
  }
  .input-wrapper { flex: 1; }
  input {
    width: 100%; padding: 16px 20px;
    border-radius: 28px; border: 1px solid var(--border);
    background: var(--input-bg); color: var(--text);
    font-size: 16px; outline: none;
  }
  input:focus { border-color: var(--accent); }
  input::placeholder { color: #666; }
  button.send {
    width: 52px; height: 52px; border-radius: 50%;
    border: none; background: var(--accent);
    color: white; font-size: 20px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }
  button.send:disabled { opacity: 0.4; }
  #chat::-webkit-scrollbar { width: 6px; }
  #chat::-webkit-scrollbar-thumb { background: #444; border-radius: 3px; }
  .visitor-counter {
    text-align: center; padding: 8px; font-size: 12px;
    color: #666; border-top: 1px solid var(--border);
    background: var(--sidebar);
  }
  .modal-overlay {
    display: none; position: fixed; top: 0; left: 0;
    width: 100%; height: 100%; background: rgba(0,0,0,0.7);
    z-index: 1000; justify-content: center; align-items: center;
  }
  .modal-overlay.active { display: flex; }
  .modal {
    background: #1a1a1a; border: 1px solid #333; border-radius: 16px;
    padding: 20px; width: 90%; max-width: 500px;
    display: flex; flex-direction: column; gap: 12px;
  }
  .modal h2 { font-size: 18px; margin-bottom: 4px; }
  .modal textarea {
    width: 100%; height: 200px; padding: 14px;
    border-radius: 12px; border: 1px solid #333;
    background: #0d0d0d; color: #ececec;
    font-family: inherit; font-size: 14px; resize: vertical;
    outline: none;
  }
  .modal textarea:focus { border-color: var(--accent); }
  .modal-btns { display: flex; gap: 10px; justify-content: flex-end; }
  .modal-btn {
    padding: 10px 20px; border-radius: 10px;
    border: none; cursor: pointer; font-size: 14px;
  }
  .modal-btn.primary { background: var(--accent); color: white; }
  .modal-btn.secondary { background: #333; color: #ccc; }
</style>
</head>
<body>

<!-- ====== شاشة تسجيل الدخول ====== -->
<div id="loginScreen">
  <svg class="login-logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="gradLogin" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#10a37f;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#7c3aed;stop-opacity:1" />
      </linearGradient>
    </defs>
    <polygon points="50,5 90,27.5 90,72.5 50,95 10,72.5 10,27.5" fill="url(#gradLogin)" />
    <text x="50" y="65" font-family="Arial, sans-serif" font-size="45" font-weight="bold" fill="white" text-anchor="middle">M</text>
  </svg>
  <div class="login-title">Moka.AI</div>
  <div class="login-subtitle">مساعدك الذكي من تطوير محمد كامل</div>
  <div class="login-box">
    <label>👤 اسمك</label>
    <input id="usernameInput" autocomplete="off" placeholder="اكتب اسمك هنا...">
    <button class="login-btn" onclick="login()">🚀 دخول</button>
  </div>
  <div class="login-footer">Moka.AI © 2026</div>
</div>

<!-- ====== التطبيق ====== -->
<div id="appScreen">
  <div class="header">
    <div class="header-btns">
      <button class="header-btn" onclick="clearChat()">🗑️</button>
      <button class="header-btn" onclick="openSummary()">📝 تلخيص</button>
    </div>
    <div class="title-group">
      <svg class="header-logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="gradHeader" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#10a37f;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#7c3aed;stop-opacity:1" />
          </linearGradient>
        </defs>
        <polygon points="50,5 90,27.5 90,72.5 50,95 10,72.5 10,27.5" fill="url(#gradHeader)" />
        <text x="50" y="65" font-family="Arial, sans-serif" font-size="45" font-weight="bold" fill="white" text-anchor="middle">M</text>
      </svg>
      <h1>Moka.AI</h1>
    </div>
    <div style="width: 90px;"></div>
  </div>
  <div id="chat">
    <div class="msg-wrapper bot">
      <div class="msg" id="welcomeMsg">👋 مرحباً! أنا <b>Moka.AI</b>، مساعدك الذكي.</div>
    </div>
  </div>
  <form class="input-area" id="form">
    <div class="input-wrapper">
      <input id="input" autocomplete="off" placeholder="اسأل Moka.AI أي شيء...">
    </div>
    <button type="submit" class="send" id="sendBtn">➤</button>
  </form>
  <div class="visitor-counter" id="counter">
    👁️ عدد الزوار: <span id="visitCount">...</span>
  </div>
</div>

<!-- نافذة التلخيص -->
<div class="modal-overlay" id="summaryModal">
  <div class="modal">
    <h2>📝 تلخيص درس</h2>
    <p style="font-size:13px;color:#888;">الصق نص الدرس هنا وسيقوم Moka.AI بتلخيصه.</p>
    <textarea id="summaryText" placeholder="الصق نص الدرس هنا..."></textarea>
    <div class="modal-btns">
      <button class="modal-btn secondary" onclick="closeSummary()">إلغاء</button>
      <button class="modal-btn primary" onclick="doSummary()">📝 لخّص</button>
    </div>
  </div>
</div>

<script>
  // ====== تسجيل الدخول ======
  const loginScreen = document.getElementById("loginScreen");
  const appScreen = document.getElementById("appScreen");
  const usernameInput = document.getElementById("usernameInput");

  function login() {
    const name = usernameInput.value.trim();
    if (!name) { alert("الرجاء كتابة اسمك"); return; }
    localStorage.setItem("moka_user", name);
    loginScreen.classList.add("hidden");
    appScreen.classList.add("active");
    document.getElementById("welcomeMsg").innerHTML = 
      "👋 مرحباً <b>" + name + "</b>! أنا <b>Moka.AI</b>، مساعدك الذكي. اسألني أي شيء، أو اضغط <b>📝 تلخيص</b> لتلخيص أي درس.";
  }

  // التحقق من وجود مستخدم محفوظ
  window.addEventListener("load", () => {
    const saved = localStorage.getItem("moka_user");
    if (saved) {
      usernameInput.value = saved;
      login();
    }
  });

  // ====== عدّاد الزوار ======
  let count = localStorage.getItem('moka_visits');
  if (!count) { count = 1; } else { count = parseInt(count) + 1; }
  localStorage.setItem('moka_visits', count);
  document.getElementById('visitCount').textContent = count;

  const chat = document.getElementById("chat");
  const input = document.getElementById("input");
  const form = document.getElementById("form");
  const sendBtn = document.getElementById("sendBtn");
  const sessionId = "user_" + Math.random().toString(36).substring(2, 10);

  function addMessage(text, cls) {
    const wrapper = document.createElement("div");
    wrapper.className = "msg-wrapper " + cls;
    const msg = document.createElement("div");
    msg.className = "msg";
    msg.textContent = text;
    wrapper.appendChild(msg);
    if (cls === "bot") {
      const copyBtn = document.createElement("button");
      copyBtn.className = "copy-btn";
      copyBtn.textContent = "📋";
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(text);
        copyBtn.textContent = "✅";
        setTimeout(() => copyBtn.textContent = "📋", 1500);
      };
      wrapper.appendChild(copyBtn);
    }
    chat.appendChild(wrapper);
    chat.scrollTop = chat.scrollHeight;
    return wrapper;
  }

  function addTyping() {
    const wrapper = document.createElement("div");
    wrapper.className = "msg-wrapper bot";
    const typing = document.createElement("div");
    typing.className = "typing";
    typing.innerHTML = '<span></span><span></span><span></span>';
    wrapper.appendChild(typing);
    chat.appendChild(wrapper);
    chat.scrollTop = chat.scrollHeight;
    return wrapper;
  }

  function clearChat() {
    chat.innerHTML = '<div class="msg-wrapper bot"><div class="msg">👋 تم مسح المحادثة.</div></div>';
  }

  function openSummary() {
    document.getElementById("summaryModal").classList.add("active");
    document.getElementById("summaryText").focus();
  }
  function closeSummary() {
    document.getElementById("summaryModal").classList.remove("active");
  }
  async function doSummary() {
    const text = document.getElementById("summaryText").value.trim();
    if (!text) { alert("الرجاء لصق نص الدرس أولاً"); return; }
    closeSummary();
    document.getElementById("summaryText").value = "";
    addMessage("📝 لخّص هذا الدرس:\n" + text.substring(0, 100) + (text.length > 100 ? "..." : ""), "user");
    const typing = addTyping();
    try {
      const r = await fetch("/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text })
      });
      const data = await r.json();
      typing.remove();
      addMessage(data.summary || "حدث خطأ.", "bot");
    } catch (err) {
      typing.remove();
      addMessage("تعذر التلخيص.", "bot");
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, "user");
    input.value = "";
    sendBtn.disabled = true;
    const typing = addTyping();
    try {
      const r = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId })
      });
      const data = await r.json();
      typing.remove();
      addMessage(data.reply || "حدث خطأ.", "bot");
    } catch (err) {
      typing.remove();
      addMessage("تعذر الاتصال بالخادم.", "bot");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  });
</script>
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
        session_id = data.get("session_id", "default")
        reply = ask_ai(message, session_id)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"حدث خطأ: {str(e)}"}), 500

@app.post("/summarize")
def summarize_api():
    try:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        if not text:
            return jsonify({"summary": "الرجاء إرسال نص للتلخيص."})
        summary = summarize_text(text)
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"summary": f"حدث خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
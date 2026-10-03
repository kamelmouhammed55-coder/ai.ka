from flask import Flask, request, jsonify, render_template_string
import os, json, urllib.request

app = Flask(__name__)

# ====== إعدادات الذكاء الاصطناعي ======
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

# ذاكرة المحادثة
conversations = {}

def ask_ai(user_message, session_id="default"):
    if not GROQ_API_KEY:
        return "⚠️ لم يتم إعداد مفتاح API. يرجى إضافته في Render."

    if session_id not in conversations:
        conversations[session_id] = [
            {"role": "system", "content": "أنت Moka.AI، مساعد ذكي متطور. تجيب باللغة العربية بوضوح وإيجاز. يمكنك حل المسائل الرياضية المعقدة، الإجابة عن الأسئلة العامة، البرمجة، الترجمة، وكل المواضيع. ردودك دقيقة ومفيدة."}
        ]

    conversations[session_id].append({"role": "user", "content": user_message})

    if len(conversations[session_id]) > 21:
        conversations[session_id] = [conversations[session_id][0]] + conversations[session_id][-20:]

    payload = {
        "model": MODEL,
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
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        reply = data["choices"][0]["message"]["content"]
        conversations[session_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"⚠️ حدث خطأ: {str(e)}"

# ====== الواجهة ======
HTML = r"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moka.AI - مساعدك الذكي</title>
<style>
  :root {
    --bg: #0d0d0d;
    --sidebar: #171717;
    --input-bg: #1e1e1e;
    --user-bubble: #2f2f2f;
    --bot-bubble: #1a1a1a;
    --text: #ececec;
    --border: #333;
    --accent: #10a37f;
    --accent-hover: #0d8a6a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', Tahoma, sans-serif;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .header {
    padding: 16px;
    text-align: center;
    border-bottom: 1px solid var(--border);
    background: var(--sidebar);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }
  .header .logo {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, var(--accent), #7c3aed);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
  }
  .header h1 {
    font-size: 18px;
    font-weight: 600;
    background: linear-gradient(90deg, var(--accent), #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  #chat {
    flex: 1;
    overflow-y: auto;
    padding: 24px 16px;
    display: flex;
    flex-direction: column;
    gap: 18px;
    scroll-behavior: smooth;
  }
  .msg {
    max-width: 88%;
    padding: 14px 18px;
    border-radius: 20px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-wrap: break-word;
    animation: slideIn 0.3s ease;
    font-size: 15px;
  }
  @keyframes slideIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .user {
    align-self: flex-end;
    background: var(--user-bubble);
    border-bottom-left-radius: 6px;
  }
  .bot {
    align-self: flex-start;
    background: var(--bot-bubble);
    border: 1px solid var(--border);
    border-bottom-right-radius: 6px;
  }
  .typing {
    display: inline-flex;
    gap: 5px;
    align-items: center;
    color: #888;
  }
  .typing span {
    width: 7px;
    height: 7px;
    background: #888;
    border-radius: 50%;
    animation: bounce 1.2s infinite;
  }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-6px); }
  }
  .input-area {
    padding: 16px;
    background: var(--bg);
    display: flex;
    gap: 10px;
    border-top: 1px solid var(--border);
    align-items: center;
  }
  .input-wrapper {
    flex: 1;
    position: relative;
  }
  input {
    width: 100%;
    padding: 16px 20px;
    border-radius: 28px;
    border: 1px solid var(--border);
    background: var(--input-bg);
    color: var(--text);
    font-size: 16px;
    outline: none;
    transition: border-color 0.2s;
  }
  input:focus {
    border-color: var(--accent);
  }
  input::placeholder {
    color: #666;
  }
  button {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    border: none;
    background: var(--accent);
    color: white;
    font-size: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    flex-shrink: 0;
  }
  button:hover { background: var(--accent-hover); }
  button:active { transform: scale(0.92); }
  button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  #chat::-webkit-scrollbar { width: 6px; }
  #chat::-webkit-scrollbar-track { background: transparent; }
  #chat::-webkit-scrollbar-thumb { background: #444; border-radius: 3px; }
  .welcome {
    text-align: center;
    color: #888;
    margin: auto;
    padding: 20px;
  }
  .welcome h2 {
    font-size: 28px;
    margin-bottom: 10px;
    background: linear-gradient(90deg, var(--accent), #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .welcome p { font-size: 14px; line-height: 1.8; }
</style>
</head>
<body>
<div class="header">
  <div class="logo">🤖</div>
  <h1>Moka.AI</h1>
</div>
<div id="chat">
  <div class="msg bot">👋 مرحباً! أنا <b>Moka.AI</b>، مساعدك الذكي. يمكنني الإجابة على أي سؤال، حل المسائل الرياضية، البرمجة، الترجمة، وأكثر. كيف يمكنني مساعدتك؟</div>
</div>
<form class="input-area" id="form">
  <div class="input-wrapper">
    <input id="input" autocomplete="off" placeholder="اسأل Moka.AI أي شيء...">
  </div>
  <button type="submit" id="sendBtn">➤</button>
</form>

<script>
  const chat = document.getElementById("chat");
  const input = document.getElementById("input");
  const form = document.getElementById("form");
  const sendBtn = document.getElementById("sendBtn");
  const sessionId = "user_" + Math.random().toString(36).substring(2, 10);

  function addMessage(text, cls) {
    const d = document.createElement("div");
    d.className = "msg " + cls;
    d.textContent = text;
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
    return d;
  }

  function addTyping() {
    const d = document.createElement("div");
    d.className = "msg bot typing";
    d.innerHTML = '<span></span><span></span><span></span>';
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
    return d;
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

<!-- كود تتبع StatCounter -->
<script type="text/javascript">
var sc_project=13358120; 
var sc_invisible=1; 
var sc_security="83ce6869"; 
</script>
<script type="text/javascript"
src="https://www.statcounter.com/counter/counter.js" async></script>
<noscript><div class="statcounter"><a title="Web Analytics" href="https://statcounter.com/" target="_blank"><img class="statcounter" src="https://c.statcounter.com/13358120/0/83ce6869/1/" alt="Web Analytics" referrerPolicy="no-referrer-when-downgrade"></a></div></noscript>

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
إضافة البحث في ويكيبيديا 
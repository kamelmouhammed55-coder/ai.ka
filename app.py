from flask import Flask, request, jsonify, render_template_string
import os, json, urllib.request, urllib.error

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
]

conversations = {}

def ask_ai(user_message, session_id="default"):
    if not GROQ_API_KEY:
        return "⚠️ مفتاح API غير موجود."
    if not GROQ_API_KEY.startswith("gsk_"):
        return "⚠️ المفتاح غير صحيح."

    if session_id not in conversations:
        conversations[session_id] = [
            {"role": "system", "content": "أنت Moka.AI، مساعد ذكي عربي متطور. أجب بوضوح ودقة وبأسلوب ودود."}
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


HTML = r"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moka.AI</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0d0d0d; color: #ececec;
    font-family: Tahoma, sans-serif;
    height: 100vh; display: flex; flex-direction: column;
    overflow: hidden;
  }
  .header {
    padding: 14px; text-align: center;
    border-bottom: 1px solid #333; background: #171717;
    display: flex; justify-content: space-between; align-items: center;
  }
  .header h1 {
    font-size: 18px; margin: 0 auto;
    background: linear-gradient(90deg, #10a37f, #7c3aed);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .clear-btn {
    background: transparent; border: 1px solid #333;
    color: #aaa; padding: 6px 10px; border-radius: 8px;
    cursor: pointer; font-size: 12px;
  }
  #chat {
    flex: 1; overflow-y: auto; padding: 20px 16px;
    display: flex; flex-direction: column; gap: 16px;
  }
  .msg {
    max-width: 85%; padding: 14px 18px;
    border-radius: 20px; line-height: 1.7;
    white-space: pre-wrap; font-size: 15px;
  }
  .user { align-self: flex-end; background: #2f2f2f; border-bottom-left-radius: 6px; }
  .bot { align-self: flex-start; background: #1a1a1a; border: 1px solid #333; border-bottom-right-radius: 6px; }
  .typing { display: flex; gap: 5px; padding: 14px 18px; background: #1a1a1a; border: 1px solid #333; border-radius: 20px; }
  .typing span { width: 7px; height: 7px; background: #888; border-radius: 50%; animation: bounce 1.2s infinite; }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }
  .input-area {
    padding: 16px; display: flex; gap: 10px;
    border-top: 1px solid #333; background: #0d0d0d;
  }
  input {
    flex: 1; padding: 16px 20px; border-radius: 28px;
    border: 1px solid #333; background: #1e1e1e;
    color: #ececec; font-size: 16px; outline: none;
  }
  input:focus { border-color: #10a37f; }
  button.send {
    width: 52px; height: 52px; border-radius: 50%;
    border: none; background: #10a37f; color: white;
    font-size: 20px; cursor: pointer; flex-shrink: 0;
  }
  button.send:disabled { opacity: 0.4; }
  .visitor-counter {
    text-align: center; padding: 8px; font-size: 12px;
    color: #666; border-top: 1px solid #333; background: #171717;
  }
</style>
</head>
<body>
<div class="header">
  <button class="clear-btn" onclick="clearChat()">🗑️ مسح</button>
  <h1>Moka.AI</h1>
  <div style="width: 60px;"></div>
</div>
<div id="chat">
  <div class="msg bot">👋 مرحباً! أنا <b>Moka.AI</b>، مساعدك الذكي. اسألني أي شيء!</div>
</div>
<form class="input-area" id="form">
  <input id="input" autocomplete="off" placeholder="اسأل Moka.AI أي شيء...">
  <button type="submit" class="send" id="sendBtn">➤</button>
</form>
<div class="visitor-counter" id="counter">
  👁️ عدد الزوار: <span id="visitCount">...</span>
</div>

<script>
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
    const d = document.createElement("div");
    d.className = "msg " + cls;
    d.textContent = text;
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
  }

  function addTyping() {
    const d = document.createElement("div");
    d.className = "typing";
    d.innerHTML = '<span></span><span></span><span></span>';
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
    return d;
  }

  function clearChat() {
    chat.innerHTML = '<div class="msg bot">👋 تم مسح المحادثة.</div>';
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
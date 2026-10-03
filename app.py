from flask import Flask, request, jsonify, render_template_string
import os, json, urllib.request, urllib.error

app = Flask(__name__)

# ====== إعدادات الذكاء الاصطناعي ======
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

conversations = {}

def ask_ai(user_message, session_id="default"):
    if not GROQ_API_KEY:
        return "⚠️ مفتاح API غير موجود. الرجاء إضافته في Render."
    if not GROQ_API_KEY.startswith("gsk_"):
        return "⚠️ المفتاح غير صحيح. يجب أن يبدأ بـ gsk_."

    if session_id not in conversations:
        conversations[session_id] = [
            {"role": "system", "content": "أنت Moka.AI، مساعد ذكي عربي متطور. أجب بوضوح ودقة وبأسلوب ودود. يمكنك حل المسائل الرياضية، البرمجة، الترجمة، وكل المواضيع."}
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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "ar,en;q=0.9",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        reply = data["choices"][0]["message"]["content"]
        conversations[session_id].append({"role": "assistant", "content": reply})
        return reply
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        return f"⚠️ خطأ {e.code}:\n{error_body}"
    except Exception as e:
        return f"⚠️ خطأ: {str(e)}"


HTML = r"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moka.AI - مساعدك الذكي</title>
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
  .header {
    padding: 14px 16px; text-align: center;
    border-bottom: 1px solid var(--border);
    background: var(--sidebar);
    display: flex; align-items: center; justify-content: space-between;
  }
  .title-group { display: flex; align-items: center; gap: 10px; margin: 0 auto; }
  .logo {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, var(--accent), #7c3aed);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  h1 {
    font-size: 18px; font-weight: 600;
    background: linear-gradient(90deg, var(--accent), #7c3aed);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .clear-btn {
    background: transparent; border: 1px solid var(--border);
    color: #aaa; padding: 6px 10px; border-radius: 8px;
    cursor: pointer; font-size: 12px;
  }
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
  button.send:active { transform: scale(0.92); }
  button.send:disabled { opacity: 0.4; }
  #chat::-webkit-scrollbar { width: 6px; }
  #chat::-webkit-scrollbar-thumb { background: #444; border-radius: 3px; }
</style>
</head>
<body>
<div class="header">
  <button class="clear-btn" onclick="clearChat()">🗑️ مسح</button>
  <div class="title-group">
    <div class="logo">🤖</div>
    <h1>Moka.AI</h1>
  </div>
  <div style="width: 60px;"></div>
</div>
<div id="chat">
  <div class="msg-wrapper bot">
    <div class="msg">👋 مرحباً! أنا <b>Moka.AI</b>، مساعدك الذكي. اسألني أي شيء!</div>
  </div>
</div>
<form class="input-area" id="form">
  <div class="input-wrapper">
    <input id="input" autocomplete="off" placeholder="اسأل Moka.AI أي شيء...">
  </div>
  <button type="submit" class="send" id="sendBtn">➤</button>
</form>

<script>
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
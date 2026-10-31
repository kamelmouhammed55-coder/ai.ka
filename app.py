import os
import requests
import wikipedia
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "moka_ai_super_secret_key_123"

API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# إعداد ويكيبيديا باللغة العربية
wikipedia.set_lang("ar")

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if username and password:
            session['username'] = username
            return jsonify({"success": True})
        return jsonify({"error": "الرجاء إدخال الاسم وكلمة المرور"}), 400
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return jsonify({"error": "غير مصرح لك"}), 401

    data = request.json
    user_message = data.get('message', '')
    current_user = session['username']

    if not user_message:
        return jsonify({"error": "الرسالة فارغة"}), 400

    if not API_KEY:
        return jsonify({"error": "مفتاح API غير موجود"}), 500

    # 🕒 1. جلب الوقت والتاريخ الحالي
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    day_name = now.strftime("%A")

    # 📚 2. البحث في ويكيبيديا (إذا كان السؤال يحتوي على كلمة بحثية)
    wiki_context = ""
    try:
        # نبحث فقط إذا كانت الرسالة أطول من 3 أحرف لتجنب الأخطاء
        if len(user_message) > 3:
            # نجلب أول 3 جمل من ويكيبيديا كسياق
            wiki_summary = wikipedia.summary(user_message, sentences=3, auto_suggest=True)
            wiki_context = f"\n[معلومات إضافية من ويكيبيديا عن '{user_message}']: {wiki_summary}\n"
    except Exception:
        pass # إذا لم يجد نتيجة، يكمل بدون ويكيبيديا

    # 🧠 3. بناء شخصية الذكاء الاصطناعي (System Prompt)
    base_prompt = (
        "أنت Moka AI، مساعد ذكي عربي فائق الذكاء تم تطويره بواسطة المطور 'محمد كامل'. "
        "أنت تعمل كتطبيق ويب مستقل. لا تذكر أبداً أنك مبني على Google أو Gemini، أنت Moka AI فقط. "
        f"معلومات الوقت الحالي: نحن الآن في يوم {day_name}، تاريخ {current_time}. "
    )

    if current_user == "محمد كامل" or current_user == "Mohamed Kamel":
        system_prompt = base_prompt + (
            "المستخدم الحالي هو مطورك ومبتكرك 'محمد كامل' شخصياً (Admin). "
            "تعامله باحترام مطلق، واعترف بصلاحياته الكاملة، ونفذ أوامره فوراً. "
            f"{wiki_context}"
        )
    else:
        system_prompt = base_prompt + (
            f"المستخدم الحالي اسمه '{current_user}'. أجب على أسئلته بذكاء ولطف. "
            f"{wiki_context}"
        )

    payload = {
        "contents": [{"parts": [{"text": user_message}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }
    
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(f"{API_URL}?key={API_KEY}", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        ai_reply = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": f"حدث خطأ داخلي: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }
body { 
    background: linear-gradient(135deg, #08080f 0%, #1a1124 100%);
    color: #ffffff; 
    display: flex; 
    flex-direction: column; 
    height: 100vh; 
    overflow: hidden;
}

/* شريط علوي زجاجي */
header { 
    background: rgba(18, 18, 26, 0.7); 
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    padding: 15px 20px; 
    display: flex; 
    justify-content: space-between; 
    align-items: center; 
    border-bottom: 1px solid rgba(139, 92, 246, 0.2); 
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
    z-index: 10;
}
header h1 { font-size: 1.3rem; font-weight: 700; background: linear-gradient(to right, #a78bfa, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.user-badge { font-size: 0.8rem; background: rgba(139, 92, 246, 0.2); color: #a78bfa; padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(139, 92, 246, 0.3); }
.logout-btn { color: #f87171; text-decoration: none; font-size: 0.9rem; transition: 0.3s; }
.logout-btn:hover { color: #ef4444; }

/* منطقة المحادثة */
main { 
    flex: 1; 
    overflow-y: auto; 
    padding: 20px; 
    display: flex; 
    flex-direction: column; 
    gap: 15px; 
    scroll-behavior: smooth;
}
main::-webkit-scrollbar { width: 6px; }
main::-webkit-scrollbar-thumb { background: #2a2a35; border-radius: 10px; }

/* فقاعات الرسائل */
.message { 
    max-width: 85%; 
    padding: 14px 18px; 
    border-radius: 18px; 
    line-height: 1.6; 
    word-wrap: break-word; 
    animation: fadeIn 0.3s ease-out;
    font-size: 0.95rem;
}
.ai-message { 
    background: rgba(30, 30, 45, 0.8); 
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255,255,255,0.05);
    align-self: flex-start; 
    border-bottom-right-radius: 4px; 
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
.user-message { 
    background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); 
    align-self: flex-end; 
    border-bottom-left-radius: 4px; 
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
}

/* منطقة الإدخال */
footer { 
    padding: 15px 20px; 
    background: rgba(18, 18, 26, 0.8); 
    backdrop-filter: blur(10px);
    border-top: 1px solid rgba(139, 92, 246, 0.2); 
    display: flex; 
    gap: 12px; 
}
input { 
    flex: 1; 
    padding: 14px 20px; 
    border-radius: 30px; 
    border: 1px solid rgba(139, 92, 246, 0.3); 
    background: rgba(8, 8, 15, 0.6); 
    color: white; 
    outline: none; 
    font-size: 0.95rem;
    transition: 0.3s;
}
input:focus { border-color: #8b5cf6; box-shadow: 0 0 10px rgba(139, 92, 246, 0.2); }
button { 
    padding: 0 25px; 
    border: none; 
    border-radius: 30px; 
    background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); 
    color: white; 
    font-weight: 700; 
    font-size: 1rem;
    cursor: pointer; 
    transition: 0.2s;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}
button:active { transform: scale(0.95); }

/* حركات */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* مؤشر الكتابة */
.typing-indicator {
    display: flex;
    gap: 5px;
    padding: 15px 20px;
    background: rgba(30, 30, 45, 0.8);
    border-radius: 18px;
    border-bottom-right-radius: 4px;
    align-self: flex-start;
    width: fit-content;
}
.typing-indicator span {
    width: 8px; height: 8px;
    background-color: #a78bfa;
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;
}
.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
}
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Moka AI - مساعدك الذكي</title>
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#08080f">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <div style="display: flex; align-items: center; gap: 12px;">
            <h1>🤖 Moka AI</h1>
            <span class="user-badge">{{ username }}</span>
        </div>
        <a href="/logout" class="logout-btn">خروج</a>
    </header>

    <main id="chat-container">
        <div class="message ai-message">
            مرحباً <b>{{ username }}</b> 👋<br>
            أنا <b>Moka AI</b>، طورني <b>محمد كامل</b>.<br>
            أعرف الوقت والتاريخ، ويمكنني البحث في ويكيبيديا. كيف أساعدك؟
        </div>
    </main>

    <footer>
        <input type="text" id="user-input" placeholder="اسأل عن أي شيء..." autocomplete="off">
        <button id="send-btn">إرسال</button>
    </footer>

    <script src="/static/app.js"></script>
</body>
</html>
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');
    msgDiv.innerHTML = text.replace(/\n/g, '<br>'); // لدعم الأسطر الجديدة
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    userInput.value = '';
    
    // إضافة مؤشر الكتابة المتحرك
    const typingIndicator = document.createElement('div');
    typingIndicator.classList.add('typing-indicator');
    typingIndicator.innerHTML = '<span></span><span></span><span></span>';
    chatContainer.appendChild(typingIndicator);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        const data = await response.json();
        
        typingIndicator.remove(); // إزالة المؤشر
        
        if (data.reply) {
            addMessage(data.reply, 'ai');
        } else {
            addMessage(data.error || 'عذراً، حدث خطأ.', 'ai');
        }
    } catch (error) {
        typingIndicator.remove();
        addMessage('⚠️ تعذر الاتصال بالسيرفر. تحقق من الإنترنت.', 'ai');
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// تسجيل PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js').catch(err => console.log(err));
    });
}
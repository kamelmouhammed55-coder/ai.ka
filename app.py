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

    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    day_name = now.strftime("%A")

    wiki_context = ""
    try:
        if len(user_message) > 3:
            wiki_summary = wikipedia.summary(user_message, sentences=3, auto_suggest=True)
            wiki_context = f"\n[معلومات إضافية من ويكيبيديا عن '{user_message}']: {wiki_summary}\n"
    except Exception:
        pass

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

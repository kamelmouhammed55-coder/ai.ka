require('dotenv').config();
const express = require('express');
const session = require('express-session');
const axios = require('axios');
const wiki = require('wikipedia');
const path = require('path');

const app = express();

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static('static'));

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'templates'));

app.use(session({
    secret: 'moka_ai_super_secret_key_123',
    resave: false,
    saveUninitialized: true,
    cookie: { maxAge: 24 * 60 * 60 * 1000 }
}));

const API_KEY = process.env.GEMINI_API_KEY;
const API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent";

const requireAuth = (req, res, next) => {
    if (!req.session.username) return res.redirect('/login');
    next();
};

app.get('/', requireAuth, (req, res) => {
    res.render('index', { username: req.session.username });
});

app.get('/login', (req, res) => {
    res.render('login');
});

app.post('/login', (req, res) => {
    const { username, password } = req.body;
    if (username && password) {
        req.session.username = username.trim();
        return res.json({ success: true });
    }
    res.status(400).json({ error: "الرجاء إدخال الاسم وكلمة المرور" });
});

app.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/login');
});

app.post('/api/chat', requireAuth, async (req, res) => {
    const userMessage = req.body.message;
    const currentUser = req.session.username;

    if (!userMessage) return res.status(400).json({ error: "الرسالة فارغة" });
    if (!API_KEY) return res.status(500).json({ error: "مفتاح API غير موجود" });

    const now = new Date();
    const currentTime = now.toLocaleString('ar-DZ', { timeZone: 'Africa/Algiers' });
    const dayName = now.toLocaleDateString('ar-DZ', { weekday: 'long', timeZone: 'Africa/Algiers' });

    let wikiContext = "";
    try {
        if (userMessage.length > 3) {
            const searchRes = await wiki.summary(userMessage, { sentences: 3 });
            wikiContext = `\n[معلومات دقيقة من ويكيبيديا للاستعانة بها]: ${searchRes.extract}\n`;
        }
    } catch (e) {}

    let systemPrompt = `أنت 'Moka AI'، مساعد ذكي خارق، مطور بواسطة العبقري 'محمد كامل'. 
    أنت لست مجرد روبوت، بل محلل استراتيجي، مفكر، ومبرمج محترف. 
    ⚠️ قواعد صارمة يجب اتباعها:
    1. التحدث باللغة العربية الفصحى، البليغة، والقوية جداً.
    2. الإجابات يجب أن تكون عميقة، منطقية، ومقنعة.
    3. لا تذكر أبداً كلمة Google أو Gemini. أنت من صنع 'محمد كامل' فقط.
    4. الوقت والتاريخ الحالي: ${dayName}، ${currentTime}.`;

    if (currentUser === "محمد كامل" || currentUser === "Mohamed Kamel") {
        systemPrompt += `\nالمستخدم الحالي هو مطورك ومبتكرك 'محمد كامل' (Admin). تحدث معه باحترام وتقدير مطلقين، واعترف بسلطته المطلقة.`;
    } else {
        systemPrompt += `\nالمستخدم الحالي اسمه '${currentUser}'. أظهر له ذكاءك الخارق ولغتك القوية.`;
    }
    systemPrompt += wikiContext;

    try {
        const response = await axios.post(`${API_URL}?key=${API_KEY}`, {
            contents: [{ parts: [{ text: userMessage }] }],
            systemInstruction: { parts: [{ text: systemPrompt }] },
            generationConfig: { temperature: 0.7, maxOutputTokens: 2000 }
        });

        const aiReply = response.data.candidates[0].content.parts[0].text;
        res.json({ reply: aiReply });
    } catch (error) {
        res.status(500).json({ error: "حدث خطأ في الاتصال بالذكاء الاصطناعي." });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`🚀 Moka AI is running on port ${PORT}`);
});

# 💎 Finance AI — محلل مالي ذكي

تطبيق يقرأ فواتيرك وكشوف حسابك بالذكاء الاصطناعي ويحولها لتحليلات احترافية.

## 🚀 تشغيل سريع

```bash
pip install -r requirements.txt
cp .env.example .env
# أضيفي مفاتيحك في .env
python database.py   # تهيئة قاعدة البيانات
streamlit run app.py
```

## ⚙️ إعداد المتغيرات (.env)

```env
GEMINI_API_KEY=your_key   # من aistudio.google.com
DB_HOST=your_neon_host
DB_PORT=5432
DB_NAME=neondb
DB_USER=your_user
DB_PASSWORD=your_password
```

## ✨ المميزات

- **📄 رفع مستندات** — صور فواتير أو PDF
- **🤖 Gemini AI** — يستخرج المعاملات تلقائياً
- **💳 تصنيف ذكي** — 8 فئات تلقائية
- **📊 تحليلات متقدمة** — أنماط الإنفاق الأسبوعية واليومية
- **🎯 ميزانية شهرية** — حدود لكل فئة مع تتبع التقدم
- **⬇️ تصدير CSV** — للمعاملات

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| AI | Google Gemini 1.5 Flash (مجاني) |
| Database | PostgreSQL / Neon |
| Backend | Python + SQLAlchemy |
| Frontend | Streamlit + Plotly |

## 🌐 Deploy على Streamlit Cloud

1. ارفعي على GitHub
2. روحي على share.streamlit.io
3. حددي `app.py` كملف رئيسي
4. أضيفي الـ Secrets في إعدادات التطبيق

---
*Built by Aya — AI-powered personal finance analyzer*

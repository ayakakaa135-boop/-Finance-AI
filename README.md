# 💎 Finance AI — Smart Financial Document Analyzer

An AI-powered web app that reads your invoices, bank statements, and receipts — and turns them into professional financial analytics in seconds.
live demo https://finance-ai-7mb5r63rwyyb2z8fczof6w.streamlit.app/

> Built with Google Gemini · Streamlit · PostgreSQL

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
python database.py        # Initialize the database
streamlit run app.py
```

---

## ⚙️ Environment Variables (.env)

```env
GEMINI_API_KEY=your_key       # Get it free at aistudio.google.com
DB_HOST=your_neon_host
DB_PORT=5432
DB_NAME=neondb
DB_USER=your_user
DB_PASSWORD=your_password
```

---

## ✨ Features

### 📄 Document Upload & Parsing
- Upload **images** (PNG, JPG, WEBP), **PDFs**, or **CSV** files
- **Real PDF OCR** — uses `pdf2image` + `pytesseract` to extract text from scanned PDFs; falls back to Gemini Vision for image-based PDFs
- **AI extraction** — Gemini 1.5 Flash automatically identifies and extracts all transactions
- **Smart CSV parsing** — auto-detects column names in multiple languages (English, Swedish, Spanish)

### 💱 Multi-Currency Support ✨ New
- Select the document's source currency (USD, EUR, GBP, NOK, DKK, JPY, CHF, SEK)
- Live exchange rates fetched automatically via [Frankfurter API](https://frankfurter.app)
- All amounts stored and displayed in **SEK** with original values preserved
- Exchange rate shown in real-time before analysis

### 🤖 AI Financial Chat ✨ New
- Ask questions about your finances in **English or Arabic**
- The AI has full context of your real transaction data
- Quick question buttons for instant insights
- Powered by Gemini with conversation history

Example questions:
> *"Where am I spending the most money?"*
> *"Give me 3 tips to save based on my data"*
> *"وين راحت معظم فلوسي الشهر الماضي؟"*

### 📊 Analytics Dashboard
- **Expense distribution** — interactive pie chart by category
- **Monthly income vs expenses** — grouped bar chart
- **Weekly spending trends** — area line chart
- **Day-of-week patterns** — heatmap bar chart
- **Monthly summary table** — income, expenses, and net per month

### 🎯 Budget Management
- Set monthly spending limits per category
- Real-time progress bars with color indicators (green / yellow / red)
- **Automatic budget alerts** ✨ New — warnings at 80% and 100% usage shown directly on the Dashboard

### 📄 PDF Report Export ✨ New
- Generate a professional PDF report for any month or all time
- Includes: KPI summary, category breakdown with progress bars, monthly table, recent transactions, and key insights
- Built with ReportLab — dark-themed, portfolio-ready design

### 💳 Transaction Management
- Filter by type, category, and date range
- Total amount shown for the current filter
- Export filtered transactions to CSV
- Add manual transactions via form
- Delete uploaded documents and their transactions

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Model | Google Gemini 1.5 Flash |
| PDF OCR | pdf2image + pytesseract |
| Currency | Frankfurter API (live FX rates) |
| Database | PostgreSQL / Neon |
| Backend | Python 3.11 + SQLAlchemy |
| Frontend | Streamlit + Plotly |
| PDF Export | ReportLab |

---

## 📁 Project Structure

```
finance-ai/
├── app.py              # Main Streamlit app — all pages and UI
├── ai_parser.py        # Gemini AI parsing, OCR, currency conversion, chat
├── pdf_report.py       # PDF report generator (ReportLab)
├── database.py         # DB schema initialization and engine
├── requirements.txt
└── .env.example
```

---

## 🌐 Deploy on Streamlit Cloud

1. Push the project to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Select `app.py` as the main file
4. Add your secrets under **Settings → Secrets**:

```toml
GEMINI_API_KEY = "..."
DB_HOST = "..."
DB_PORT = "5432"
DB_NAME = "neondb"
DB_USER = "..."
DB_PASSWORD = "..."
```

---

## 📦 Dependencies

```
streamlit
google-generativeai
sqlalchemy
psycopg2-binary
pandas
plotly
pillow
python-dotenv
pdf2image
pytesseract
reportlab
requests
```

---

*Built by Aya — AI-powered personal finance analyzer*

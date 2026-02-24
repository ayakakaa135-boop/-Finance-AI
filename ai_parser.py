"""
AI Document Parser
✨ Uses Groq API (free, fast) with fallback to Google Gemini
Supports: images, PDFs (OCR), CSV files + multi-currency
"""
import os
import json
import base64
import requests
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
from io import StringIO, BytesIO

load_dotenv()


# ─────────────────────────────────────────────
# API Key helpers — read from .env OR st.secrets
# ─────────────────────────────────────────────
def _get_secret(name: str) -> str | None:
    val = os.getenv(name)
    if val:
        return val
    try:
        import streamlit as st
        val = st.secrets.get(name) or st.secrets.get(name.lower())
        if val:
            return val
    except Exception:
        pass
    return None


GROQ_API_KEY   = _get_secret("GROQ_API_KEY")
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY")

if not GROQ_API_KEY and not GEMINI_API_KEY:
    raise RuntimeError(
        "No AI API key found.\n"
        "Add GROQ_API_KEY (free at console.groq.com) to Streamlit secrets.\n"
        "Or add GEMINI_API_KEY as a fallback."
    )


# ─────────────────────────────────────────────
# Groq client (text only — free & fast)
# ─────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"   # free, very capable
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"


def _groq_text(prompt: str) -> str:
    """Call Groq API with a text prompt."""
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ─────────────────────────────────────────────
# Gemini client (vision — for images)
# ─────────────────────────────────────────────
_gemini_model = None

def _get_gemini():
    global _gemini_model
    if _gemini_model:
        return _gemini_model
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "Image analysis requires GEMINI_API_KEY.\n"
            "Get a free key at aistudio.google.com (free tier: 15 requests/min).\n"
            "Add it to Streamlit secrets as GEMINI_API_KEY."
        )
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    for name in ["gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash-latest"]:
        try:
            _gemini_model = genai.GenerativeModel(name)
            return _gemini_model
        except Exception:
            continue
    raise RuntimeError("Could not initialize Gemini model.")


# ─────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────
EXTRACTION_PROMPT = """You are a financial document analyzer. Extract ALL transactions from this document.

Return ONLY a valid JSON object — no markdown, no explanation:
{
  "doc_type": "invoice|bank_statement|receipt|csv",
  "currency": "SEK|USD|EUR|etc",
  "summary": "brief description",
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "transaction description",
      "amount": 123.45,
      "category": "Food|Transport|Shopping|Health|Education|Entertainment|Housing|Salary|Other",
      "type": "expense|income"
    }
  ]
}

Rules:
- Amounts must be positive numbers
- Use income for money received, expense for money spent
- If date is missing use today
- Return ONLY the JSON"""


def _clean_json(raw: str) -> dict:
    raw = raw.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("`").strip()
    return json.loads(raw)


# ─────────────────────────────────────────────
# ✨ Public parse functions
# ─────────────────────────────────────────────
def parse_document(image: Image.Image) -> dict:
    """Parse image using Gemini Vision (requires GEMINI_API_KEY)."""
    model = _get_gemini()
    response = model.generate_content([EXTRACTION_PROMPT, image])
    return _clean_json(response.text)


def parse_text_document(text: str) -> dict:
    """Parse text (from PDF/OCR) using Groq (free) or Gemini fallback."""
    prompt = f"{EXTRACTION_PROMPT}\n\nDocument text:\n{text[:4000]}"
    if GROQ_API_KEY:
        return _clean_json(_groq_text(prompt))
    model = _get_gemini()
    return _clean_json(model.generate_content(prompt).text)


def parse_pdf_file(file_bytes: bytes) -> dict:
    """Parse PDF: OCR → text → Groq. Falls back to Gemini vision."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        images = convert_from_bytes(file_bytes, dpi=300)
        full_text = "\n".join(pytesseract.image_to_string(img, lang="eng") for img in images)
        if len(full_text.strip()) > 50:
            return parse_text_document(full_text)
        # OCR got nothing — try Gemini Vision on first page
        return parse_document(images[0])
    except ImportError:
        return parse_text_document("PDF document — extract financial transactions if any.")
    except Exception as e:
        raise Exception(f"PDF parsing error: {e}")


def parse_csv_file(file_content: str) -> dict:
    """Auto-detect CSV columns or fall back to AI parsing."""
    try:
        df = pd.read_csv(StringIO(file_content))
        df.columns = df.columns.str.strip().str.lower()
        date_col   = next((c for c in df.columns if any(k in c for k in ["date","datum","fecha"])), None)
        desc_col   = next((c for c in df.columns if any(k in c for k in ["desc","detail","merchant","payee","beskrivning"])), None)
        amount_col = next((c for c in df.columns if any(k in c for k in ["amount","value","sum","belopp","cantidad"])), None)
        type_col   = next((c for c in df.columns if any(k in c for k in ["type","typ"])), None)
        cat_col    = next((c for c in df.columns if any(k in c for k in ["category","kategori"])), None)

        if not date_col or not amount_col:
            return _parse_csv_with_ai(file_content)

        transactions = []
        for _, row in df.iterrows():
            try:
                amount = float(str(row[amount_col]).replace(",", ".").replace(" ", ""))
                if type_col:
                    tx_type = "expense" if any(k in str(row[type_col]).lower() for k in ["expense","debit","debet"]) else "income"
                else:
                    tx_type = "expense" if amount < 0 else "income"
                transactions.append({
                    "date": str(row[date_col]),
                    "description": str(row[desc_col]) if desc_col else "Transaction",
                    "amount": abs(amount),
                    "category": str(row[cat_col]) if cat_col else "Other",
                    "type": tx_type,
                })
            except Exception:
                continue
        return {"doc_type": "csv", "currency": "SEK", "summary": f"CSV with {len(transactions)} transactions", "transactions": transactions}
    except Exception:
        return _parse_csv_with_ai(file_content)


def _parse_csv_with_ai(csv_content: str) -> dict:
    prompt = f"{EXTRACTION_PROMPT}\n\nCSV file:\n{csv_content[:3000]}"
    if GROQ_API_KEY:
        return _clean_json(_groq_text(prompt))
    model = _get_gemini()
    return _clean_json(model.generate_content(prompt).text)


# ─────────────────────────────────────────────
# ✨ Multi-currency
# ─────────────────────────────────────────────
_fx_cache: dict = {}

def get_exchange_rate(from_currency: str, to_currency: str = "SEK") -> float:
    if from_currency == to_currency:
        return 1.0
    key = f"{from_currency}_{to_currency}"
    if key in _fx_cache:
        return _fx_cache[key]
    try:
        r = requests.get(f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}", timeout=5)
        rate = r.json()["rates"][to_currency]
        _fx_cache[key] = rate
        return rate
    except Exception:
        fallback = {"USD": 10.5, "EUR": 11.2, "GBP": 13.1, "NOK": 0.95, "DKK": 1.5}
        return fallback.get(from_currency, 1.0)


def convert_transactions_to_sek(transactions: list, source_currency: str) -> list:
    if source_currency == "SEK":
        return transactions
    rate = get_exchange_rate(source_currency, "SEK")
    result = []
    for tx in transactions:
        tx = tx.copy()
        tx["original_amount"]   = tx.get("amount", 0)
        tx["original_currency"] = source_currency
        tx["amount"] = round(float(tx["amount"]) * rate, 2)
        result.append(tx)
    return result


# ─────────────────────────────────────────────
# ✨ AI Chat
# ─────────────────────────────────────────────
def chat_with_finances(user_message: str, financial_context: str, history: list) -> str:
    system = f"""You are a smart personal finance advisor.
You have access to the user's real financial data. Answer clearly and helpfully with specific numbers.
If the user writes in Arabic, respond in Arabic. If English, respond in English.

FINANCIAL DATA:
{financial_context}"""

    if GROQ_API_KEY:
        messages = [{"role": "system", "content": system}]
        for role, msg in history[-6:]:
            messages.append({"role": "user" if role == "user" else "assistant", "content": msg})
        messages.append({"role": "user", "content": user_message})
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "temperature": 0.7},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    # Fallback to Gemini
    model = _get_gemini()
    parts = [system]
    for role, msg in history[-6:]:
        parts.append(f"{'User' if role == 'user' else 'Assistant'}: {msg}")
    parts.append(f"User: {user_message}")
    return model.generate_content("\n\n".join(parts)).text


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
CATEGORY_ICONS = {
    "Food": "🍔", "Transport": "🚗", "Shopping": "🛍️",
    "Health": "💊", "Education": "📚", "Entertainment": "🎮",
    "Housing": "🏠", "Salary": "💼", "Other": "📦",
}

CATEGORY_COLORS = {
    "Food": "#f472b6", "Transport": "#60a5fa", "Shopping": "#fb923c",
    "Health": "#34d399", "Education": "#a78bfa", "Entertainment": "#fbbf24",
    "Housing": "#94a3b8", "Salary": "#10b981", "Other": "#6b7280",
}

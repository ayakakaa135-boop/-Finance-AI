"""
AI Document Parser using Google Gemini
Supports invoices, bank statements, receipts, and CSV files
✨ NEW: Real PDF OCR + Multi-currency conversion
"""
import os
import json
import requests
import pandas as pd
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from io import StringIO

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Try models in order — handles regional availability differences
_MODEL_CANDIDATES = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.0-pro",
]

def _get_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. "
            "Add it to Streamlit secrets: Settings → Secrets → GEMINI_API_KEY = \"your_key\""
        )
    last_error = None
    for name in _MODEL_CANDIDATES:
        try:
            m = genai.GenerativeModel(name)
            # lightweight probe — no actual content generation
            m.count_tokens("test")
            return m
        except Exception as e:
            last_error = e
            continue
    # If count_tokens probe failed for all, still try to return the first model
    # (some regions block count_tokens but allow generate_content)
    try:
        return genai.GenerativeModel(_MODEL_CANDIDATES[0])
    except Exception:
        raise RuntimeError(
            f"Could not initialize any Gemini model. Last error: {last_error}. "
            "Check your GEMINI_API_KEY in Streamlit secrets."
        )

model = _get_model()

EXTRACTION_PROMPT = """
You are a financial document analyzer. Analyze this document (invoice, bank statement, receipt, or transaction list) and extract ALL transactions.

Return ONLY a valid JSON object with this exact structure:
{
  "doc_type": "invoice|bank_statement|receipt|csv",
  "currency": "SEK|USD|EUR|etc",
  "summary": "brief description of the document",
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
- Extract every single transaction you can find
- Amounts must be positive numbers
- Use "income" for money received, "expense" for money spent
- If date is missing use today's date
- Categories must be one of: Food, Transport, Shopping, Health, Education, Entertainment, Housing, Salary, Other
- Return ONLY the JSON, no other text
"""


# ─────────────────────────────────────────────
# ✨ NEW: Multi-currency conversion
# ─────────────────────────────────────────────
_fx_cache: dict = {}

def get_exchange_rate(from_currency: str, to_currency: str = "SEK") -> float:
    """Fetch live exchange rate. Cached per session."""
    if from_currency == to_currency:
        return 1.0
    cache_key = f"{from_currency}_{to_currency}"
    if cache_key in _fx_cache:
        return _fx_cache[cache_key]
    try:
        r = requests.get(
            f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}",
            timeout=5
        )
        rate = r.json()["rates"][to_currency]
        _fx_cache[cache_key] = rate
        return rate
    except Exception:
        # Fallback rates if API is down
        fallback = {"USD": 10.5, "EUR": 11.2, "GBP": 13.1, "NOK": 0.95, "DKK": 1.5}
        return fallback.get(from_currency, 1.0)


def convert_transactions_to_sek(transactions: list, source_currency: str) -> list:
    """Convert all transaction amounts to SEK."""
    if source_currency == "SEK":
        return transactions
    rate = get_exchange_rate(source_currency, "SEK")
    converted = []
    for tx in transactions:
        tx = tx.copy()
        original_amount = tx.get("amount", 0)
        tx["amount"] = round(float(original_amount) * rate, 2)
        tx["original_amount"] = original_amount
        tx["original_currency"] = source_currency
        converted.append(tx)
    return converted


# ─────────────────────────────────────────────
# ✨ NEW: Real PDF parsing with OCR
# ─────────────────────────────────────────────
def parse_pdf_file(file_bytes: bytes) -> dict:
    """
    Parse PDF using pdf2image + pytesseract OCR.
    Falls back to Gemini vision on each page image.
    """
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        # Convert PDF pages to images
        images = convert_from_bytes(file_bytes, dpi=300)

        # Try OCR text first
        full_text = ""
        for img in images:
            page_text = pytesseract.image_to_string(img, lang="eng")
            full_text += page_text + "\n"

        if len(full_text.strip()) > 50:
            # Good OCR result — use text parser
            return parse_text_document(full_text)
        else:
            # OCR failed (scanned image) — send pages to Gemini vision
            results = []
            for img in images[:3]:  # Max 3 pages
                try:
                    result = parse_document(img)
                    results.append(result)
                except Exception:
                    continue

            if not results:
                raise ValueError("Could not extract text from PDF")

            # Merge results from all pages
            merged = results[0]
            for r in results[1:]:
                merged["transactions"].extend(r.get("transactions", []))
            merged["summary"] = f"PDF with {len(merged['transactions'])} transactions across {len(images)} pages"
            return merged

    except ImportError:
        # pdf2image not available — try direct text extraction
        return parse_text_document(f"PDF document uploaded. Please analyze any financial data.")
    except Exception as e:
        raise Exception(f"PDF parsing error: {e}")


# ─────────────────────────────────────────────
# Core parsers
# ─────────────────────────────────────────────
def parse_document(image: Image.Image) -> dict:
    """Send image to Gemini and extract transactions."""
    response = model.generate_content([EXTRACTION_PROMPT, image])
    return _clean_and_parse(response.text)


def parse_text_document(text: str) -> dict:
    """Parse extracted text (from PDF/OCR) using Gemini."""
    prompt = f"{EXTRACTION_PROMPT}\n\nDocument text:\n{text}"
    response = model.generate_content(prompt)
    return _clean_and_parse(response.text)


def _clean_and_parse(raw: str) -> dict:
    """Clean markdown fences and parse JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ─────────────────────────────────────────────
# CSV parsing
# ─────────────────────────────────────────────
def parse_csv_file(file_content: str) -> dict:
    """Parse CSV file with auto-detection or AI fallback."""
    try:
        df = pd.read_csv(StringIO(file_content))
        date_cols = ['date', 'transaction_date', 'posting_date', 'datum', 'fecha']
        desc_cols = ['description', 'details', 'merchant', 'payee', 'beskrivning', 'descripción']
        amount_cols = ['amount', 'value', 'sum', 'belopp', 'cantidad']
        type_cols = ['type', 'transaction_type', 'typ']
        category_cols = ['category', 'kategori', 'categoría']

        df.columns = df.columns.str.strip().str.lower()
        date_col = next((col for col in df.columns if any(d in col for d in date_cols)), None)
        desc_col = next((col for col in df.columns if any(d in col for d in desc_cols)), None)
        amount_col = next((col for col in df.columns if any(d in col for d in amount_cols)), None)
        type_col = next((col for col in df.columns if any(t in col for t in type_cols)), None)
        category_col = next((col for col in df.columns if any(c in col for c in category_cols)), None)

        if not date_col or not amount_col:
            return parse_csv_with_ai(file_content)

        transactions = []
        for _, row in df.iterrows():
            try:
                amount = float(str(row[amount_col]).replace(',', '.').replace(' ', ''))
                if type_col and type_col in row:
                    tx_type = 'expense' if 'expense' in str(row[type_col]).lower() or 'debit' in str(row[type_col]).lower() else 'income'
                else:
                    tx_type = 'expense' if amount < 0 else 'income'
                transactions.append({
                    "date": str(row[date_col]) if date_col else "",
                    "description": str(row[desc_col]) if desc_col else "Transaction",
                    "amount": abs(amount),
                    "category": str(row[category_col]) if category_col and category_col in row else "Other",
                    "type": tx_type
                })
            except Exception:
                continue

        return {
            "doc_type": "csv",
            "currency": "SEK",
            "summary": f"CSV file with {len(transactions)} transactions",
            "transactions": transactions
        }
    except Exception:
        return parse_csv_with_ai(file_content)


def parse_csv_with_ai(csv_content: str) -> dict:
    """Use Gemini AI to parse CSV when auto-detection fails."""
    prompt = f"{EXTRACTION_PROMPT}\n\nThis is a CSV file:\n{csv_content[:3000]}"
    response = model.generate_content(prompt)
    return _clean_and_parse(response.text)


# ─────────────────────────────────────────────
# ✨ NEW: AI Financial Chat
# ─────────────────────────────────────────────
def chat_with_finances(user_message: str, financial_context: str, history: list) -> str:
    """
    Chat with Gemini about personal finances.
    history: list of (role, message) tuples
    """
    system_prompt = f"""You are a smart and friendly personal finance advisor.
You have access to the user's real financial data below. Answer questions clearly and helpfully.
Always give specific numbers from the data when relevant.
If asked in Arabic, respond in Arabic. If in English, respond in English.

FINANCIAL DATA:
{financial_context}
"""
    # Build conversation history
    messages = [system_prompt]
    for role, msg in history[-6:]:  # Last 6 exchanges for context
        prefix = "User" if role == "user" else "Assistant"
        messages.append(f"{prefix}: {msg}")
    messages.append(f"User: {user_message}")

    full_prompt = "\n\n".join(messages)
    response = model.generate_content(full_prompt)
    return response.text


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

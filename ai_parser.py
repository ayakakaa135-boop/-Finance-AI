"""
AI Document Parser using Google Gemini
يقرأ الفواتير وكشوف الحساب ويستخرج المعاملات تلقائياً
"""
import os
import json
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")  # مجاني وسريع

EXTRACTION_PROMPT = """
You are a financial document analyzer. Analyze this document (invoice, bank statement, or receipt) and extract ALL transactions.

Return ONLY a valid JSON object with this exact structure:
{
  "doc_type": "invoice|bank_statement|receipt",
  "currency": "SEK|USD|EUR|etc",
  "summary": "brief description of the document in Arabic",
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
- Write summary in Arabic
- Return ONLY the JSON, no other text
"""


def parse_document(image: Image.Image) -> dict:
    """
    Send image to Gemini and extract transactions.
    Returns parsed JSON or raises exception.
    """
    response = model.generate_content([EXTRACTION_PROMPT, image])
    raw = response.text.strip()

    # Clean response — remove markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def parse_text_document(text: str) -> dict:
    """
    Parse extracted text (from PDF/OCR) using Gemini.
    """
    prompt = f"{EXTRACTION_PROMPT}\n\nDocument text:\n{text}"
    response = model.generate_content(prompt)
    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


CATEGORY_ICONS = {
    "Food": "🍔",
    "Transport": "🚗",
    "Shopping": "🛍️",
    "Health": "💊",
    "Education": "📚",
    "Entertainment": "🎮",
    "Housing": "🏠",
    "Salary": "💼",
    "Other": "📦",
}

CATEGORY_COLORS = {
    "Food": "#f472b6",
    "Transport": "#60a5fa",
    "Shopping": "#fb923c",
    "Health": "#34d399",
    "Education": "#a78bfa",
    "Entertainment": "#fbbf24",
    "Housing": "#94a3b8",
    "Salary": "#10b981",
    "Other": "#6b7280",
}

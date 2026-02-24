"""
AI Document Parser using Google Gemini
Supports invoices, bank statements, receipts, and CSV files
"""
import os
import json
import pandas as pd
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from io import StringIO

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

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


def parse_csv_file(file_content: str) -> dict:
    """
    Parse CSV file and convert to standard transaction format.
    Attempts to auto-detect columns or uses AI to understand the structure.
    """
    try:
        # Try to read CSV
        df = pd.read_csv(StringIO(file_content))
        
        # Common column name mappings (case-insensitive)
        date_cols = ['date', 'transaction_date', 'posting_date', 'datum', 'fecha']
        desc_cols = ['description', 'details', 'merchant', 'payee', 'beskrivning', 'descripción']
        amount_cols = ['amount', 'value', 'sum', 'belopp', 'cantidad']
        type_cols = ['type', 'transaction_type', 'typ']
        category_cols = ['category', 'kategori', 'categoría']
        
        # Find matching columns
        df.columns = df.columns.str.strip().str.lower()
        
        date_col = next((col for col in df.columns if any(d in col for d in date_cols)), None)
        desc_col = next((col for col in df.columns if any(d in col for d in desc_cols)), None)
        amount_col = next((col for col in df.columns if any(d in col for d in amount_cols)), None)
        type_col = next((col for col in df.columns if any(t in col for t in type_cols)), None)
        category_col = next((col for col in df.columns if any(c in col for c in category_cols)), None)
        
        # If we can't auto-detect, use AI
        if not date_col or not amount_col:
            return parse_csv_with_ai(file_content)
        
        # Parse transactions
        transactions = []
        for _, row in df.iterrows():
            try:
                # Get amount and determine if expense or income
                amount = float(str(row[amount_col]).replace(',', '.').replace(' ', ''))
                
                # Determine transaction type
                if type_col and type_col in row:
                    tx_type = 'expense' if 'expense' in str(row[type_col]).lower() or 'debit' in str(row[type_col]).lower() else 'income'
                else:
                    tx_type = 'expense' if amount < 0 else 'income'
                
                # Make amount positive
                amount = abs(amount)
                
                transaction = {
                    "date": str(row[date_col]) if date_col else "",
                    "description": str(row[desc_col]) if desc_col else "Transaction",
                    "amount": amount,
                    "category": str(row[category_col]) if category_col and category_col in row else "Other",
                    "type": tx_type
                }
                transactions.append(transaction)
            except:
                continue
        
        return {
            "doc_type": "csv",
            "currency": "SEK",
            "summary": f"CSV file with {len(transactions)} transactions",
            "transactions": transactions
        }
        
    except Exception as e:
        # Fallback to AI parsing
        return parse_csv_with_ai(file_content)


def parse_csv_with_ai(csv_content: str) -> dict:
    """
    Use Gemini AI to parse CSV when auto-detection fails.
    """
    prompt = f"""
    {EXTRACTION_PROMPT}
    
    This is a CSV file. Please analyze it and extract all financial transactions:
    
    {csv_content[:3000]}  # Limit to first 3000 chars
    """
    
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

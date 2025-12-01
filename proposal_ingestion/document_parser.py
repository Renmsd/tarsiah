# document_parser.py
# Light version: all heavy parsing moved to Railway extractor

import os
import requests
from pathlib import Path
from typing import Optional

from utils.helpers import clean_text, normalize_arabic_text, is_arabic_text, arabic_to_western_digits

# =============================
# CONFIG: Railway Extractor API
# =============================
RAILWAY_EXTRACT_URL = "https://pdfextractor-production-e86f.up.railway.app/extract"


# ----------  Arabic-digit / RTL helpers  ----------
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
DIGIT_MAP     = str.maketrans(ARABIC_DIGITS, "0123456789")

def is_arabic(s: str) -> bool:
    return any('\u0600' <= ch <= '\u06FF' or
               '\u0750' <= ch <= '\u077F' or
               '\u08A0' <= ch <= '\u08FF' or
               '\uFB50' <= ch <= '\uFDFF' or
               '\uFE70' <= ch <= '\uFEFF' for ch in s)

def to_western_digits(s: str) -> str:
    return s.translate(DIGIT_MAP)


# =============================
# NEW: Remote PDF extraction
# =============================
def extract_pdf_remote(pdf_path: str) -> str:
    """
    Sends PDF to Railway Extractor API.
    All heavy parsing (Tika + pdfplumber fallback) happens on Railway.
    """

    with open(pdf_path, "rb") as f:
        files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
        response = requests.post(
            RAILWAY_EXTRACT_URL,
            files=files,
            timeout=900   # up to 15 minutes, safe
        )

    if response.status_code != 200:
        raise RuntimeError(f"❌ Railway parser error {response.status_code}: {response.text}")

    data = response.json()

    if "content" not in data:
        raise RuntimeError(f"❌ Railway parser returned invalid JSON: {data}")

    # Normalize and clean
    raw_text = data["content"]
    normalized_text = normalize_arabic_text(raw_text)
    cleaned_text = clean_text(normalized_text)

    return cleaned_text


# =============================
# MAIN ENTRY POINT (used by Flask)
# =============================
def parse_document(file_path: str, extract_tables: bool = False) -> str:
    """
    Main function called by your Flask app.
    Now only calls the remote Railway parser.
    """
    if not file_path.lower().endswith(".pdf"):
        raise ValueError("❌ Only PDF files can be parsed.")

    try:
        return extract_pdf_remote(file_path)
    except Exception as e:
        raise RuntimeError(f"❌ Failed to parse PDF via Railway: {str(e)}")

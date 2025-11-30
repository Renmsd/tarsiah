import pdfplumber
from pathlib import Path
from utils.helpers import clean_text, normalize_arabic_text, is_arabic_text, arabic_to_western_digits
from typing import Optional

import requests

TIKA_URL = "https://tika-service-production.up.railway.app"



# ... (ARABIC_DIGITS, DIGIT_MAP, is_arabic, to_western_digits remain the same) ...
# ----------  Arabic-digit / RTL helpers  ----------
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
DIGIT_MAP     = str.maketrans(ARABIC_DIGITS, "0123456789")

def is_arabic(s: str) -> bool:
    return any('\u0600' <= ch <= '\u06FF' or '\u0750' <= ch <= '\u077F' or
               '\u08A0' <= ch <= '\u08FF' or '\uFB50' <= ch <= '\uFDFF' or
               '\uFE70' <= ch <= '\uFEFF' for ch in s)

def to_western_digits(s: str) -> str:
    return s.translate(DIGIT_MAP)
# ... (end of helpers) ...



def read_pdf_text_with_tika(pdf_path: str) -> Optional[str]:
    """
    Sends PDF file to remote Apache Tika server deployed on Railway.
    Returns extracted text or None if Tika fails.
    """
    try:
        with open(pdf_path, "rb") as f:
            response = requests.put(
                f"{TIKA_URL}/tika",
                data=f,
                headers={"Content-Type": "application/pdf"},
                timeout=60
            )

        if response.status_code == 200:
            text = response.text
            if text.strip():
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                text = text.replace("\x00", "").replace("\xa0", " ")
                text = text.replace("\x0c", "\n\n=== PAGE BREAK ===\n\n")
                return normalize_arabic_text(text)

        print(f"⚠️ Tika returned non-200 status: {response.status_code}")
        return None

    except Exception as e:
        print(f"❌ Remote Tika request failed: {e}")
        return None


def extract_tables_from_page(path: str | Path, page_idx: int = 0, table_settings: dict = None):
    """
    Finds and extracts text from tables on a specific page using pdfplumber.

    Args:
        path: Path to the PDF file.
        page_idx: Index of the page to extract tables from (0-based).
        table_settings: Optional dictionary of settings for table finding.
                        See pdfplumber documentation for details.

    Returns:
        A list of lists of lists, where the outer list represents tables,
        the middle list represents rows within a table, and the inner list
        represents cells within a row. Cell values are strings.
        Returns an empty list if no tables are found.
    """
    if table_settings is None:
        # Use default settings, potentially adapted for Arabic/RTL layouts if needed
        # See pdfplumber docs for all possible settings and their defaults
        table_settings = {}

    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_idx]
        try:
            # Find tables using the provided settings
            tables = page.find_tables(table_settings)
            if not tables:
                print(f"   ℹ️  لا توجد جداول في الصفحة {page_idx + 1}.")
                return []

            extracted_tables = []
            for i, table in enumerate(tables):
                # Extract text from the table object
                # This returns a list of lists (rows of cells)
                table_data = table.extract()
                extracted_tables.append(table_data)
                print(f"   ✅ تم استخراج الجدول {i + 1} من الصفحة {page_idx + 1} ((rows: {len(table_data)}, cols: {len(table_data[0]) if table_data else 0}).")

            return extracted_tables

        except Exception as e:
            print(f"❌ خطأ في استخراج الجداول من الصفحة {page_idx + 1}: {str(e)}")
            return [] # Return empty list on error

def extract_all_tables_from_pdf(path: str | Path, table_settings: dict = None):
    """
    Finds and extracts text from tables on ALL pages of a PDF.

    Args:
        path: Path to the PDF file.
        table_settings: Optional dictionary of settings for table finding.

    Returns:
        A dictionary where keys are page numbers (1-based) and values are
        lists of tables found on that page (same structure as extract_tables_from_page).
        Example: {1: [[['Cell1', 'Cell2'], ['Cell3', 'Cell4']], [['CellA', 'CellB']]], 2: [...]}
    """
    all_tables = {}
    with pdfplumber.open(path) as pdf:
        for page_num in range(len(pdf.pages)):
            print(f"🔍 البحث عن جداول في صفحة {page_num + 1}...")
            tables_on_page = extract_tables_from_page(path, page_num, table_settings)
            if tables_on_page:
                all_tables[page_num + 1] = tables_on_page # Store using 1-based page numbering

    return all_tables

# --- Text Extraction Logic (Built-in RTL) ---

def extract_page_lines_builtin_rtl(path: str | Path, page_idx: int = 0):
    """
    Extracts text from a specific page using pdfplumber's built-in layout and RTL handling.
    This attempts to use the char_dir and line_dir parameters for Arabic.
    """
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_idx]
        # Use extract_text with layout=True and RTL settings
        # This should theoretically handle RTL word order and TTB line order.
        # Note: The effectiveness depends on how well pdfminer.six (the backend) handles the PDF's internal text order.
        # It might work well for simple cases, but the manual sorting approach is more robust for complex layouts.
        # Experiment with this vs. the manual approach.
        text_layout = page.extract_text(
            layout=True,
            x_density=7.25,  # Default values for layout mimic
            y_density=13,    # Default values for layout mimic
            # IMPORTANT: Set directions for Arabic
            char_dir_render="rtl", # Attempt to render characters RTL
            line_dir_render="ttb", # Attempt to render lines TTB
            # These parameters control how characters are grouped into words/lines internally
            # They might also need adjustment for complex Arabic fonts/layouts
            x_tolerance=3,
            y_tolerance=3
        )
        if text_layout:
             # Apply digit normalization and general cleaning
             normalized_text = to_western_digits(text_layout)
             cleaned_text = clean_text(normalized_text)
             # Split into lines based on newlines added by extract_text(layout=True)
             lines = cleaned_text.split('\n')
             # Filter out empty lines if necessary
             return [line for line in lines if line.strip()]
        else:
             print(f"⚠️ تحذير: فشل extract_text(layout=True) في استخراج نص من الصفحة {page_idx + 1} باستخدام الإعدادات المبنية.")
             return []


def extract_page_lines_manual_rtl(path: str | Path, page_idx: int = 0):
    """
    Original method: Extracts text from a specific page using manual coordinate-based sorting for RTL.
    This is the more robust method for ensuring correct RTL order based on physical position.
    """
    print(f"⚠️ تحذير: استخدام الطريقة اليدوية (القائمة على الإحداثيات) غير مُضمنة في هذا التحديث. يُرجى الرجوع للنسخة السابقة للوظائف 'clean_words' و 'words_to_lines_ar'.")
    return [] # Or implement the full manual logic here if needed as a fallback


def parse_document(file_path: str, extract_tables: bool = False) -> str: # Added extract_tables parameter
    """
    Parses a document (PDF only for now) using the enhanced extraction logic.
    Attempts to use Apache Tika first, then pdfplumber.
    Applies advanced cleaning and RTL handling.
    Optionally extracts tables from the document.
    For non-PDF files, you would need to implement other parsers or raise an error.
    """
    if file_path.lower().endswith('.pdf'):
        try:
            # Try Tika first (better for complex PDFs)
            full_text = read_pdf_text_with_tika(file_path)
            
            if full_text and full_text.strip():
                print(f"✅ تم استخراج النص باستخدام Apache Tika")
                # Apply the general clean_text function from helpers
                cleaned_text = clean_text(full_text)
                return cleaned_text
            else:
                print(f"⚠️ Apache Tika failed, using pdfplumber fallback...")
            
            # Use the pdfplumber logic to extract text page by page
            full_text = ""
            all_extracted_tables = {} # Dictionary to store tables if requested

            with pdfplumber.open(file_path) as pdf:
                for page_num in range(len(pdf.pages)):
                    print(f"📄 معالجة صفحة {page_num + 1} من {len(pdf.pages)}...")
                    # --- NEW LOGIC: Use the built-in RTL handling function ---
                    page_lines = extract_page_lines_builtin_rtl(file_path, page_num)
                    # --- END NEW LOGIC ---

                    page_text = "\n".join(page_lines)
                    if page_text: # Check if text was extracted for this page using the new method
                        print(f"   ✅ تم استخراج {len(page_text)} حرف باستخدام الطريقة المبنية للصفحة {page_num + 1}.")
                        full_text += page_text + "\n"
                    else:
                        print(f"   ⚠️ الطريقة المبنية فشلت في استخراج نص من الصفحة {page_num + 1}.")
                        # --- FALLBACK LOGIC: Use manual coordinate-based RTL ---
                        # If the built-in method fails or doesn't work well, uncomment the next lines
                        # and implement the manual logic in extract_page_lines_manual_rtl
                        # page_lines_fallback = extract_page_lines_manual_rtl(file_path, page_num)
                        # page_text_fallback = "\n".join(page_lines_fallback)
                        # if page_text_fallback:
                        #     print(f"   ✅ تم استخراج {len(page_text_fallback)} حرف باستخدام الطريقة اليدوية للصفحة {page_num + 1}.")
                        #     full_text += page_text_fallback + "\n"
                        # else:
                        #     print(f"   ❌ كلا الطريقتين فشلتا في استخراج نص من الصفحة {page_num + 1}.")
                        # --- END FALLBACK LOGIC ---

                    # --- NEW LOGIC: Extract tables if requested ---
                    if extract_tables:
                        print(f"🔍 جاري استخراج الجداول من الصفحة {page_num + 1}...")
                        tables_on_page = extract_tables_from_page(file_path, page_num)
                        if tables_on_page:
                             all_extracted_tables[page_num + 1] = tables_on_page
                    # --- END NEW LOGIC ---

            if full_text:
                # Apply the general clean_text function from helpers
                cleaned_text = clean_text(full_text)
            else:
                print(f"⚠️ تحذير: لم يتم استخراج محتوى نصي من الملف: {file_path}")
                cleaned_text = "" # Return empty string if no text found

            # --- NEW LOGIC: Return text and optionally tables ---
            if extract_tables:
                # You might want to structure this differently depending on how you plan to use the tables
                # For now, returning a tuple (text, tables_dict)
                return cleaned_text, all_extracted_tables
            else:
                # Return only the text as before
                return cleaned_text
            # --- END NEW LOGIC ---

        except Exception as e:
            print(f"❌ خطأ في تحليل الملف {file_path}: {str(e)}")
            raise RuntimeError(f"Failed to parse {file_path}: {str(e)}")
    else:
        # Handle other formats (DOCX, DOC, TXT) here or raise an error
        # For now, let's raise an error as the new logic only handles PDFs
        raise ValueError(f"Unsupported file format for enhanced parser: {file_path}. Only PDF is supported by this parser.")
        # If you want to handle other formats, you can add logic here using libraries like python-docx for DOCX.
        # For TXT, just read the file directly as in proposal_loader.py.
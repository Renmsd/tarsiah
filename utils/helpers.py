import re
from typing import Optional

def clean_text(text: str) -> str:
    """
    Cleans extracted text by removing excessive whitespace and repeated words within lines.
    """
    if not text:
        return ""

    # Split the full text into lines based on newline characters
    lines = text.split('\n')

    cleaned_lines = []
    for line in lines:
        # Remove excessive whitespace within the line (multiple spaces, tabs) and strip leading/trailing whitespace
        # This helps ensure words are separated by a single space
        cleaned_line = re.sub(r'\s+', ' ', line).strip()

        if cleaned_line: # Check if the line is not empty after initial cleaning
            # Split the cleaned line into individual words based on spaces
            words = cleaned_line.split(' ')
            
            # Maintain order of first occurrence, remove duplicates within the line
            seen_words = set()
            unique_words = []
            for word in words:
                # Use case-sensitive comparison for now (adjust if needed)
                # Using a set for O(1) average lookup time for efficiency
                if word not in seen_words:
                    seen_words.add(word)
                    unique_words.append(word)
            
            # Join the unique words back together with a single space
            deduplicated_line = ' '.join(unique_words)
            
            # Add the final processed line to the list of cleaned lines
            cleaned_lines.append(deduplicated_line)
        # else: # If the line was empty after initial cleaning, it won't be added

    # Join all the processed lines back together with newline characters
    final_text = '\n'.join(cleaned_lines)
    return final_text

def chunk_text(text: str, max_chars: int = 3000) -> list:
    """Simple chunking for long documents"""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    for i in range(0, len(text), max_chars):
        chunks.append(text[i:i + max_chars])
    return chunks

# ===== Arabic helpers from friend's code =====
ARABIC_DIGITS   = "٠١٢٣٤٥٦٧٨٩"
WESTERN_DIGITS  = "0123456789"
ARABIC_PERCENT  = "٪"

def arabic_to_western_digits(s: str) -> str:
    return s.translate(str.maketrans(ARABIC_DIGITS, WESTERN_DIGITS))

def normalize_arabic_text(s: str) -> str:
    """Enhanced text normalization from friend's code"""
    if not s:
        return ""
    s = s.replace('ـ','').replace(ARABIC_PERCENT, '%')
    s = arabic_to_western_digits(s)
    s = s.replace('–','-').replace('—','-').replace('−','-').replace('：',':')
    s = re.sub(r'[ \t]+',' ', s)
    s = s.replace("\r\n","\n").replace("\r","\n")
    s = re.sub(r'\n+','\n', s).strip()
    return s

def is_arabic_text(text: str) -> bool:
    """Check if text contains Arabic characters"""
    return any('\u0600' <= ch <= '\u06FF' or '\u0750' <= ch <= '\u077F' or
               '\u08A0' <= ch <= '\u08FF' or '\uFB50' <= ch <= '\uFDFF' or
               '\uFE70' <= ch <= '\uFEFF' for ch in text)
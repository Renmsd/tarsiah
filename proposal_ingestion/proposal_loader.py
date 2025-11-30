# proposal_ingestion/proposal_loader.py
import os
from pathlib import Path
# Import the parser function
from proposal_ingestion.document_parser import parse_document

def load_proposals(proposals_dir: str) -> dict:
    """
    Loads proposals from a directory.
    Converts PDF to text using pdfplumber. Reads TXT directly.
    Currently does not handle DOCX/DOC without additional libraries.
    Returns a dict: {filename: {"text": "...", "name": "..."}}
    """
    proposals = {}
    for filename in os.listdir(proposals_dir):
        filepath = os.path.join(proposals_dir, filename)
        # Check for supported document extensions (PDF, TXT for now)
        if os.path.isfile(filepath) and filename.lower().endswith(('.pdf', '.txt')):
            # Extract a display name from the filename (remove extension, replace _ with spaces, etc.)
            path_obj = Path(filename)
            display_name = path_obj.stem.replace('_', ' ').replace('-', ' ').title() # Example: "Vendor_A_Report.pdf" -> "Vendor A Report"

            if filename.lower().endswith('.txt'):
                 # Read text files directly
                 with open(filepath, 'r', encoding='utf-8') as f:
                      text = f.read()
            elif filename.lower().endswith('.pdf'):
                 # Use the pdfplumber parser for PDFs
                 text = parse_document(filepath)
                 # The text is now extracted but NOT saved to a separate .txt file

            proposals[filename] = {
                "text": text,
                "name": display_name # Add the extracted name
            }
        else:
             print(f"⚠️ تجاهل الملف غير المدعوم: {filename}")
    return proposals

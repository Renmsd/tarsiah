# rfp_summurizor.py
# Light version: PDF text comes from Railway extractor instead of local parsing

import os
import re
import json
import requests
from pathlib import Path
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, MODEL_NAME

# =============================
# CONFIG: Railway Extractor API
# =============================
RAILWAY_EXTRACT_URL = "https://pdfextractor-production-e86f.up.railway.app/extract"


# ===== Arabic helpers =====
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
WESTERN_DIGITS = "0123456789"
ARABIC_PERCENT = "٪"

def arabic_to_western_digits(s: str) -> str:
    return s.translate(str.maketrans(ARABIC_DIGITS, WESTERN_DIGITS))

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace('ـ', '').replace(ARABIC_PERCENT, '%')
    s = arabic_to_western_digits(s)
    s = s.replace('–', '-').replace('—', '-').replace('−', '-').replace('：', ':')
    s = re.sub(r'[ \t]+', ' ', s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r'\n+', '\n', s).strip()
    return s


# =============================
# NEW: Remote PDF extraction
# =============================
def read_pdf_text(pdf_path: str) -> str:
    """
    Extract PDF text using Railway Extractor API.
    """

    with open(pdf_path, "rb") as f:
        files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
        response = requests.post(
            RAILWAY_EXTRACT_URL,
            files=files,
            timeout=900
        )

    if response.status_code != 200:
        raise RuntimeError(f"❌ Railway parser error {response.status_code}: {response.text}")

    data = response.json()

    if "content" not in data:
        raise RuntimeError(f"❌ Railway parser returned invalid result: {data}")

    return normalize_text(data["content"])


# =============================
# RFP SUMMARY MODELS
# =============================

class EvaluationSubCriterion(BaseModel):
    name: str
    weight: float = Field(0.0, ge=0.0, le=100.0)

class EvaluationCriteriaDetails(BaseModel):
    technical_pass_mark: float = Field(70.0)
    technical_criteria: list[EvaluationSubCriterion] = Field(default_factory=list)
    financial_evaluation_method: str = "lowest_price_among_qualified"

class RFPSummary(BaseModel):
    project_scope: str = ""
    technical_requirements: list[str] = Field(default_factory=list)
    evaluation_criteria_details: EvaluationCriteriaDetails = Field(default_factory=EvaluationCriteriaDetails)
    submission_deadline: str = ""
    contact_info: str = ""


# =============================
# LLM Summarization
# =============================
def summarize_rfp(rfp_text: str, output_file_path: str = "./rfp_summary_output.json") -> RFPSummary:

    if not rfp_text:
        summary = RFPSummary()
        return summary

    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.0, api_key=OPENAI_API_KEY)
    structured_llm = llm.with_structured_output(RFPSummary)

    prompt = f"""
        أنت خبير في المشتريات والمناقصات.  
        لخص وثيقة طلب العروض (RFP) التالية إلى كائن JSON منظم مطابق تمامًا لنموذج Pydantic التالي:
        
        class EvaluationSubCriterion(BaseModel):
            name: str = Field(..., description="The name of the sub-criterion (e.g., 'القدرات الفنية (إدارة مرافق)', 'الخبرات_previous_experience_in_similar_field', weight: float = Field(0.0, ge=0.0, le=100.0, description="The weight/score of the sub-criterion (e.g., 30 for 30 points out of 70).")

        class EvaluationCriteriaDetails(BaseModel):
            technical_pass_mark: float = Field(70.0, ge=0.0, le=100.0, description="The minimum total score required to pass the technical evaluation (e.g., 70).")
            technical_criteria: list[EvaluationSubCriterion] = Field(default_factory=list, description="List of technical criteria with their individual scores/weights.")
            financial_evaluation_method: str = Field("lowest_price_among_qualified", description="How the financial evaluation is conducted after technical pass (e.g., 'lowest_price_among_qualified').")

        class RFPSummary(BaseModel):
            project_scope: str = Field(default="", description="Brief description of the project.")
            technical_requirements: list[str] = Field(default_factory=list, description="List of key technical requirements.")
            evaluation_criteria_details: EvaluationCriteriaDetails = Field(default_factory=EvaluationCriteriaDetails, description="Detailed evaluation criteria structure based on the provided text.")
            submission_deadline: str = Field(default="", description="Submission deadline if found.")
            contact_info: str = Field(default="", description="Contact information if found.")

        نص وثيقة طلب العروض:
        {rfp_text}

        أجب **بـ JSON صالح فقط** يطابق بنية RFPSummary وEvaluationCriteriaDetails وEvaluationSubCriterion. لا تستخدم تنسيق Markdown أو شرح خارجي.
        """

    try:
        summary_object: RFPSummary = structured_llm.invoke(prompt)
    except Exception as e:
        print(f"⚠️ LLM structured output failed: {e}")
        summary_object = RFPSummary(
            project_scope="فشل التلخيص تلقائيًا",
        )

    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(summary_object.model_dump_json(indent=2))

    return summary_object


def summarize_rfp_from_file(rfp_file_path: str, output_file_path: str = "./rfp_summary_output.json") -> RFPSummary:
    """
    Reads PDF using Railway and sends text to LLM summarizer.
    """
    if rfp_file_path.lower().endswith(".pdf"):
        text = read_pdf_text(rfp_file_path)
    else:
        with open(rfp_file_path, "r", encoding="utf-8") as f:
            text = f.read()

    return summarize_rfp(text, output_file_path)

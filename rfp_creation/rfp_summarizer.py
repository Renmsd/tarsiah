# -*- coding: utf-8 -*-
import json
import os
import re
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, MODEL_NAME
import requests

TIKA_URL = "https://tika-service-production.up.railway.app"  # النسخة النهائية


# Import for PDF reading


try:
    import pdfplumber
except ImportError:
    pdfplumber = None

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

def read_pdf_text(pdf_path: str) -> str:
    """
    Uses remote Apache Tika server deployed on Railway.
    If Tika fails → fallback to pdfplumber.
    """

    # --------- 1) Remote Tika extraction ---------
    try:
        with open(pdf_path, "rb") as f:
            response = requests.put(
                f"{TIKA_URL}/tika",
                data=f,
                headers={"Content-Type": "application/pdf"},
                timeout=90
            )

        if response.status_code == 200:
            text = response.text or ""
            if text.strip():
                text = text.replace("\r", "\n")
                text = text.replace("\x00", "").replace("\xa0", " ")
                text = text.replace("\x0c", "\n\n=== PAGE BREAK ===\n\n")
                return normalize_text(text)

        print(f"⚠️ Tika returned {response.status_code}, falling back to pdfplumber...")

    except Exception as e:
        print(f"⚠️ Remote Tika request failed: {e}")

    # --------- 2) pdfplumber fallback ---------
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is not installed.")
    
    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
                text_parts.append("\n\n=== PAGE BREAK ===\n\n")

        return normalize_text("".join(text_parts))

    except Exception as e:
        raise RuntimeError(f"pdfplumber failed to read the PDF: {e}")

# --- Pydantic Models for RFP Summary ---
class EvaluationSubCriterion(BaseModel):
    """Represents a sub-criterion within the technical evaluation."""
    name: str = Field(..., description="The name of the sub-criterion (e.g., 'القدرات الفنية (إدارة مرافق)', 'الخبرات السابقة في مجال عمل مشابه').")
    weight: float = Field(0.0, ge=0.0, le=100.0, description="The weight/score of the sub-criterion (e.g., 30 for 30 points out of 70).")

class EvaluationCriteriaDetails(BaseModel):
    """Represents the detailed evaluation criteria structure based on the provided text."""
    technical_pass_mark: float = Field(70.0, ge=0.0, le=100.0, description="The minimum total score required to pass the technical evaluation (e.g., 70).")
    technical_criteria: list[EvaluationSubCriterion] = Field(default_factory=list, description="List of technical criteria with their individual scores/weights.")
    financial_evaluation_method: str = Field("lowest_price_among_qualified", description="How the financial evaluation is conducted after technical pass (e.g., 'lowest_price_among_qualified').")

class RFPSummary(BaseModel):
    """Represents the structured summary of an RFP."""
    project_scope: str = Field(default="", description="Brief description of the project.")
    technical_requirements: list[str] = Field(default_factory=list, description="List of key technical requirements.")
    evaluation_criteria_details: EvaluationCriteriaDetails = Field(default_factory=EvaluationCriteriaDetails, description="Detailed evaluation criteria structure based on the provided text.")
    submission_deadline: str = Field(default="", description="Submission deadline if found.")
    contact_info: str = Field(default="", description="Contact information if found.")

# --- End Pydantic Models ---

def summarize_rfp(rfp_text: str, output_file_path: str = "./rfp_summary_output.json") -> RFPSummary:
    """
    Summarize RFP into structured JSON using LLM via with_structured_output.
    Saves the structured output to a file.
    Returns a Pydantic RFPSummary object.
    """
    if not rfp_text or not isinstance(rfp_text, str):
        summary_object = RFPSummary()
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                 f.write(summary_object.model_dump_json(indent=2))
            print(f"📄 تم حفظ ملخص RFP الافتراضي في '{output_file_path}'")
        except Exception as e:
             print(f"❌ خطأ في حفظ ملخص RFP الافتراضي: {str(e)}")
        return summary_object

    try:
        llm = ChatOpenAI(model=MODEL_NAME, temperature=0.0, api_key=OPENAI_API_KEY)
        structured_llm = llm.with_structured_output(RFPSummary)

        # Define the prompt specifically for structured output
        structured_prompt_text = f"""
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
            summary_object: RFPSummary = structured_llm.invoke(structured_prompt_text)
            print(f"--- DEBUG: Pydantic RFPSummary object created via structured output ---\n{summary_object.model_dump_json(indent=2)}\n--- END DEBUG ---")
        except Exception as e:
            print(f"⚠️ LLM failed to return structured output: {str(e)}")
            print("⚠️ Falling back to manual JSON parsing...")
            summary_object = RFPSummary(
                project_scope="فشل تلخيص كراسة الشروط تلقائيًا",
                evaluation_criteria_details=EvaluationCriteriaDetails(
                    technical_pass_mark=70.0,
                    technical_criteria=[
                        EvaluationSubCriterion(name="القدرات الفنية (إدارة مرافق)", weight=30.0),
                        EvaluationSubCriterion(name="الخبرات_previous_experience_in_similar_field", weight=20.0),
                        EvaluationSubCriterion(name="قدرات الفريق الفني", weight=20.0),
                        EvaluationSubCriterion(name="خطة إدارة المشروع", weight=20.0),
                        EvaluationSubCriterion(name="خطة إدارة المخاطر ومدة الاستجابة للمشاكل التقنية", weight=10.0),
                    ],
                    financial_evaluation_method="lowest_price_among_qualified"
                ) # default criteria based on provided text
            )

        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                 f.write(summary_object.model_dump_json(indent=2))
            print(f"📄 تم حفظ ملخص RFP المهيكل في '{output_file_path}'")
        except Exception as e:
             print(f"❌ خطأ في حفظ ملخص RFP: {str(e)}")

        return summary_object


    except Exception as e:
        print(f"⚠️ Failed to summarize RFP using structured output: {str(e)}")
        summary_object = RFPSummary(
            project_scope="فشل تلخيص كراسة الشروط تلقائيًا",
            evaluation_criteria_details=EvaluationCriteriaDetails(
                    technical_pass_mark=70.0,
                    technical_criteria=[
                        EvaluationSubCriterion(name="القدرات الفنية (إدارة مرافق)", weight=30.0),
                        EvaluationSubCriterion(name="الخبرات_previous_experience_in_similar_field", weight=20.0),
                        EvaluationSubCriterion(name="قدرات الفريق الفني", weight=20.0),
                        EvaluationSubCriterion(name="خطة إدارة المشروع", weight=20.0),
                        EvaluationSubCriterion(name="خطة إدارة المخاطر ومدة الاستجابة للمشاكل التقنية", weight=10.0),
                    ],
                    financial_evaluation_method="lowest_price_among_qualified"
                ) # default criteria based on provided text
        )

        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                 f.write(summary_object.model_dump_json(indent=2))
            print(f"📄 تم حفظ ملخص RFP الاحتياطي في '{output_file_path}'")
        except Exception as e:
             print(f"❌ خطأ في حفظ ملخص RFP الاحتياطي: {str(e)}")

        return summary_object

def summarize_rfp_from_file(rfp_file_path: str, output_file_path: str = "./rfp_summary_output.json") -> RFPSummary:
    """
    Summarize RFP from file path using enhanced PDF reading capabilities.
    """
    if rfp_file_path.lower().endswith('.pdf'):
        rfp_text = read_pdf_text(rfp_file_path)
    else:
        with open(rfp_file_path, 'r', encoding='utf-8') as f:
            rfp_text = f.read()
    
    return summarize_rfp(rfp_text, output_file_path)
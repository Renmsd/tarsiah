# evaluation_engine/evaluator.py
import json
import re
from typing import Dict, List, Optional, Any # Add Any
from pydantic import BaseModel
from langchain_openai import ChatOpenAI # Import ChatOpenAI instead of ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from utils.prompts import EVALUATION_PROMPT
# Import OpenAI API key and model name (changed variable name)
from config import OPENAI_API_KEY, MODEL_NAME

# --- Pydantic Models for Structured Output ---
class EvaluationScore(BaseModel):
    """Represents a single criterion's score."""
    criterion: str
    score: float  # 0-100

class EvaluationResult(BaseModel):
    """Represents the full evaluation result for a proposal."""
    scores: List[EvaluationScore]
    overall_comment: str
    raw_response: Optional[str] = None

# --- Pydantic Model for Comparison Log Entry ---
class ComparisonLogEntry(BaseModel):
    """Represents a single comparison log entry."""
    proposal_id: str
    criteria_list: str
    rfp_summary_preview: str
    proposal_text_preview: str
    llm_response: str

# --- End Pydantic Models ---

def extract_json_from_llm_output(text: str) -> str:
    """Extract JSON from LLM response, even if wrapped in Markdown."""
    # Look for JSON between ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    # If no markdown, try to find the first JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text.strip() # Return as is if no match

def evaluate_proposal(proposal_text: str, rfp_summary: dict, criteria_list: list) -> EvaluationResult:
    # Use ChatOpenAI instead of ChatGoogleGenerativeAI
    # Use OPENAI_API_KEY instead of google_api_key
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.0, api_key=OPENAI_API_KEY)
    prompt = PromptTemplate.from_template(EVALUATION_PROMPT)
    chain = prompt | llm

    # Add a safety check if criteria_list is empty
    if not criteria_list:
        print("⚠️ تحذير: قائمة المعايير فارغة.")
        criteria_list = ["السعر", "الجودة", "الجدول الزمني"] # Default fallback

    criteria_str = ", ".join(criteria_list)
    # Use json.dumps for better formatting of the rfp_summary dict
    rfp_summary_str = json.dumps(rfp_summary, indent=2) # Remove ensure_ascii=False
    response = chain.invoke({
        "rfp_summary": rfp_summary_str, # Pass the formatted JSON string
        "proposal_text": proposal_text,
        "criteria_list": criteria_str
    })

    # --- NEW LOGIC: Save the comparison details as structured JSON ---
    # Create a log entry object
    log_entry = ComparisonLogEntry(
        proposal_id="N/A", # This will be set later when the proposal ID is known
        criteria_list=criteria_str,
        rfp_summary_preview=rfp_summary_str[:500] + "...", # Truncate for preview
        proposal_text_preview=proposal_text[:1000] + "...", # Truncate for preview
        llm_response=response.content
    )
    # Create a log file for comparisons (append mode) - Save as JSON
    comparison_log_path = "./evaluation_comparisons.json" # Change extension to .json
    try:
        # Read existing log file if it exists
        existing_entries = []
        try:
            with open(comparison_log_path, 'r', encoding='utf-8') as log_file:
                content = log_file.read()
                if content: # Check if file is not empty
                    existing_entries = json.loads(content)
        except FileNotFoundError:
            pass # It's okay if the file doesn't exist yet

        # Append the new entry
        existing_entries.append(log_entry.model_dump())

        # Write the updated list back to the file
        with open(comparison_log_path, 'w', encoding='utf-8') as log_file:
            json.dump(existing_entries, log_file, indent=2, ensure_ascii=False) # Add ensure_ascii=False for writing JSON file
        print(f"📝 تفاصيل المقارنة لعرض تم حفظها في '{comparison_log_path}'")
    except Exception as e:
        print(f"❌ خطأ في حفظ تفاصيل المقارنة: {str(e)}")
    # --- END NEW LOGIC ---

    # DEBUG: Print the raw response from the LLM
    print(f"--- DEBUG: Raw LLM Response for a Proposal ---\n{response.content}\n--- END DEBUG ---")

    try:
        # Clean the response before parsing
        clean_response = extract_json_from_llm_output(response.content)
        parsed_data = json.loads(clean_response)

        # --- NEW LOGIC: Convert to Pydantic Model ---
        # Assuming the LLM returns JSON like {"scores": {"criterion1": 80, "criterion2": 90}, "overall_comment": "..."}
        raw_scores = parsed_data.get("scores", {})
        overall_comment = parsed_data.get("overall_comment", "No comment provided.")

        # Convert raw scores dict to list of EvaluationScore models
        score_objects = []
        for criterion, score_value in raw_scores.items():
            # Validate score is within expected range if necessary
            if not (0 <= score_value <= 100):
                 print(f"⚠️ تحذير: درجة غير صحيحة {score_value} ل criterion '{criterion}'. استخدام 0.")
                 score_value = 0.0
            score_obj = EvaluationScore(criterion=criterion, score=score_value)
            score_objects.append(score_obj)

        result = EvaluationResult(
            scores=score_objects,
            overall_comment=overall_comment,
            raw_response=response.content # Optionally store raw response
        )
        # --- END NEW LOGIC ---

        return result
    except json.JSONDecodeError as e:
        print(f"❌ خطأ في تحليل JSON من التقييم: {e}")
        print(f"❌ محتوى الاستجابة: {response.content}")
        # Return a default failure structure as a Pydantic model
        score_objects = [EvaluationScore(criterion=c, score=0.0) for c in criteria_list]
        return EvaluationResult(
            scores=score_objects,
            overall_comment="فشل التقييم بسبب خطأ في تنسيق الاستجابة.",
            raw_response=response.content
        )
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء معالجة التقييم: {e}")
        score_objects = [EvaluationScore(criterion=c, score=0.0) for c in criteria_list]
        return EvaluationResult(
            scores=score_objects,
            overall_comment="فشل التقييم بسبب خطأ غير معروف.",
            raw_response=response.content
        )

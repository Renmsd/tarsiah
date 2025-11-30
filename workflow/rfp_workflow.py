# workflow/rfp_workflow.py
from typing import TypedDict, Dict
import json  # Import json for saving at the top level
from pydantic import BaseModel  # Import BaseModel
from langgraph.graph import StateGraph, END
from rfp_creation.rfp_summarizer import summarize_rfp, RFPSummary  # Import RFPSummary
from proposal_ingestion.proposal_loader import load_proposals
from evaluation_engine.criteria_extractor import extract_criteria_from_rfp_summary  # This function now handles RFPSummary
from evaluation_engine.evaluator import evaluate_proposal, EvaluationResult  # Import the model
from evaluation_engine.ranker import rank_proposals
import os

# --- Pydantic Model for Parsed RFP ---
class ParsedRFP(BaseModel):
    """Represents the raw text extracted from the RFP file."""
    filename: str
    text: str

# --- End Pydantic Model ---

class AgentState(TypedDict):
    user_input: str
    proposals_dir: str
    rfp_summary: RFPSummary  # Change type hint to Pydantic model
    criteria_with_weights: list
    proposals: Dict[str, Dict[str, str]]
    scored_proposals: Dict[str, dict]  # Still stores dict for compatibility with ranker for now
    final_report: dict

def summarize_rfp_node(state: AgentState) -> AgentState:
    rfp_file_path = state["user_input"]
    if not os.path.isfile(rfp_file_path):
        raise FileNotFoundError(f"RFP file not found: {rfp_file_path}")

    if rfp_file_path.lower().endswith('.txt'):
        with open(rfp_file_path, 'r', encoding='utf-8') as f:
            rfp_text = f.read()
    else:
        from proposal_ingestion.document_parser import parse_document
        rfp_text = parse_document(rfp_file_path)
        # --- NEW LOGIC: Save parsed text as structured JSON ---
        parsed_rfp_obj = ParsedRFP(filename=os.path.basename(rfp_file_path), text=rfp_text)
        parsed_rfp_json_path = "./last_parsed_rfp.json"  # Change extension to .json
        try:
            # Use the json imported at the top level
            with open(parsed_rfp_json_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_rfp_obj.model_dump(), f, ensure_ascii=False, indent=2)  # Add indent for readability
            print(f"📄 تم حفظ النص المستخرج من RFP كـ JSON في '{parsed_rfp_json_path}'")
        except Exception as e:
            print(f"❌ خطأ في حفظ النص المستخرج من RFP كـ JSON: {str(e)}")
        # --- END NEW LOGIC ---

    # rfp_summary is now an RFPSummary object
    rfp_summary: RFPSummary = summarize_rfp(rfp_text)

    # Extract criteria with weights using the updated function
    criteria_with_weights = extract_criteria_from_rfp_summary(rfp_summary)

    # Return the Pydantic object and the criteria list
    return {"rfp_summary": rfp_summary, "criteria_with_weights": criteria_with_weights}

def ingest_proposals_node(state: AgentState) -> AgentState:
    proposals_dir = state.get("proposals_dir", "./proposals")
    print(f"📂 جاري تحميل العروض من: {proposals_dir}")
    proposals = load_proposals(proposals_dir)  # This now returns the new structure
    return {"proposals": proposals}

def evaluate_proposals_node(state: AgentState) -> AgentState:
    # Access the Pydantic object
    rfp_summary_obj: RFPSummary = state["rfp_summary"]
    # Convert it back to a dictionary for the evaluator prompt (for now)
    rfp_summary_dict = rfp_summary_obj.model_dump()  # Pydantic method to convert to dict

    proposals_with_details = state["proposals"]  # {pid: {"text": "...", "name": "..."}} # Extract criteria with weights (list of dicts)
    criteria_with_weights = state["criteria_with_weights"]

    # Extract just the names for passing to the evaluator
    criteria_names = [c["name"] for c in criteria_with_weights]

    print(f"🔍 جاري تقييم {len(proposals_with_details)} عرضًا مقابل كراسة الشروط باستخدام المعايير: {criteria_names}...")
    scored = {}
    for pid, details in proposals_with_details.items():
        text = details["text"]
        name = details["name"]

        if not text.strip():
            # Still store as dict for compatibility with ranker
            scored[pid] = {
                "name": name,
                "scores": {},
                "overall_comment": "العرض فارغ أو غير قابل للتحليل."
            }
            continue

        # Pass the list of names to evaluate_proposal - it now returns EvaluationResult
        evaluation_result: EvaluationResult = evaluate_proposal(text, rfp_summary_dict, criteria_names)  # Pass the dict version

        # Convert EvaluationResult back to a dictionary structure for the state
        # This maintains compatibility with the existing ranker which expects scores as a dict
        scores_dict = {score.criterion: score.score for score in evaluation_result.scores}

        score_result = {
            "scores": scores_dict,
            "overall_comment": evaluation_result.overall_comment
        }
        score_result["name"] = name  # Add the name back
        scored[pid] = score_result  # Store the dict version

    return {"scored_proposals": scored}

def rank_proposals_node(state: AgentState) -> AgentState:
    print("📊 جاري ترتيب العروض وفقًا للأداء...")
    # Get the criteria weights from the state
    criteria_with_weights = state.get("criteria_with_weights", [])
    # Pass them to rank_proposals
    ranked = rank_proposals(state["scored_proposals"], criteria_with_weights)
    return {"final_report": ranked}

def build_rfp_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("summarize_rfp", summarize_rfp_node)
    workflow.add_node("ingest_proposals", ingest_proposals_node)
    workflow.add_node("evaluate_proposals", evaluate_proposals_node)
    workflow.add_node("rank_proposals", rank_proposals_node)

    workflow.set_entry_point("summarize_rfp")
    workflow.add_edge("summarize_rfp", "ingest_proposals")
    workflow.add_edge("ingest_proposals", "evaluate_proposals")
    workflow.add_edge("evaluate_proposals", "rank_proposals")
    workflow.add_edge("rank_proposals", END)

    return workflow.compile()

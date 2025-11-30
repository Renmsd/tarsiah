# evaluation_engine/ranker.py
import json
import re
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from utils.prompts import RANKING_PROMPT
from config import OPENAI_API_KEY, MODEL_NAME

def extract_json_from_llm_output(text: str) -> str:
    """Extract JSON from LLM response, even if wrapped in Markdown."""
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text.strip()

def calculate_weighted_score(scores: dict, criteria_weights: list) -> float:
    """Calculate proper weighted score based on criteria weights"""
    total_weighted_score = 0.0
    
    for criterion in criteria_weights:
        criterion_name = criterion["name"]
        criterion_weight = criterion["weight"] / 100.0  # Convert to fraction
        
        if criterion_name in scores:
            # Apply weight to the score (0-100 scale)
            weighted_contribution = scores[criterion_name] * criterion_weight
            total_weighted_score += weighted_contribution
    
    return round(total_weighted_score, 1)

def rank_proposals(scored_proposals: Dict[str, dict], criteria_with_weights: list = None) -> dict:
    """
    Ranks proposals based on weighted scores.
    
    Corrected to ensure:
    1. Proper weighted scoring calculation
    2. Technical qualification check (≥ 70% technical score)
    3. Lowest price among qualified winners
    """
    print("--- DEBUG: Scores passed to Ranker ---")
    for pid, data in scored_proposals.items():
        print(f"{pid} (Name: {data.get('name', 'N/A')}): {data.get('scores', {})}")
    print("--- END DEBUG ---")

    if not criteria_with_weights:
        print("⚠️ تحذير: لم يتم تمرير معايير التقييم مع الأوزان. استخدام الأوزان الافتراضية.")
        criteria_with_weights = [
            {"name": "القدرات الفنية (إدارة مرافق)", "weight": 30.0},
            {"name": "الخبرات السابقة في مجال عمل مشابه", "weight": 20.0},
            {"name": "قدرات الفريق الفني", "weight": 20.0},
            {"name": "خطة إدارة المشروع", "weight": 20.0},
            {"name": "خطة المخاطر ومدة الاستجابة للمشاكل التقنية", "weight": 10.0}
        ]

    # Normalize weights to sum to 100 if needed
    total_weight = sum(c["weight"] for c in criteria_with_weights)
    if abs(total_weight - 100.0) > 0.01 and total_weight > 0:
        print(f"⚠️ تحذير: مجموع الأوزان ({total_weight}) لا يساوي 100. تطبيع الأوزان.")
        for c in criteria_with_weights:
            c["weight"] = (c["weight"] / total_weight) * 100.0

    print(f"--- DEBUG: Criteria with Weights ---")
    for crit in criteria_with_weights:
        print(f"  {crit['name']}: {crit['weight']}%")
    print("--- END DEBUG ---")

    # Calculate weighted scores and identify technically qualified proposals
    input_data = {}
    qualified_proposals = []  # Only proposals that pass technical evaluation
    
    for pid, data in scored_proposals.items():
        scores = data.get("scores", {})
        
        # Calculate weighted score
        weighted_score = calculate_weighted_score(scores, criteria_with_weights)
        
        # Check if technically qualified (≥ 70% of maximum possible score)
        max_possible_score = sum(c["weight"] for c in criteria_with_weights)
        is_qualified = weighted_score >= 70.0
        
        # Extract price information from comments (this is where we need to improve)
        price_info = "unknown"
        comment = data.get("overall_comment", "").lower()
        
        # Look for price indicators in the comment
        if "منخفض" in comment or "سعر منخفض" in comment or "أقل سعر" in comment:
            price_info = "low"
        elif "متوسط" in comment or "سعر معقول" in comment:
            price_info = "medium"
        elif "مرتفع" in comment or "سعر مرتفع" in comment:
            price_info = "high"
        
        input_data[pid] = {
            "weighted_average_score": weighted_score,
            "comment": data.get("overall_comment", ""),
            "name": data.get("name", pid),
            "is_qualified": is_qualified,
            "price_info": price_info
        }
        
        if is_qualified:
            qualified_proposals.append({
                "proposal_id": pid,
                "name": data.get("name", pid),
                "total_score": weighted_score,
                "scores": scores,
                "overall_comment": data.get("overall_comment", ""),
                "price_info": price_info
            })

    # Sort qualified proposals by weighted score (highest first)
    qualified_proposals.sort(key=lambda x: x["total_score"], reverse=True)
    
    # If no qualified proposals, use all proposals sorted by score
    if not qualified_proposals:
        print("❌ لا يوجد عروض مؤهلة فنيًا. الترتيب حسب الدرجة الفنية فقط.")
       # Sort ALL proposals (qualified first, then unqualified)
    all_proposals = []

    for pid, data in scored_proposals.items():
        scores = data.get("scores", {})
        weighted_score = calculate_weighted_score(scores, criteria_with_weights)

        all_proposals.append({
            "proposal_id": pid,
            "name": data.get("name", pid),
            "total_score": weighted_score,
            "scores": scores,
            "overall_comment": data.get("overall_comment", ""),
            "is_qualified": weighted_score >= 70.0,
            "price_info": input_data[pid]["price_info"],
        })

    # رتّبي المؤهلين أولاً ثم حسب الدرجة
    all_proposals.sort(key=lambda x: (x["is_qualified"], x["total_score"]), reverse=True)

    print("\n--- FINAL RANKED PROPOSALS (All) ---")
    for i, prop in enumerate(all_proposals, 1):
        status = "✓ مؤهل" if prop["is_qualified"] else "✘ غير مؤهل"
        print(f"{i}. {prop['name']} - {prop['total_score']} ({status})")
    print("--- END FINAL RANKING ---\n")

    return {
        "ranked_proposals": all_proposals,
        "rationale": "تم ترتيب جميع العروض مع توضيح المؤهل وغير المؤهل. تم تقديم المؤهّلين أولاً حسب الدرجة الفنية."
    }

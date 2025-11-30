import re
from typing import List, Dict, Optional
from rfp_creation.rfp_summarizer import RFPSummary, EvaluationCriteriaDetails, EvaluationSubCriterion
from utils.helpers import normalize_arabic_text
from utils.prompts import FOCUS_WINDOW_PROMPT
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, MODEL_NAME
import json

# Keywords to identify evaluation sections
KEYWORDS = [
    "تقييم العروض","المعايير الفنية","المعايير المالية","التقييم الفني",
    "آلية التقييم","آلية الترسية","درجة الاجتياز","الحد الأدنى","التمرير الفني",
    "الوزن","نسبة","النقاط","%",

    "الخطة الزمنية","البرنامج الزمني","الجدول الزمني",
    "خطة التنفيذ","الخطة الزمنية للتنفيذ","الخطة الزمنية للتشغيل",
    "الخطة الزمنية للإنشاء والتشغيل","الخطة الزمنية للإنشاء",
]
KW_PATTERN = re.compile("|".join([re.escape(k) for k in KEYWORDS]), re.IGNORECASE)

def extract_relevant_windows(full_text: str, radius_lines: int = 12) -> List[str]:
    """Extract focus windows around evaluation keywords"""
    lines = full_text.split("\n")
    windows = []
    for i, line in enumerate(lines):
        if KW_PATTERN.search(line):
            start = max(0, i - radius_lines)
            end   = min(len(lines), i + radius_lines + 1)
            windows.append(normalize_arabic_text("\n".join(lines[start:end])))
    return windows

def chunk_text_by_tokens(text: str, max_tokens: int = 4500) -> List[str]:
    """Simple token-based chunking (fallback without tiktoken)"""
    # Rough heuristic: 1 token ≈ 0.75 words
    words = text.split()
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for word in words:
        if len(word) > max_tokens * 0.75:  # Handle very long words
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_word_count = 0
            # Split very long word into smaller chunks
            for i in range(0, len(word), int(max_tokens * 0.75)):
                chunks.append(word[i:i + int(max_tokens * 0.75)])
        elif current_word_count + 1 > max_tokens * 0.75:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_word_count = 1
        else:
            current_chunk.append(word)
            current_word_count += 1
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def extract_criteria_with_llm(focused_chunks: List[str]) -> List[Dict]:
    """Extract criteria using LLM on focused chunks"""
    if not focused_chunks:
        return []
    
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.0, api_key=OPENAI_API_KEY)
    
    all_extracted_criteria = []
    
    for i, chunk in enumerate(focused_chunks, 1):
        prompt = FOCUS_WINDOW_PROMPT.format(
            chunk_num=i,
            total_chunks=len(focused_chunks),
            chunk_text=chunk
        )
        
        try:
            response = llm.invoke(prompt)
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    extracted = json.loads(json_str)
                    all_extracted_criteria.append(extracted)
                except json.JSONDecodeError:
                    print(f"⚠️ Failed to parse JSON from chunk {i}")
            else:
                print(f"⚠️ No JSON found in response for chunk {i}")
        except Exception as e:
            print(f"⚠️ Error processing chunk {i}: {e}")
    
    return all_extracted_criteria

def merge_extracted_criteria(partials: List[Dict]) -> Dict:
    """Merge criteria from multiple chunks"""
    passing = None
    financial_rule = None
    overall_mix = None
    tech_map = {}
    fin_map = {}

    for p in partials:
        if (passing is None) and (p.get("technical_passing_score") is not None):
            passing = p["technical_passing_score"]
        if (financial_rule is None) and p.get("financial_rule"):
            financial_rule = p["financial_rule"]
        if (overall_mix is None) and p.get("overall_mix"):
            overall_mix = p["overall_mix"]

        for c in p.get("technical_criteria", []):
            key = (c.get("name") or "").strip()
            if not key: continue
            if key not in tech_map:
                tech_map[key] = c
            else:
                mc = tech_map[key]
                if (mc.get("weight") is None) and (c.get("weight") is not None): 
                    mc["weight"] = c["weight"]
                if (mc.get("unit") is None) and (c.get("unit") is not None):   
                    mc["unit"] = c["unit"]
                if (mc.get("evidence") is None) and c.get("evidence"):          
                    mc["evidence"] = c["evidence"]
                tech_map[key] = mc

        for c in p.get("financial_criteria", []):
            key = (c.get("name") or "").strip()
            if not key: continue
            if key not in fin_map:
                fin_map[key] = c
            else:
                mc = fin_map[key]
                if (mc.get("weight") is None) and (c.get("weight") is not None): 
                    mc["weight"] = c["weight"]
                if (mc.get("unit") is None) and (c.get("unit") is not None):     
                    mc["unit"] = c["unit"]
                if (mc.get("evidence") is None) and c.get("evidence"):            
                    mc["evidence"] = c["evidence"]
                fin_map[key] = mc

    return {
        "technical_passing_score": passing,
        "technical_criteria": list(tech_map.values()),
        "financial_criteria": list(fin_map.values()),
        "financial_rule": financial_rule,
        "overall_mix": overall_mix
    }

def clean_and_split_criteria(extracted: Dict) -> Dict:
    """Clean extracted criteria by removing non-criteria items"""
    # Non-criteria hints to filter out
    non_criteria_hints = [
        "الضمان","الزكاة","الضرائب","ضريبة","السلامة","الصيانة","النظافة",
        "اشتراطات","سداد الأجرة","المستندات","السجلات","التراخيص",
        "نموذج العطاء","بيان الأسعار","غرامات","جزاءات","تأمين","تأمينات","إخلاء مسؤولية","التزامات",
    ]
    
    financial_name_hints = [
        "رأس المال", "سيولة", "السيولة", "ربحية", "الربحية", "مديون", "المديونية",
        "القوة المالية", "نسبة مالية", "ملاءة", "الملاءة"
    ]
    
    def is_non_criteria(name: str) -> bool:
        n = (name or "").strip()
        return any(h in n for h in non_criteria_hints)
    
    def is_financial_name(name: str) -> bool:
        n = (name or "").strip()
        return any(h in n for h in financial_name_hints)

    cleaned_tech = []
    fin_list = list(extracted.get("financial_criteria", []))

    for c in extracted.get("technical_criteria", []):
        if not c.get("name"): 
            continue
        if is_non_criteria(c["name"]):
            continue
        if c.get("weight") is None or c.get("unit") not in ("percent","points"):
            continue
        if is_financial_name(c["name"]):
            fin_list.append({
                "name": c["name"], 
                "weight": c["weight"], 
                "unit": c["unit"], 
                "evidence": c.get("evidence")
            })
            continue
        cleaned_tech.append(c)

    extracted["technical_criteria"] = cleaned_tech

    cleaned_fin = []
    for c in fin_list:
        if not c.get("name"):
            continue
        if is_non_criteria(c["name"]):
            continue
        if c.get("weight") is None or c.get("unit") not in ("percent","points"):
            continue
        cleaned_fin.append(c)
    extracted["financial_criteria"] = cleaned_fin

    return extracted

def dedupe_by_name(extracted: Dict) -> Dict:
    """Remove duplicate criteria by name"""
    def _dedupe(items):
        seen = {}
        for c in items:
            key = re.sub(r"\s+", " ", (c.get("name") or "").strip())
            if not key: 
                continue
            if key not in seen:
                seen[key] = c
            else:
                prev = seen[key]
                if prev.get("weight") is None and c.get("weight") is not None:
                    prev["weight"] = c["weight"]
                if prev.get("unit") is None and c.get("unit") is not None:
                    prev["unit"] = c["unit"]
                if prev.get("evidence") is None and c.get("evidence"):
                    prev["evidence"] = c["evidence"]
        return list(seen.values())

    extracted["technical_criteria"] = _dedupe(extracted.get("technical_criteria", []))
    extracted["financial_criteria"] = _dedupe(extracted.get("financial_criteria", []))
    return extracted

def try_fill_passing_score(extracted: Dict, full_text: str) -> Dict:
    """Try to extract passing score from full text if not found in focused chunks"""
    if extracted.get("technical_passing_score") is None:
        # Look for patterns like "passing score 70%" or "passing score 70 points"
        m = re.search(r"(?:اجتياز|تمرير|حد\s*الاجتياز)[^.\n]{0,50}?(\d{1,3})\s*%", full_text)
        if m:
            extracted["technical_passing_score"] = int(m.group(1))
        else:
            m2 = re.search(r"(\d{1,3})\s*%[^.\n]{0,60}(?:مجتاز|فوق|أعلى|فأعلى)", full_text)
            if m2:
                extracted["technical_passing_score"] = int(m2.group(1))
    return extracted

def enforce_financial_rule_and_mix(extracted: Dict, full_text: str) -> Dict:
    """Set default financial rule and mix if not found"""
    txt = full_text
    if not extracted.get("overall_mix"):
        if re.search(r"70\s*%[^.\n]{0,20}(?:فني|الفنية)", txt) and re.search(r"30\s*%[^.\n]{0,20}(?:مالي|المالية)", txt):
            extracted["overall_mix"] = {"technical": 70, "financial": 30}
    if not extracted.get("financial_rule"):
        extracted["financial_rule"] = "بعد اجتياز التقييم الفني (≥ 70%) يتم تقييم العروض المالية واختيار صاحب العرض المالي الأعلى"
    return extracted

def extract_criteria_from_rfp_summary(rfp_summary: RFPSummary, full_rfp_text: str = "") -> list: 
    """
    Extracts criteria names and weights from RFP summary Pydantic object.
    Uses the new 'evaluation_criteria_details' structure based on the provided text.
    Enhanced with focus windows and Tika-based extraction.
    """
    # rfp_summary is now an RFPSummary object
    details: EvaluationCriteriaDetails = rfp_summary.evaluation_criteria_details

    # Try enhanced extraction from full text first (if available)
    criteria_list = []
    if full_rfp_text:
        # Extract focus windows around evaluation keywords
        focus_windows = extract_relevant_windows(full_rfp_text, radius_lines=12)
        
        if focus_windows:
            # Chunk the focus windows
            chunks = []
            for window in focus_windows:
                chunks.extend(chunk_text_by_tokens(window, max_tokens=4500))
            
            if chunks:
                # Extract criteria using LLM
                extracted_criteria = extract_criteria_with_llm(chunks)
                if extracted_criteria:
                    # Merge and process extracted criteria
                    merged = merge_extracted_criteria(extracted_criteria)
                    merged = clean_and_split_criteria(merged)
                    merged = try_fill_passing_score(merged, full_rfp_text)
                    merged = enforce_financial_rule_and_mix(merged, full_rfp_text)
                    merged = dedupe_by_name(merged)
                    
                    # Convert to the format expected by the rest of the system
                    for tech_criterion in merged.get("technical_criteria", []):
                        criteria_list.append({
                            "name": tech_criterion["name"], 
                            "weight": tech_criterion.get("weight", 0.0)
                        })
    
    # If enhanced extraction didn't work, fall back to original method
    if not criteria_list:
        # Use the correct attribute name: 'technical_criteria'
        for sub_criterion in details.technical_criteria:
            criteria_list.append({"name": sub_criterion.name, "weight": sub_criterion.weight})

    # If no criteria found or weights don't sum to the pass mark (70), calculate or assign defaults
    total_weight = sum(c["weight"] for c in criteria_list)
    if total_weight != details.technical_pass_mark and total_weight > 0:
        print(f"⚠️ تحذير: مجموع أوزان المعايير الفنية ({total_weight}) لا يساوي علامة النجاح ({details.technical_pass_mark}). تaptic الأوزان.")
        for c in criteria_list:
            c["weight"] = (c["weight"] / total_weight) * details.technical_pass_mark
    elif total_weight == 0 and criteria_list:
         # Assign equal weights if no weights were provided
         total_weight = details.technical_pass_mark
         weight_per_criterion = total_weight / len(criteria_list)
         for c in criteria_list:
              c["weight"] = weight_per_criterion

    # If still no criteria found, use defaults
    if not criteria_list:
        print("⚠️ تحذير: قائمة المعايير فارغة. استخدام المعايير الافتراضية.")
        criteria_names = ["القدرات الفنية (إدارة مراف)", "الخبرات.previous_experience_in_similar_field", "قدرات الفريق الفني", "خطة إدارة المشروع", "خطة إدارة المخاطر ومدة الاستجابة للمشاكل التقنية"]
        total_weight = 70.0 # Default pass mark from provided text
        weight_per_criterion = total_weight / len(criteria_names)
        criteria_list = [{"name": name, "weight": weight_per_criterion} for name in criteria_names]

    return criteria_list
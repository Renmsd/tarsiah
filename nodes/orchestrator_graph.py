# nodes/orchestrator_graph.py
from langgraph.graph import StateGraph, START, END
from datetime import datetime, timedelta
from typing import TypedDict, Annotated
from nodes.field_map import FIELD_MAP
import operator
import asyncio
from concurrent.futures import ThreadPoolExecutor

# ---------------------------
# ✅ تعريف الحالة العامة للـ Graph
# ---------------------------
class State(TypedDict):
    raw_input: str
    decisions: dict
    sections: list[str]
    completed_sections: Annotated[list, operator.add]


# ---------------------------
# ✅ تواريخ تلقائية (الجدول الزمني)
# ---------------------------
def generate_auto_dates(issue_date: str | None):
    """
    إذا المستخدم أدخل Issue_Date → نحسب التواريخ بناءً عليها,
    إذا لم يدخل → نستخدم تاريخ اليوم.
    """
    if issue_date:
        base = datetime.strptime(issue_date, "%Y-%m-%d")
    else:
        base = datetime.today()

    return {
        "Issue_Date": base.strftime("%Y-%m-%d"),
        "Participation_Confirmation_Letter": (base + timedelta(days=2)).strftime("%Y-%m-%d"),
        "Submission_of_Questions_and_Inquiries": (base + timedelta(days=5)).strftime("%Y-%m-%d"),
        "Submission_of_Proposals": (base + timedelta(days=10)).strftime("%Y-%m-%d"),
        "Opening_of_Proposals": (base + timedelta(days=11)).strftime("%Y-%m-%d"),
        "Award_Decision_Date": (base + timedelta(days=17)).strftime("%Y-%m-%d"),
        "Commencement_of_Work": (base + timedelta(days=30)).strftime("%Y-%m-%d"),
    }



# ---------------------------
# ✅ استدعاء LLM (متوافق sync/async)
# ---------------------------
async def _call_llm_async(llm, prompt):
    if hasattr(llm, "ainvoke"):
        try:
            result = await llm.ainvoke(prompt)
            return getattr(result, "content", result).strip()
        except Exception:
            pass

    loop = asyncio.get_running_loop()

    def sync():
        try:
            result = llm.invoke(prompt)
            return getattr(result, "content", result).strip()
        except Exception:
            return "تعذر توليد الفقرة بسبب خطأ تقني."

    return await loop.run_in_executor(ThreadPoolExecutor(max_workers=6), sync)


# ---------------------------
# ✅ orchestrator: يحضّر البيانات واختيار ال sections
# ---------------------------
def orchestrator(state: State):
    from flask import session

    # ✅ يجب أن يكون لدينا decisions
    state.setdefault("decisions", {})
    decisions = state["decisions"]

    # ✅ raw_input يأتي من run_graph(user_data)
    raw = state.get("raw_input")

    # ✅ إذا raw dict → ندمجه مباشرة
    if isinstance(raw, dict):
        decisions.update(raw)

    # ✅ إذا raw string JSON → نحوله ونضيفه
    elif isinstance(raw, str):
        try:
            import json
            decisions.update(json.loads(raw))
        except Exception:
            pass
    # ✅ ضمان وجود مفاتيح الجزاءات حتى لو المستخدم ما اختار شيء
    for key in ["Penalty_Deduction", "Penalty_Execute_On_Vendor", "Penalty_Suspend", "Penalty_Termination"]:
        decisions.setdefault(key, "")


    # ✅ تواريخ تلقائية
    issue_date_input = decisions.get("Issue_Date")
    decisions.update(generate_auto_dates(issue_date_input))

    # ✅ تحكم الأقسام اختيارية حسب checkbox
    include = session.get("include_sections", {})
    sections = []

    for key, v in FIELD_MAP.items():
        if v == "llm":
            # إذا القسم اختياري ولم يتم تفعيله → تجاهله
            if key in include and not include[key]:
                print(f"🚫 SKIP section: {key}")
                continue

            sections.append(key)
        # ✅ Inject raw_input into decisions so PROMPTS can use {raw_input}
    decisions["raw_input"] = state.get("raw_input")


    return {
        "sections": sections,
        "decisions": decisions
    }



# ---------------------------
# ✅ توليد كل الفقرات (بالتوازي للسرعة)
# ---------------------------
# ---------------------------
# ✅ توليد كل الفقرات (بالتوازي للسرعة) + DEBUG
# ---------------------------
def generate_all_sections(state, llm):
    from flask import session

    state.setdefault("decisions", {})
    d = state["decisions"]
    sections = state.get("sections", [])

    # ✅ DEBUG — عرض البيانات التي تصل للـ LLM
    print("\n============================")
    print("✅ DEBUG | Decisions sent to LLM:")
    for k, v in d.items():
        print(f" - {k}: {v}")
    print("============================\n")

    from nodes.prompts import PROMPTS

    async def _parallel_generate():
        tasks, keys = [], []

        for sec in sections:
            if sec in PROMPTS:
                prompt = PROMPTS[sec].format(**d)

                # ✅ DEBUG — طباعة البرومبت الفعلي قبل الإرسال
                print(f"\n🟦 Generating section: {sec}")
                print("🔹 Final Prompt Sent to LLM:\n")
                print(prompt)
                print("---------------------------------------------------\n")

                tasks.append(_call_llm_async(llm, prompt))
                keys.append(sec)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for sec, result in zip(keys, results):
            d[sec] = result if isinstance(result, str) else "تعذر توليد النص."

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_parallel_generate())
    loop.close()

    return {"decisions": d}



# ---------------------------
# ✅ synthesize output
# ---------------------------
def synthesizer(state):
    return {"decisions": state.get("decisions", {})}


# ---------------------------
# ✅ build graph
# ---------------------------
def build_orchestrator_graph(llm):
    g = StateGraph(State)
    g.add_node("orchestrator", orchestrator)
    g.add_node("generate_all_sections", lambda s: generate_all_sections(s, llm))
    g.add_node("synthesizer", synthesizer)

    g.add_edge(START, "orchestrator")
    g.add_edge("orchestrator", "generate_all_sections")
    g.add_edge("generate_all_sections", "synthesizer")
    g.add_edge("synthesizer", END)

    return g.compile()

#graph1.py
from nodes.orchestrator_graph import build_orchestrator_graph
from nodes.render_node import render_node
from langgraph.graph import StateGraph,START, END
from typing import TypedDict
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json

# ============================================================
# 🧠 تحميل المتغيرات البيئية (API Keys)
# ============================================================
load_dotenv()

# ============================================================
# 🤖 إعداد النموذج
# ============================================================
llm = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0.3
)

def get_llm():
    return llm

orchestrator_graph = build_orchestrator_graph(llm)

def build_main_app():
    g = StateGraph(dict)

    # ✅ return the WHOLE dict from orchestrator_graph, not just decisions
    def generate_node(state):
        state.setdefault("decisions", {})
        result = orchestrator_graph.invoke(state)
        # merge back into state so render_node receives {"decisions": {...}, ...}
        state.update(result or {})
        return state

    g.add_node("generate", generate_node)
    g.add_node("render", render_node)

    g.add_edge(START, "generate")
    g.add_edge("generate", "render")
    g.add_edge("render", END)
    return g.compile()

app = build_main_app()

def run_graph(user_data: dict):
    """
    ✅ استدعاء LangGraph بشكل صحيح وتمرير الـ user input في raw_input
    """
    print("⚙️ تشغيل LangGraph...")
    print("🔥 USER DATA RECEIVED BY GRAPH:", user_data)

    initial_state = {
        "raw_input": user_data,    # ← هنا ندخل بيانات المستخدم
        "decisions": {},           # ← يملؤها orchestrator
        "sections": [],            # ← ليتم تعبئتها بناءً على الـ FIELD_MAP
        "completed_sections": []   # ← مطلوب من StateGraph
    }

    result = {}

    try:
        for event in app.stream(initial_state):  # ✅ لا تمريّرس messages هنا
            for value in event.values():
                result.update(value)
    except Exception as e:
        print("❌ خطأ أثناء تشغيل LangGraph:", e)

    return result










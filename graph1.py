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
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ لم يتم العثور على OPENAI_API_KEY في ملف .env")

# ============================================================
# 🤖 إعداد النموذج
# ============================================================
llm = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0.3,
    api_key=api_key
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
    🔹 دالة بسيطة لاستدعاء LangGraph من Flask
    """
    print("⚙️ تشغيل LangGraph...")
    result = {}
    try:
        for event in app.stream({"messages": [("user", str(user_data))]}):
            for value in event.values():
                result.update(value)
    except Exception as e:
        print("❌ خطأ أثناء تشغيل LangGraph:", e)
    return result







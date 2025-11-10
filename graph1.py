# ========================= graph1.py =========================
from nodes.orchestrator_graph import build_orchestrator_graph
from nodes.render_node import render_node

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from flask import stream_with_context, Response
import os
import json


# ============================================================
# 🧠 تحميل المتغيرات البيئية (API Keys)
# ============================================================
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ لم يتم العثور على OPENAI_API_KEY في ملف .env")


# ============================================================
# 🤖 إعداد الـ LLM
# ============================================================
llm = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0.3,
    api_key=api_key,
)

orchestrator_graph = build_orchestrator_graph(llm)


# ============================================================
# 🔧 العقدة المسؤولة عن التوليد — بإستخدام STREAM 🔥
# ============================================================
def generate_node(state: dict):
    state.setdefault("decisions", {})

    # ✅ Streaming from orchestrator_graph (بدلاً من invoke)
    for event in orchestrator_graph.stream(state):
        for key, value in event.items():
            state[key] = value  # keep merging into state

    return state


# ============================================================
# 🏗️ Build Main Graph
# ============================================================
def build_main_app():
    g = StateGraph(dict)

    g.add_node("generate", generate_node)
    g.add_node("render", render_node)

    g.add_edge(START, "generate")
    g.add_edge("generate", "render")
    g.add_edge("render", END)

    return g.compile()


app = build_main_app()


# ============================================================
# 🚀 Streaming output to Flask
# ============================================================
def run_graph(user_data: dict):
    print("⚙️ Streaming LangGraph execution...")

    # ✅ app.stream returns events incrementally, do NOT block
    for event in app.stream({"messages": [("user", json.dumps(user_data, ensure_ascii=False))]}):
        yield event  # sen

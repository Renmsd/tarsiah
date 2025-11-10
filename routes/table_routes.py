from flask import Blueprint, jsonify, request, session
from langchain_openai import ChatOpenAI  # type: ignore
from graph1 import run_graph, llm  # type: ignore
import os
from dotenv import load_dotenv
load_dotenv()
table_bp = Blueprint("table_bp", __name__)

api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ لم يتم العثور على OPENAI_API_KEY في ملف .env")


def generate_table_from_text(user_input: str):
    llm_instance = ChatOpenAI(model="gpt-5-mini", temperature=0.3, api_key=api_key)

    prompt = f"""
        أنت مساعد ذكي متخصص في استخراج الجداول من النصوص العربية.

        🔹 المهمة:
        حلّل الوصف التالي واستخرج منه جدولًا منظمًا يحتوي على الأعمدة المناسبة بناءً على نوع البيانات الموجودة.
        يجب أن تُحدَّد أسماء الأعمدة تلقائيًا حسب النص فعليًا فقط.

        🔹 التنسيق المطلوب:
        - استخدم الفاصل العمودي (|).
        - السطر الأول يحتوي على العناوين.
        - الأسطر التالية هي البيانات.
        - لا تضف أي شرح أو نص آخر.

        الوصف:
        {user_input}
        """

    result = llm_instance.invoke([("user", prompt)])
    table_text = result.content.strip()

    lines = [l.strip() for l in table_text.split("\n") if "|" in l]
    headers = [h.strip() for h in lines[0].split("|")]
    rows = [l.split("|") for l in lines[1:]]

    html = "<table border='1' style='border-collapse:collapse;width:100%;text-align:center;'>"
    html += "<thead><tr>" + "".join([f"<th>{h}</th>" for h in headers]) + "</tr></thead><tbody>"

    for r in rows:
        html += "<tr>" + "".join([
            f"<td><input value='{c.strip().replace('<','&lt;').replace('>','&gt;')}' "
            f"style='width:100%;border:none;text-align:center;'></td>"
            for c in r
        ]) + "</tr>"

    html += "</tbody></table>"

    plain_text = "|".join(headers) + "\n" + "\n".join(["|".join(r) for r in rows])
    return html, plain_text


# ============================================================
# ✅ جدول الكميات والأسعار
# ============================================================
@table_bp.route("/generate_table/quantities", methods=["POST"])
def generate_quantities():
    data = request.get_json()
    text = data.get("text", "").strip() if data else ""
    if not text:
        return jsonify({"error": "النص فارغ."})
    html, plain_text = generate_table_from_text(text)
    session["Bill_of_Quantities_and_Prices"] = plain_text
    return jsonify({"html": html})


# ============================================================
# ✅ جدول المواد
# ============================================================
@table_bp.route("/generate_table/materials", methods=["POST"])
def generate_materials():
    data = request.get_json()
    text = data.get("text", "").strip() if data else ""
    if not text:
        return jsonify({"error": "النص فارغ."})
    html, plain_text = generate_table_from_text(text)
    session["Materials_Specifications_Table"] = plain_text
    return jsonify({"html": html})


# ============================================================
# ✅ جدول المعدات
# ============================================================
@table_bp.route("/generate_table/equipment", methods=["POST"])
def generate_equipment():
    data = request.get_json()
    text = data.get("text", "").strip() if data else ""
    if not text:
        return jsonify({"error": "النص فارغ."})
    html, plain_text = generate_table_from_text(text)
    session["Equipment_Specifications_Table"] = plain_text
    return jsonify({"html": html})


# ============================================================
# 🆕 ✅ جدول العمال (هام)
# ============================================================
@table_bp.route("/generate_table/workers", methods=["POST"])
def generate_workers():
    data = request.get_json()
    text = data.get("text", "").strip() if data else ""
    if not text:
        return jsonify({"error": "النص فارغ."})
    html, plain_text = generate_table_from_text(text)
    session["Workers_Table"] = plain_text   # ✅ تخزين الجداول في session
    return jsonify({"html": html})


# ============================================================
# ✅ حفظ أي جدول من الصفحة
# ============================================================
@table_bp.route("/save_table", methods=["POST"])
def save_table():
    data = request.get_json()
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    table_name = data.get("table_name", "Bill_of_Quantities_and_Prices")
    plain_text = "|".join(headers) + "\n" + "\n".join(["|".join(r) for r in rows])

    session[table_name] = plain_text
    return jsonify({"message": f"✅ تم حفظ الجدول '{table_name}' بنجاح في الجلسة."})

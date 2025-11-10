# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, render_template, request, send_file, jsonify, session, Response, stream_with_context
from docxtpl import DocxTemplate
from datetime import datetime
from graph1 import run_graph, llm
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from typing import Optional

app = Flask(__name__)
app.secret_key = "smart-rfp-ai-key"

from routes.table_routes import table_bp
app.register_blueprint(table_bp)


def fix_rtl_bullets(text: str) -> str:
    if not isinstance(text, str):
        return text
    rtl_start = "\u202B"
    rtl_end = "\u202C"
    replacements = {"•": f"{rtl_start}•{rtl_end}", "-": f"{rtl_start}-{rtl_end}"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/rfp_input')
def rfp_input():
    return render_template('rfp_input.html')


# ✅ STREAMING GENERATION HERE
@app.route('/rfp_generate', methods=['POST'])
def generate():

    user_data = request.form.to_dict(flat=False)
    for key, value in user_data.items():
        if isinstance(value, list):
            user_data[key] = "، ".join(value)

    include_sections = {
        "Joint_Venture": request.form.get("include_Joint_Venture") is not None,
        "Tender_Split_Section": request.form.get("include_Tender_Split_Section") is not None,
        "Alternative_Offers": request.form.get("include_Alternative_Offers") is not None,
        "Insurance": request.form.get("include_Insurance") is not None,
    }
    session["include_sections"] = include_sections

    def stream_events():
        for event in run_graph(user_data):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(stream_events()), mimetype="text/event-stream")


@app.route('/save', methods=['POST'])
def save():
    session_user = session.get("user_data", {})
    session_llm = session.get("decisions", {})
    edited_data = request.form.to_dict()
    context = {**session_user, **session_llm, **edited_data}

    tpl = DocxTemplate("templates/rfp_general.docx")

    TABLE_KEYS = {
        "Bill_of_Quantities_and_Prices",
        "Materials_Specifications_Table",
        "Equipment_Specifications_Table",
        "Workers_Table",
    }
    safe_context = {k: v for k, v in context.items() if k not in TABLE_KEYS}

    llm_fields = {
        "Competition_Definition",
        "Text_of_Costs_of_Competition_Documents",
        "Project_Scope_of_Work",
        "Technical_Proposal_Documents",
        "Financial_Proposal_Documents",
        "Bid_Evaluation_Criteria",
        "Regulatory_Records_and_Licenses",
        "Inquiries_Section",
        "Tender_Split_Section",
        "Penalties",
        "Delay_Penalties",
        "Insurance",
        "Service_Delivery_Plan",
        "Service_Execution_Method",
        "Alternative_Offers",
    }

    for key in list(safe_context.keys()):
        if key in llm_fields and isinstance(safe_context[key], str):
            safe_context[key] = fix_rtl_bullets(safe_context[key])

    tpl.render(safe_context)
    output_folder = os.path.join(os.path.expanduser("~"), "Documents", "RFP_outputs")
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_folder, f"filled_{timestamp}.docx")
    tpl.save(output_path)

    project_name = context.get("Competition_Name") or "مشروع بدون اسم"
    session["generated_file"] = output_path
    return render_template("result.html", project_name=project_name, download_url="/download")


@app.route('/download')
def download_file():
    file_path = session.get("generated_file")
    if not file_path or not os.path.exists(file_path):
        return "⚠️ الملف غير موجود. يرجى إعادة التوليد.", 404
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)

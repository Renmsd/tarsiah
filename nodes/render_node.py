# nodes/render_node.py
from docxtpl import DocxTemplate
from datetime import datetime
import os

def render_node(state):
    os.makedirs("output", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"output/filled_{ts}.docx"

    decisions = state.get("decisions", {})
    if not isinstance(decisions, dict) or not decisions:
        print("⚠️ No decisions found to render.")
        return {"render": {"status": "empty", "outputs_file": None}}

    print("🧠 Render context keys:", list(decisions.keys()))
    
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))  # يرجع لمجلد المشروع الرئيسي
        template_path = os.path.join(base_dir, "templates", "rfp_general.docx")

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"❌ قالب Word غير موجود في: {template_path}")

        print(f"📂 تم العثور على القالب في: {template_path}")

        doc = DocxTemplate(template_path)
  # يرجع لمجلد المشروع الرئيسي

        doc.render(decisions)
        doc.save(output_path)
        print(f"✅ Document generated: {output_path}")
        return {"render": {"status": "success", "outputs_file": output_path}}
    except Exception as e:
        print(f"❌ Render error: {e}")
        return {"render": {"status": f"error: {e}", "outputs_file": None}}

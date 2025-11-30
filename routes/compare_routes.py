from flask import Blueprint, request, jsonify
import os, shutil, stat
from werkzeug.utils import secure_filename
from workflow.rfp_workflow import build_rfp_graph
import time
import uuid

compare_bp = Blueprint("compare_bp", __name__)

@compare_bp.route("/compare_llm", methods=["POST"])
def compare_llm():
    try:
        upload_dir = "uploads"
        proposals_dir = os.path.join(upload_dir, "proposals")

        def handle_remove_readonly(func, path, exc_info):
            os.chmod(path, stat.S_IWRITE)
            func(path)

        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir, onerror=handle_remove_readonly)
        os.makedirs(proposals_dir, exist_ok=True)

        # 🟣 كراسة الشروط
        rfp_file = request.files["rfp_file"]
        rfp_filename = secure_filename(rfp_file.filename or f"RFP_{int(time.time())}.pdf")
        rfp_path = os.path.join(upload_dir, rfp_filename)
        with open(rfp_path, "wb") as f:
            rfp_file.stream.seek(0)
            shutil.copyfileobj(rfp_file.stream, f)
        print(f"✅ تم حفظ كراسة الشروط في: {rfp_path}")

        # 🟢 العروض
        proposal_files = request.files.getlist("proposal_files")
        proposal_names = []              # ← أسماء الملفات بعد الحفظ
        proposal_original_names = []     # ⭐ الأسماء الأصلية كما رفعها المستخدم

        for idx, file in enumerate(proposal_files, start=1):
            
            original_name = file.filename                 # ← الاسم الأصلي 100%
            proposal_original_names.append(original_name) # ← نحفظه لواجهة HTML

            filename = original_name                      # ← نترك الاسم كما هو

            # ضمان وجود امتداد PDF
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"

            # حفظ الملف بنفس اسمه الأصلي دون أي تغيير
            save_path = os.path.join(proposals_dir, filename)
            file.save(save_path)

            proposal_names.append(filename)

            print(f"📄 تم حفظ العرض بنفس اسمه الأصلي: {filename}")

        if not proposal_names:
            return jsonify({"error": "⚠️ لم يتم رفع أي ملفات عروض صالحة."}), 400

        print(f"✅ تم حفظ {len(proposal_names)} عرض بنجاح.")

        # 🧠 تشغيل Workflow
        graph = build_rfp_graph()
        inputs = {"user_input": rfp_path, "proposals_dir": proposals_dir}
        state = graph.invoke(inputs)

        final_report = state.get("final_report", None)
        all_results = []

        if isinstance(final_report, list):
            for item in final_report:
                all_results.append(item if isinstance(item, dict) else {"details": str(item)})
        elif isinstance(final_report, dict):
            all_results.append(final_report)

        expanded_results = []
        for idx, r in enumerate(all_results):

            if isinstance(r, dict) and "ranked_proposals" in r:
                for i, sub in enumerate(r["ranked_proposals"]):
                    expanded_results.append({
                        "proposal_name": sub.get("name"),
                        "scores": [{"criterion": k, "score": float(v)} for k, v in sub.get("scores", {}).items()],
                        "details": sub.get("overall_comment", "لا يوجد تعليق."),
                        "total_score": sub.get("total_score", 0)
                    })
            elif isinstance(r, dict):
                expanded_results.append({
                    "proposal_name": proposal_original_names[idx],     # ← الاسم الأصلي
                    "scores": [{"criterion": k, "score": v} for k, v in (r.get("scores") or {}).items()],
                    "details": r.get("details") or r.get("overall_comment") or "لا يوجد تعليق.",
                    "total_score": r.get("total_score", 0)
                })

            else:
                expanded_results.append({
                    "proposal_name": sub.get("name"),
                    "scores": [{"criterion": k, "score": float(v)} for k, v in sub.get("scores", {}).items()],
                    "details": sub.get("overall_comment", "لا يوجد تعليق."),
                    "total_score": sub.get("total_score", 0)
                })
            print(f"✅ تم استخراج {len(expanded_results)} نتيجة جاهزة للعرض.")

        # 🔥 ترتيب حسب الدرجة — نفس المنطق
        expanded_results = sorted(expanded_results, key=lambda x: x.get("total_score", 0), reverse=True)

        return jsonify({"results": expanded_results, "total_uploaded": len(proposal_names)}), 200

    except Exception as e:
        import traceback
        print("❌ Error in /compare_llm:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

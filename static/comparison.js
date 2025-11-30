// ===============================
// 📊 تشغيل المقارنة وعرض النتائج (النسخة النهائية الثابتة)
// ===============================
document.getElementById("compareForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const formEl = document.getElementById("compareForm");
  const formData = new FormData();
  formData.delete("proposal_files"); // 🔥 حذف أي ملفات قديمة
  formData.delete("rfp_file");

  // ✅ إصلاح bug تفريغ الملفات في بعض المتصفحات
  const rfpFile = document.getElementById("rfp_file").files[0];
  const proposals = document.getElementById("proposal_files").files;

  if (rfpFile) formData.append("rfp_file", rfpFile);
  if (proposals.length > 0) {
    for (let file of proposals) formData.append("proposal_files", file);
  }


  console.log("📦 الملفات الجاهزة للإرسال:");
  for (let [key, value] of formData.entries()) {
    console.log(key, value);
  }

  const introBox = document.getElementById("intro-box");
  const resultsSection = document.getElementById("results-section");

  introBox.style.display = "none";
  resultsSection.innerHTML = "<p style='text-align:center;color:#0f3d61;'> جاري تحليل العروض باستخدام AI الرجاء الانتظار...</p>";
  resultsSection.style.display = "block";

  try {
    const response = await fetch("/compare_llm", { method: "POST", body: formData });
    const data = await response.json();
    resultsSection.innerHTML = "";
    console.log("✅ البيانات المستلمة:", data);

    if (data.error) {
      resultsSection.innerHTML = `<p style='color:red;text-align:center;'>⚠️ ${data.error}</p>`;
      return;
    }

    // 🧩 دمج النتائج مع المبررات (في حال وجودها)
    let results = [];

    if (data.ranked_proposals && Array.isArray(data.ranked_proposals)) {
      results = data.ranked_proposals.map((r) => ({
        proposal_name: r.name || r.proposal_id || "عرض بدون اسم",
        total_score: r.total_score || 0,
        scores: r.scores || {},
        details: r.overall_comment || "",
      }));

      if (data.rationale) {
        results.push({
          proposal_name: "📘 مبررات التقييم",
          details: data.rationale,
          total_score: "",
          scores: [],
        });
      }
    } else if (Array.isArray(data.results)) {
      results = data.results;
    }

    const totalUploaded = data.total_uploaded || results.length;

    if (totalUploaded > results.length) {
      resultsSection.innerHTML += `
        <p style="color:#a33;text-align:center;font-weight:bold;">
          ⚠️ تم تحليل ${results.length} من أصل ${totalUploaded} ملفات مرفوعة.
        </p>`;
    }

    if (results.length === 0) {
      resultsSection.innerHTML += "<p style='color:#666;text-align:center;'>لم يتم العثور على نتائج.</p>";
      return;
    }

    resultsSection.innerHTML += `<h2 style="text-align:center;color:#003366;margin-bottom:20px;">نتائج مقارنة العروض</h2>`;

      // 🔥 ترتيب النتائج حسب الدرجة من الأعلى إلى الأقل قبل عرضها
    results.sort((a, b) => (b.total_score || 0) - (a.total_score || 0));


    // ===============================
    // 🟦 إنشاء بطاقات النتائج
    // ===============================
    results.forEach((item, i) => {
      if (typeof item === "string") {
        try {
          item = JSON.parse(item);
        } catch {
          item = { proposal_name: "عرض غير معروف", details: item };
        }
      }

      let name = item.proposal_name || item.name || "عرض بدون اسم";
      name = name.replace(/\.[^/.]+$/, ""); // يحذف الامتداد

      const total = parseFloat(item.total_score || 0);
      const isRationale = name.includes("مبررات");
      const qualified = total >= 70; // ✅ المؤهل فنياً

      const card = document.createElement("div");
      card.className = "proposal-card";

      if (isRationale) {
        card.classList.add("rationale-card");
      } else if (qualified) {
        card.style.borderTop = "5px solid #3cb371"; // ✅ مؤهل
      } else {
        card.style.borderTop = "5px solid #e74c3c"; // ❌ غير مؤهل
      }

      const title = document.createElement("h3");
      title.innerHTML = `${i + 1}. ${name}
        <span style="color:#0056b3;font-size:15px;">
          ${!isNaN(total) && total > 0 ? `(${total}/100)` : ""}
        </span>`;
      card.appendChild(title);

      // 📘 مبررات التقييم
      if (isRationale) {
        card.innerHTML += `
          <p class="rationale-text">
            <b>📘 مبررات التقييم:</b><br>${item.details || "لا توجد مبررات."}
          </p>`;
        resultsSection.appendChild(card);
        return;
      }

      // 📊 جدول الدرجات
      const table = document.createElement("table");
      table.className = "summary-table";
      const scores = Array.isArray(item.scores)
        ? item.scores
        : typeof item.scores === "object"
        ? Object.entries(item.scores).map(([k, v]) => ({ criterion: k, score: v }))
        : [];

      let scoreRows = "";
      scores.forEach(s => {
        scoreRows += `<tr><td>${s.criterion}</td><td>${s.score}</td></tr>`;
      });

      table.innerHTML = `<tr><th>المعيار</th><th>الدرجة</th></tr>${scoreRows}`;
      card.appendChild(table);

      // 💬 التعليق العام
      // 🔽 زر السهم داخل دائرة — مخفي حتى تمرير الماوس
      const toggleBtn = document.createElement("div");
      toggleBtn.className = "toggle-btn";
      toggleBtn.addEventListener("click", () => {
      commentBox.classList.toggle("hidden");
      toggleBtn.classList.toggle("open");
      });

      // صندوق التعليق (مخفي)
      const commentBox = document.createElement("div");
      commentBox.className = "comment-box hidden";
      commentBox.innerHTML = `
        <p class="overall-comment">
          <strong>💬 التعليق:</strong> ${item.details}
        </p>
      `;

      // عند الضغط على السهم
  

      // إضافة السهم + صندوق التعليق
      card.appendChild(toggleBtn);
      card.appendChild(commentBox);


      // ✅ شارة الحالة
      const badge = document.createElement("div");
      badge.className = "status-badge";
      badge.textContent = qualified ? "✅ مؤهل فنياً" : "❌ لم يجتز التقييم الفني";
      badge.style.backgroundColor = qualified ? "#3cb371" : "#e74c3c";
      card.appendChild(badge);

      resultsSection.appendChild(card);
    });
  } catch (err) {
    console.error("❌ Error:", err);
    resultsSection.innerHTML = `<p style='color:red;text-align:center;'>حدث خطأ أثناء التحليل.</p>`;
  }
});

// ===============================
// 💅 الأنماط الجمالية
// ===============================

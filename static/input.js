// ✅ static/input.js — النسخة النهائية بعد إصلاح الخطوات ورسالة الخطأ

document.addEventListener("DOMContentLoaded", function () {
  // ==============================
  // 🟦 تعريف المتغيرات الأساسية
  // ==============================
  let currentStep = 0;
  const steps = document.querySelectorAll(".form-step");
  const nextBtn = document.getElementById("nextBtn");
  const prevBtn = document.getElementById("prevBtn");
  const reviewBox = document.getElementById("review-box");
  const form = document.getElementById("rfpForm");
  const generateBtn = document.getElementById("generateBtn");
  const loadingText = document.getElementById("loadingText");
  const errorMsg = document.getElementById("errorMsg");

  // 🟦 تسميات الحقول بالعربية (لصفحة المراجعة)
  const fieldNamesArabic = {
    Competition_Name: "اسم المنافسة",
    Booklet_Number: "رقم الكراسة",
    Announcement_Date: "تاريخ طرح الكراسة",
    Government_Agency: "الجهة الحكومية",
    Competition_Document_Fees: "تكاليف وثائق المنافسة (ريال)",
    Payment_Method: "آلية الدفع",
    Name_of_Government_Agency_Representative: "اسم ممثل الجهة الحكومية",
    Position_of_Government_Agency_Representative: "الوظيفة",
    Phone_Number_of_Government_Agency_Representative: "رقم الهاتف",
    Fax_Number_of_Government_Agency_Representative: "الفاكس",
    Email_of_Government_Agency_Representative: "البريد الإلكتروني",
    Bid_Submission_Address: "العنوان",
    Bid_Submission_Building: "المبنى",
    Bid_Submission_Floor: "الطابق",
    Bid_Submission_Department_Name: "الغرفة / الإدارة",
    Bid_Submission_Time: "وقت التسليم",
    Inquiry_Response_Period: "فترة الرد على الاستفسارات",
    Initial_Guarantee_Percentage: "نسبة الضمان الابتدائي",
    Service_Execution_Location: "مكان تنفيذ الأعمال"
  };

  // ==============================
  // ✅ عرض الخطوة الحالية
  // ==============================
  function showStep(step) {
    steps.forEach((s, i) => s.classList.toggle("active", i === step));
    prevBtn.style.display = step === 0 ? "none" : "inline-block";
    nextBtn.style.display = step === steps.length - 1 ? "none" : "inline-block";
  }

  // ==============================
  // ✅ تحديث المراجعة النهائية
  // ==============================
  function updateReview() {
    let html = "";
    const allFields = document.querySelectorAll("#rfpForm input, #rfpForm textarea, #rfpForm select");

    allFields.forEach((el) => {
      const key = el.name?.trim();
      if (!key) return;

      let value = "";
      if (el.type === "checkbox") {
        const checked = document.querySelectorAll(`input[name="${key}"]:checked`);
        value = Array.from(checked).map(c => c.value).join(", ");
      } else {
        value = el.value?.trim() || "";
      }

      if (value !== "") {
        const label = fieldNamesArabic[key] || key;
        html += `
          <div class="review-item" style="margin-bottom:8px; background:#f9f9f9; padding:8px; border-radius:6px;">
            <strong>${label}:</strong> ${value}
          </div>
        `;
      }
    });

    reviewBox.innerHTML = html || "<p style='color:gray;text-align:center;'>لا توجد بيانات بعد</p>";
  }

  // ==============================
  // ✅ أزرار التنقل بين الخطوات
  // ==============================
  nextBtn.addEventListener("click", () => {
    if (currentStep < steps.length - 1) {
      currentStep++;
      showStep(currentStep);
      if (currentStep === steps.length - 1) setTimeout(updateReview, 200);
    }
  });

  prevBtn.addEventListener("click", () => {
    if (currentStep > 0) {
      currentStep--;
      showStep(currentStep);
    }
  });

  // ==============================
  // ✅ عند إرسال النموذج (زر توليد RFP)
  // ==============================
  form.addEventListener("submit", (e) => {
    const agency = document.querySelector("[name='Government_Agency']");
    const competition = document.querySelector("[name='Competition_Name']");

    // 🔸 التحقق من الحقول المطلوبة فقط
    // if (!agency.value.trim() || !competition.value.trim()) {
    //   e.preventDefault();
    //   errorMsg.style.display = "block";
    //   errorMsg.classList.remove("fade-out"); 
    //   setTimeout(() => {
    //     errorMsg.classList.add("fade-out");
    //     setTimeout(() => (errorMsg.style.display = "none"), 600);
    //   }, 5000);
    //   return;
    // }



    // 🔹 تعطيل الزر وإظهار التحميل
    generateBtn.disabled = true;
    generateBtn.style.opacity = "0.6";
    loadingText.style.display = "block";

    // 🔹 تحريك النقاط أثناء التوليد
    const dots = document.createElement("span");
    dots.id = "dots";
    loadingText.appendChild(dots);

    let dotCount = 0;
    const dotInterval = setInterval(() => {
      dotCount = (dotCount + 1) % 4;
      dots.textContent = ".".repeat(dotCount);
    }, 500);

    setTimeout(() => clearInterval(dotInterval), 20000);
  });

  // ✅ عرض أول خطوة عند تحميل الصفحة
  showStep(currentStep);
});



  // ==============================
  // ✅ دوال توليد الجداول
  // ==============================
  async function generateTable(apiEndpoint, inputId, outputId, saveBtnId, loadingId) {
    const text = document.getElementById(inputId).value.trim();
    if (!text) {
      alert("⚠️ الرجاء إدخال نص أولاً");
      return;
    }
    document.getElementById(loadingId).style.display = "block";
    try {
      const res = await fetch(apiEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      document.getElementById(loadingId).style.display = "none";
      if (data.error) {
        alert("❌ خطأ أثناء التوليد: " + data.error);
        return;
      }
      document.getElementById(outputId).innerHTML = data.html;
      document.getElementById(saveBtnId).style.display = "inline-block";
    } catch (err) {
      console.error("خطأ أثناء الاتصال:", err);
      document.getElementById(loadingId).style.display = "none";
    }
  }

  // ✅ حفظ أي جدول من الصفحة
  async function saveTable(outputId, tableName) {
    const table = document.querySelector(`#${outputId} table`);
    if (!table) {
      alert("⚠️ لا يوجد جدول لحفظه!");
      return;
    }
    const headers = Array.from(table.querySelectorAll("th")).map((th) => th.innerText);
    const rows = [];
    table.querySelectorAll("tbody tr").forEach((tr) => {
      const cells = Array.from(tr.querySelectorAll("td input")).map((td) => td.value);
      rows.push(cells);
    });
    const res = await fetch("/save_table", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ headers, rows, table_name: tableName }),
    });
    const data = await res.json();
    alert(data.message);
  }

  // ==============================
  // 🧱 جدول الكميات والأسعار
  // ==============================
  document.getElementById("quantitiesGenerateBtn").addEventListener("click", () => {
    generateTable(
      "/generate_table/quantities",
      "quantitiesInput",
      "quantitiesTableContainer",
      "quantitiesSaveBtn",
      "quantitiesLoading"
    );
  });

  document.getElementById("quantitiesSaveBtn").addEventListener("click", () => {
    saveTable("quantitiesTableContainer", "Bill_of_Quantities_and_Prices");
  });

  // ==============================
  // ⚙️ جدول المواد
  // ==============================
  document.getElementById("materialsGenerateBtn").addEventListener("click", () => {
    generateTable(
      "/generate_table/materials",
      "materialsInput",
      "materialsTableContainer",
      "materialsSaveBtn",
      "materialsLoading"
    );
  });

  document.getElementById("materialsSaveBtn").addEventListener("click", () => {
    saveTable("materialsTableContainer", "Materials_Specifications_Table");
  });

  // ==============================
  // 🔧 جدول المعدات
  // ==============================
  document.getElementById("equipmentGenerateBtn").addEventListener("click", () => {
    generateTable(
      "/generate_table/equipment",
      "equipmentInput",
      "equipmentTableContainer",
      "equipmentSaveBtn",
      "equipmentLoading"
    );
  });

  document.getElementById("equipmentSaveBtn").addEventListener("click", () => {
    saveTable("equipmentTableContainer", "Equipment_Specifications_Table");
  });


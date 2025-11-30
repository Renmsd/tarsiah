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
    Issue_Date: "تاريخ طرح الكراسة",
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
    Post_Qualification:"ملحق معايير التأهيل",
    Inquiry_Submission_period:"فتره ارسال الاسئله والاستفسارات",
    Inquiry_Response_Period: "فترة الاجابة على الاسئلة و الاستفسارات",
    Inquiry_Email:"البريد الالكتروني للرد على الاسئله والاستفسارات",
    Initial_Guarantee_Percentage: "نسبة الضمان الابتدائي",
    include_Joint_Venture:"التضامن",
    include_Tender_Split_Section:"تجزئه المنافسة",
    include_Alternative_Offers:"العروض البديلة",
    include_Insurance:"التأمينات",
    Project_Type:"طبيعة المشروع",
    Project_Duration:"مده المشروع",
    Award_Method:"اسلوب الترسيه",
    Includes_Equipment:"هل يشمل المشروع توريد اجهزه او معدات؟",
    Local_Content_Requirements:"متطلبات المحتوى المحلي ",
    Penalty_Deduction:"الخصم من مستحقات المالية",
    Penalty_Execute_On_Vendor:"تنفيذ الأعمال على حساب المتعاقد",
    Penalty_Suspend:"ابقاف الاعمال مؤقتا وإشعار المتعاقد",
    Penalty_Termination:"سحب المشروع وفسخ العقد",
    Max_Penalty_Percentage:"اجمالي الغرامة من القيمة الاجمالية للعقد(%)",
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
    if (!agency.value.trim() || !competition.value.trim()) {
      e.preventDefault();
      errorMsg.style.display = "block";
      errorMsg.classList.remove("fade-out"); 
      setTimeout(() => {
        errorMsg.classList.add("fade-out");
        setTimeout(() => (errorMsg.style.display = "none"), 600);
      }, 5000);
      return;
    }



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
      // ✅ أضف كلاس التصميم الجديد إلى الجدول المولد
      const table = document.querySelector(`#${outputId} table`);
      if (table) table.classList.add("dates-table");

      makeTableEditable(outputId); 
      
      document.getElementById(saveBtnId).style.display = "inline-block";
    } catch (err) {
      console.error("خطأ أثناء الاتصال:", err);
      document.getElementById(loadingId).style.display = "none";
    }
  }
// ✅ تعديل اسم العمود مباشرة داخل الجدول
  function makeTableEditable(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const table = container.querySelector("table");
  if (!table) return;

  const headers = table.querySelectorAll("th");
  if (!headers.length) return; // ✅ حماية إضافية

  headers.forEach(th => {
    th.style.cursor = "text";
    th.title = "انقر مرتين لتعديل اسم العمود ✏️";

    th.addEventListener("dblclick", () => {
      const oldText = th.textContent.trim();
      const input = document.createElement("input");
      input.type = "text";
      input.value = oldText;
      input.className = "edit-header-input";

      th.textContent = "";
      th.appendChild(input);
      input.focus();

      input.addEventListener("blur", () => {
        const newText = input.value.trim() || oldText;
        th.textContent = newText;
      });

      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === "Escape") {
          input.blur();
        }
      });
    });
  });
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

    // ==============================
   // 👷 جدول العمال (Workers Table)
   // ==============================
  document.getElementById("workersGenerateBtn").addEventListener("click", () => {
    generateTable(
      "/generate_table/workers",
      "workersInput",
      "workersTableContainer",
      "workersSaveBtn",
      "workersLoading"
    );
  });

  document.getElementById("workersSaveBtn").addEventListener("click", () => {
    saveTable("workersTableContainer", "Workers_Table");
  });



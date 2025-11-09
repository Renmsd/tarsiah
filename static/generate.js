// ✅ التحكم في عرض خطوات النموذج (multi-step form)
let currentStep = 0;
const steps = document.querySelectorAll(".form-step");
const nextBtns = document.querySelectorAll(".nextBtn");
const prevBtns = document.querySelectorAll(".prevBtn");

// 🔹 دالة إظهار الخطوة الحالية فقط
function showStep(index) {
  steps.forEach((step, i) => {
    step.classList.toggle("active", i === index);
  });

  // ✨ تأثير ناعم عند الانتقال
  steps[index].style.animation = "fadeIn 0.4s ease";
}

// 🔹 الانتقال إلى الخطوة التالية
nextBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    if (currentStep < steps.length - 1) {
      currentStep++;
      showStep(currentStep);
    }
  });
});

// 🔹 الرجوع إلى الخطوة السابقة
prevBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    if (currentStep > 0) {
      currentStep--;
      showStep(currentStep);
    }
  });
});

// 🔹 إظهار أول خطوة عند تحميل الصفحة
showStep(currentStep);

// ============================
// 💾 تأثير عند الضغط على زر الحفظ
// ============================
const saveBtn = document.getElementById("saveBtn");
const waitMsg = document.getElementById("waitMsg");

if (saveBtn) {
  saveBtn.addEventListener("submit", () => {
  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.style.opacity = "0.6";
    generateBtn.textContent = "جاري التوليد...";
  }
  if (loadingText) {
    loadingText.style.display = "block";
  }

  // 🔹 تحريك النقاط أثناء التوليد
  const dots = document.createElement("span");
  dots.id = "dots";
  loadingText.appendChild(dots);

  let dotCount = 0;
  const dotInterval = setInterval(() => {
    dotCount = (dotCount + 1) % 4;
    dots.textContent = ".".repeat(dotCount);
  }, 500);

  setTimeout(() => {
    clearInterval(dotInterval);
  }, 20000);
  });
}

// ============================
// 🎨 أنيميشن ناعم للتنقل بين الأقسام
// ============================
const style = document.createElement("style");
style.textContent = `
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
`;
document.head.appendChild(style);

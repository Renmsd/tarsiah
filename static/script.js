// ==========================
// 👤 التحكم بقائمة المستخدم
// ==========================
function toggleUserMenu() {
  const menu = document.getElementById("userDropdown");
  menu.style.display = menu.style.display === "block" ? "none" : "block";
}

// إغلاق القائمة عند النقر خارجها
document.addEventListener("click", (e) => {
  const menu = document.getElementById("userDropdown");
  if (!e.target.closest(".user-menu")) {
    menu.style.display = "none";
  }
});

// ==========================
// 🌍 كائن الترجمة (عربي / إنجليزي)
// ==========================
const translations = {
  ar: {
    home: " ",
    generate: " ",
    compare: " ",
    logout: "تسجيل الخروج",
    title: "Smart RFP AI",
    subtitle: "حلول ذكية لإدارة RFP والعروض بدقة وكفاءة",
    desc: "منصة متكاملة تساعدك على إنشاء، تحليل، ومقارنة RFP باستخدام تقنيات الذكاء الاصطناعي الحديثة.",
    features: ["سهولة الاستخدام", "ذكاء اصطناعي موثوق", "نتائج دقيقة"],
    card1Title: "إنشاء RFP",
    card1Text: "ابدأ بإنشاء RFP  بناءً على بيانات المشروع",
    card2Title: "مقارنة العروض",
    card2Text: "قارن بين RFP والعروض المقدمة باستخدام الذكاء الاصطناعي",
    tableTitle: "آخر المشاريع التي تم توليدها",
    colProject: "اسم المشروع",
    colDate: "تاريخ الإنشاء",
    projects: [
      ["إنشاء مبنى إداري جديد", "2025-10-28"],
      ["مشروع صيانة الطرق", "2025-10-22"],
      ["تطوير النظام الإلكتروني", "2025-10-18"],
    ],
  },
  en: {
    home: " ",
    generate: " ",
    compare: " ",
    logout: "Logout",
    title: "Smart RFP AI",
    subtitle: "Intelligent Solutions for RFP and Proposal Management",
    desc: "A complete platform to create, analyze, and compare RFPs using modern AI technologies.",
    features: ["Easy to use", "Reliable AI", "Accurate results"],
    card1Title: "Generate RFP",
    card1Text: "Start creating a smart RFP based on your project details.",
    card2Title: "Compare Offers",
    card2Text: "Compare RFPs and proposals using artificial intelligence.",
    tableTitle: "Recently Generated Projects",
    colProject: "Project Name",
    colDate: "Creation Date",
    projects: [
      ["Administrative Building Construction", "2025-10-28"],
      ["Road Maintenance Project", "2025-10-22"],
      ["Electronic System Development", "2025-10-18"],
    ],
  },
};

// ==========================
// 🔄 تطبيق الترجمة على الصفحة
// ==========================
function applyTranslation(lang) {
  const t = translations[lang];

  // ✅ تحديث شريط التنقل
  document.getElementById("nav-home").textContent = t.home;
  document.getElementById("nav-generate").textContent = t.generate;
  document.getElementById("nav-compare").textContent = t.compare;

  // ✅ تحديث قائمة المستخدم
  document.getElementById("logout-text").textContent = t.logout;

  // ✅ تحديث النصوص والعناوين
  document.getElementById("main-title").textContent = t.title;
  document.getElementById("main-subtitle").textContent = t.subtitle;
  document.getElementById("main-desc").textContent = t.desc;

  // ✅ تحديث مميزات النظام
  document.getElementById("feat1").textContent = t.features[0];
  document.getElementById("feat2").textContent = t.features[1];
  document.getElementById("feat3").textContent = t.features[2];

  // ✅ تحديث الكروت
  document.getElementById("card1-title").textContent = t.card1Title;
  document.getElementById("card1-text").textContent = t.card1Text;
  document.getElementById("card2-title").textContent = t.card2Title;
  document.getElementById("card2-text").textContent = t.card2Text;

  // ✅ ضبط اتجاه الصفحة
  document.body.dir = lang === "ar" ? "rtl" : "ltr";
  document.body.setAttribute("lang", lang);
  loadProjects(lang);

}

// ==========================
// 🌐 تبديل اللغة وحفظها
// ==========================
function toggleLang() {
  const currentLang = localStorage.getItem("lang") || "ar";
  const newLang = currentLang === "ar" ? "en" : "ar";
  localStorage.setItem("lang", newLang);
  applyTranslation(newLang);
}

// ==========================
// 🚀 عند تحميل الصفحة
// ==========================
window.addEventListener("DOMContentLoaded", () => {
  const savedLang = localStorage.getItem("lang") || "ar";
  applyTranslation(savedLang);
});

// ==========================
// 📊 تحميل بيانات المشاريع من ملف JSON
// ==========================
async function loadProjects(lang) {
  try {

    const response = await fetch("static/projects.json?ts=" + new Date().getTime());
    const data = await response.json();
    const projects = data[lang].slice(-5);


    const tableBody = document.getElementById("table-body");
    tableBody.innerHTML = "";

    projects.forEach((proj) => {
      const row = document.createElement("tr");
      row.innerHTML = `<td>${proj.name}</td><td>${proj.date}</td>`;
      tableBody.appendChild(row);
    });
  } catch (error) {
    console.error("❌ خطأ في تحميل المشاريع:", error);
  }
}




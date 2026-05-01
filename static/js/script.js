/**
 * script.js — ResumeAI
 * Handles: profile dropdown, password toggle, drag-drop upload,
 *          loading animation, password strength, orb parallax
 */

document.addEventListener("DOMContentLoaded", () => {

  // ─── PROFILE DROPDOWN ─────────────────────────────
  const profileBtn      = document.getElementById("profileBtn");
  const profileDropdown = document.getElementById("profileDropdown");
  const pdBackdrop      = document.getElementById("pdBackdrop");

  if (profileBtn && profileDropdown) {
    profileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = profileDropdown.classList.contains("open");
      profileDropdown.classList.toggle("open", !isOpen);
      pdBackdrop && pdBackdrop.classList.toggle("active", !isOpen);
      profileBtn.classList.toggle("open", !isOpen);
    });

    // Close on backdrop click
    if (pdBackdrop) {
      pdBackdrop.addEventListener("click", closeDropdown);
    }

    // Close on ESC
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeDropdown();
    });
  }

  function closeDropdown() {
    profileDropdown && profileDropdown.classList.remove("open");
    pdBackdrop && pdBackdrop.classList.remove("active");
    profileBtn && profileBtn.classList.remove("open");
  }

  // ─── PASSWORD TOGGLE ──────────────────────────────
  const pwdToggle = document.getElementById("pwdToggle");
  const pwdInput  = document.getElementById("pwdInput") || document.getElementById("pwd1");

  if (pwdToggle && pwdInput) {
    pwdToggle.addEventListener("click", () => {
      const isText = pwdInput.type === "text";
      pwdInput.type = isText ? "password" : "text";
      pwdToggle.textContent = isText ? "👁" : "🙈";
    });
  }

  // ─── PASSWORD STRENGTH (register page) ────────────
  const pwd1      = document.getElementById("pwd1");
  const strength  = document.getElementById("pwdStrength");
  const psFill    = document.getElementById("psFill");
  const psLabel   = document.getElementById("psLabel");

  if (pwd1 && strength) {
    pwd1.addEventListener("input", () => {
      const val = pwd1.value;
      if (!val) { strength.style.display = "none"; return; }
      strength.style.display = "flex";

      let score = 0;
      if (val.length >= 8)           score++;
      if (/[A-Z]/.test(val))         score++;
      if (/[0-9]/.test(val))         score++;
      if (/[^A-Za-z0-9]/.test(val))  score++;

      const levels = [
        { w: "25%",  color: "#f87171", label: "Weak" },
        { w: "50%",  color: "#fbbf24", label: "Fair" },
        { w: "75%",  color: "#60a5fa", label: "Good" },
        { w: "100%", color: "#4ade80", label: "Strong" },
      ];
      const lvl = levels[score - 1] || levels[0];
      psFill.style.width      = lvl.w;
      psFill.style.background = lvl.color;
      psLabel.textContent     = lvl.label;
      psLabel.style.color     = lvl.color;
    });
  }

  // ─── REGISTER FORM — password match validation ────
  const registerForm = document.getElementById("registerForm");
  const pwd2 = document.getElementById("pwd2");

  if (registerForm && pwd1 && pwd2) {
    registerForm.addEventListener("submit", (e) => {
      if (pwd1.value !== pwd2.value) {
        e.preventDefault();
        showToast("⚠ Passwords do not match.", "error");
        pwd2.focus();
      }
    });
  }

  // ─── UPLOAD PAGE ──────────────────────────────────
  const dropZone       = document.getElementById("dropZone");
  const fileInput      = document.getElementById("fileInput");
  const filePreview    = document.getElementById("filePreview");
  const fileName       = document.getElementById("fileName");
  const fileSize       = document.getElementById("fileSize");
  const removeFile     = document.getElementById("removeFile");
  const submitBtn      = document.getElementById("submitBtn");
  const uploadForm     = document.getElementById("uploadForm");
  const loadingOverlay = document.getElementById("loadingOverlay");

  if (dropZone) {
    dropZone.addEventListener("click",    () => fileInput && fileInput.click());
    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
    dropZone.addEventListener("dragleave",() => dropZone.classList.remove("drag-over"));
    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    });
  }

  if (fileInput) {
    fileInput.addEventListener("change", () => {
      if (fileInput.files[0]) handleFile(fileInput.files[0]);
    });
  }

  if (removeFile) {
    removeFile.addEventListener("click", () => {
      if (fileInput)  fileInput.value = "";
      if (filePreview) filePreview.style.display = "none";
      if (dropZone)   dropZone.style.display = "block";
      if (submitBtn)  submitBtn.disabled = true;
    });
  }

  function handleFile(file) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx"].includes(ext)) {
      showToast("⚠ Only PDF or DOCX files are supported.", "error");
      return;
    }
    if (fileName)  fileName.textContent  = file.name;
    if (fileSize)  fileSize.textContent  = formatSize(file.size);
    if (filePreview) filePreview.style.display = "flex";
    if (dropZone)    dropZone.style.display    = "none";
    if (submitBtn)   submitBtn.disabled        = false;

    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      if (fileInput) fileInput.files = dt.files;
    } catch(e) {}
  }

  function formatSize(bytes) {
    if (bytes < 1024)        return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  // Loading animation
  if (uploadForm && loadingOverlay) {
    uploadForm.addEventListener("submit", () => {
      if (fileInput && fileInput.files && fileInput.files.length > 0) {
        loadingOverlay.style.display = "flex";
        runLoadingSteps();
      }
    });
  }

  function runLoadingSteps() {
    const steps  = ["ls1","ls2","ls3","ls4"].map(id => document.getElementById(id));
    const labels = ["Parsing resume text","Extracting skills with NLP","Matching career paths","Building your report"];
    if (!steps[0]) return;
    steps.forEach(s => s && s.classList.remove("active","done"));
    steps[0].classList.add("active");

    [1300, 2600, 3900].forEach((delay, i) => {
      setTimeout(() => {
        const prev = steps[i], curr = steps[i + 1];
        if (prev) {
          prev.classList.remove("active");
          prev.classList.add("done");
          const span = prev.querySelector("span");
          if (span) span.textContent = "✓ " + labels[i];
        }
        if (curr) curr.classList.add("active");
      }, delay);
    });
  }

  // ─── RESULT PAGE — stagger skill tags ─────────────
  document.querySelectorAll(".s-tag").forEach((tag, i) => {
    tag.style.animationDelay = `${i * 30}ms`;
  });

  // Animate bars on scroll into view
  if ("IntersectionObserver" in window) {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) e.target.style.animationPlayState = "running";
      });
    }, { threshold: 0.1 });

    document.querySelectorAll(".dp-bar-fill,.sc-bar-fill,.ct-bar-fill,.ap-bar-fill")
      .forEach(b => { b.style.animationPlayState = "paused"; obs.observe(b); });
  }

  // ─── PROFILE PAGE — auto-save toast clear ─────────
  const toastBanner = document.querySelector(".toast-banner.success");
  if (toastBanner) {
    setTimeout(() => {
      toastBanner.style.transition = "opacity .5s";
      toastBanner.style.opacity = "0";
      setTimeout(() => toastBanner.remove(), 500);
    }, 3000);
  }

  // ─── TOAST UTILITY ────────────────────────────────
  function showToast(message, type = "info") {
    const existing = document.querySelector(".js-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "js-toast";
    toast.style.cssText = `
      position:fixed;bottom:28px;left:50%;transform:translateX(-50%);
      background:rgba(13,13,26,.97);
      border:1px solid ${type==="error"?"rgba(248,113,113,.3)":"rgba(110,231,247,.3)"};
      color:${type==="error"?"#fca5a5":"#6EE7F7"};
      backdrop-filter:blur(20px);padding:12px 22px;
      border-radius:100px;font-family:'Outfit',sans-serif;
      font-size:.87rem;font-weight:600;z-index:9999;
      animation:toastIn .3s ease;white-space:nowrap;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.animation = "toastOut .3s ease forwards";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // Inject toast keyframes once
  if (!document.getElementById("toastKF")) {
    const s = document.createElement("style");
    s.id = "toastKF";
    s.textContent = `
      @keyframes toastIn  { from{opacity:0;transform:translateX(-50%) translateY(10px)} to{opacity:1;transform:translateX(-50%) translateY(0)} }
      @keyframes toastOut { from{opacity:1} to{opacity:0;transform:translateX(-50%) translateY(8px)} }
    `;
    document.head.appendChild(s);
  }

  // ─── HOME — orb parallax ──────────────────────────
  const orbs = document.querySelectorAll(".ambient-orb");
  if (orbs.length) {
    let ticking = false;
    window.addEventListener("mousemove", e => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const x = (e.clientX / window.innerWidth  - 0.5) * 22;
        const y = (e.clientY / window.innerHeight - 0.5) * 22;
        orbs.forEach((o, i) => {
          const f = (i + 1) * 0.5;
          o.style.transform = `translate(${x * f}px, ${y * f}px)`;
        });
        ticking = false;
      });
    });
  }

});

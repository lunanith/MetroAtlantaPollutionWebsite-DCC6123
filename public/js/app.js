console.log("MAP-USA loaded");

document.addEventListener("DOMContentLoaded", function () {
  const chatbotToggle = document.getElementById("chatbotToggle");
  const chatbotPanel = document.getElementById("chatbotPanel");
  const chatbotClose = document.getElementById("chatbotClose");

  if (chatbotToggle && chatbotPanel) {
    chatbotToggle.addEventListener("click", function () {
      chatbotPanel.classList.toggle("open");
    });
  }

  if (chatbotClose && chatbotPanel) {
    chatbotClose.addEventListener("click", function () {
      chatbotPanel.classList.remove("open");
    });
  }

  // ===== Report a Bug modal =====
  const openBtn   = document.getElementById("openBugReport");
  const closeBtn  = document.getElementById("closeBugReport");
  const overlay   = document.getElementById("bugReportOverlay");
  const form      = document.getElementById("bugReportForm");
  const statusEl  = document.getElementById("bugStatusText");
  const submitBtn = document.getElementById("bugSubmitBtn");

  function clearFieldErrors() {
    document.querySelectorAll(".field-error").forEach(function (el) {
      el.textContent = "";
    });
  }

  function setStatus(msg, kind) {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
    statusEl.className = "status-text" + (kind ? " " + kind : "");
  }

  function openBugModal() {
    if (!overlay) return;
    overlay.classList.add("open");
    overlay.setAttribute("aria-hidden", "false");
  }

  function closeBugModal() {
    if (!overlay) return;
    overlay.classList.remove("open");
    overlay.setAttribute("aria-hidden", "true");
  }

  if (openBtn)  openBtn.addEventListener("click", openBugModal);
  if (closeBtn) closeBtn.addEventListener("click", closeBugModal);
  if (overlay) {
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeBugModal();
    });
  }

  if (form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      clearFieldErrors();
      setStatus("Submitting…");
      submitBtn.disabled = true;

      const formData = new FormData(form);

      try {
        const res = await fetch("/api/report-bug", {
          method: "POST",
          body: formData,
        });
        const data = await res.json();

        if (!res.ok || !data.success) {
          if (data.errors) {
            Object.keys(data.errors).forEach(function (field) {
              const el = document.querySelector('[data-error-for="' + field + '"]');
              if (el) el.textContent = data.errors[field];
            });
            setStatus("Please fix the errors above.", "error");
          } else {
            setStatus(data.error || "Something went wrong. Please try again.", "error");
          }
          return;
        }

        setStatus("Thanks! Your report was submitted.", "success");
        form.reset();
        setTimeout(function () {
          closeBugModal();
          setStatus("");
        }, 1500);
      } catch (err) {
        setStatus("Network error. Please try again.", "error");
      } finally {
        submitBtn.disabled = false;
      }
    });
  }
});
console.log("MAP-USA loaded");

document.addEventListener("DOMContentLoaded", function () {
  const chatbotToggle = document.getElementById("chatbotToggle");
  const chatbotPanel = document.getElementById("chatbotPanel");
  const chatbotClose = document.getElementById("chatbotClose");
  const chatbotBody = chatbotPanel ? chatbotPanel.querySelector(".chatbot-body") : null;
  const chatForm = chatbotPanel ? chatbotPanel.querySelector(".chatbot-form") : null;
  const chatInput = chatbotPanel ? chatbotPanel.querySelector(".chatbot-input") : null;
  const chatSendBtn = chatbotPanel ? chatbotPanel.querySelector(".chatbot-send") : null;

  function scrollChatToBottom() {
    if (chatbotBody) chatbotBody.scrollTop = chatbotBody.scrollHeight;
  }

  function appendChatMessage(role, text, extraClass) {
    if (!chatbotBody) return null;
    const msg = document.createElement("div");
    msg.className = "chat-msg " + role + (extraClass ? " " + extraClass : "");
    msg.textContent = text;
    chatbotBody.appendChild(msg);
    scrollChatToBottom();
    return msg;
  }

  function setChatLoading(isLoading) {
    if (chatInput) chatInput.disabled = isLoading;
    if (chatSendBtn) chatSendBtn.disabled = isLoading;
    if (chatSendBtn) chatSendBtn.textContent = isLoading ? "..." : "Send";
  }

  if (chatbotToggle && chatbotPanel) {
    chatbotToggle.addEventListener("click", function () {
      chatbotPanel.classList.toggle("open");
      if (chatbotPanel.classList.contains("open")) {
        scrollChatToBottom();
        if (chatInput) chatInput.focus();
      }
    });
  }

  if (chatbotClose && chatbotPanel) {
    chatbotClose.addEventListener("click", function () {
      chatbotPanel.classList.remove("open");
    });
  }

  if (chatForm && chatInput) {
    chatForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const message = chatInput.value.trim();
      if (!message) return;

      if (chatbotPanel && !chatbotPanel.classList.contains("open")) {
        chatbotPanel.classList.add("open");
      }

      appendChatMessage("user", message);
      chatInput.value = "";
      setChatLoading(true);

      const pendingMessage = appendChatMessage("bot", "Thinking...", "pending");

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({
            message: message,
            pageTitle: document.title,
            pagePath: window.location.pathname,
          }),
        });
        const data = await res.json();

        if (!res.ok || !data.success) {
          throw new Error(data.error || "Something went wrong.");
        }

        if (pendingMessage) pendingMessage.remove();
        appendChatMessage("bot", data.reply);
      } catch (err) {
        if (pendingMessage) pendingMessage.remove();
        appendChatMessage("bot", err.message || "The assistant is unavailable right now.");
      } finally {
        setChatLoading(false);
        chatInput.focus();
      }
    });
  }

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

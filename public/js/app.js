console.log("MAP-USA loaded");

document.addEventListener("DOMContentLoaded", function () {
  const chatbotToggle = document.getElementById("chatbotToggle");
  const chatbotPanel = document.getElementById("chatbotPanel");
  const chatbotClose = document.getElementById("chatbotClose");
  const chatbotHeader = chatbotPanel ? chatbotPanel.querySelector(".chatbot-header") : null;
  const chatbotBody = chatbotPanel ? chatbotPanel.querySelector(".chatbot-body") : null;
  const chatForm = chatbotPanel ? chatbotPanel.querySelector(".chatbot-form") : null;
  const chatInput = chatbotPanel ? chatbotPanel.querySelector(".chatbot-input") : null;
  const chatSendBtn = chatbotPanel ? chatbotPanel.querySelector(".chatbot-send") : null;
  const chatInputWrap = chatbotPanel ? chatbotPanel.querySelector(".chatbot-input-wrap") : null;
  const CHAT_MESSAGES_STORAGE_KEY = "mapusaChatMessages";
  const CHAT_STATE_STORAGE_KEY = "mapusaChatState";
  const MAX_STORED_CHAT_MESSAGES = 40;
  const MAX_CHAT_FILES = 3;
  const MAX_CHAT_FILE_BYTES = 8 * 1024 * 1024;
  const CHAT_ACCEPTED_FILES = "image/png,image/jpeg,image/webp,image/gif,application/pdf,text/plain,text/markdown,text/csv,application/json,.txt,.md,.csv,.json,.html,.css,.js,.py,.xml,.log";
  let chatbotExpand = null;
  let chatFileInput = null;
  let chatAttachButton = null;
  let chatAttachmentList = null;
  let selectedChatFiles = [];
  let chatMessages = [];

  function wasPageReloaded() {
    const navEntries = performance.getEntriesByType ? performance.getEntriesByType("navigation") : [];
    if (navEntries.length) return navEntries[0].type === "reload";
    return performance.navigation && performance.navigation.type === 1;
  }

  function clearStoredChat() {
    try {
      window.sessionStorage.removeItem(CHAT_MESSAGES_STORAGE_KEY);
      window.sessionStorage.removeItem(CHAT_STATE_STORAGE_KEY);
    } catch (err) {
      // Ignore storage errors so chat still works in private or restricted browsing modes.
    }
  }

  function resetServerChatHistory() {
    try {
      const body = new Blob(["{}"], { type: "application/json" });
      if (navigator.sendBeacon) {
        navigator.sendBeacon("/api/chat/reset", body);
        return;
      }
      fetch("/api/chat/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: "{}",
        keepalive: true,
      });
    } catch (err) {
      // A failed reset should not block page rendering.
    }
  }

  if (wasPageReloaded()) {
    clearStoredChat();
    resetServerChatHistory();
  }

  function scrollChatToBottom() {
    if (chatbotBody) chatbotBody.scrollTop = chatbotBody.scrollHeight;
  }

  function readStoredJson(key, fallback) {
    try {
      const stored = window.sessionStorage.getItem(key);
      return stored ? JSON.parse(stored) : fallback;
    } catch (err) {
      return fallback;
    }
  }

  function writeStoredJson(key, value) {
    try {
      window.sessionStorage.setItem(key, JSON.stringify(value));
    } catch (err) {
      // Ignore storage errors so chat still works in private or restricted browsing modes.
    }
  }

  function saveChatState() {
    if (!chatbotPanel) return;
    writeStoredJson(CHAT_STATE_STORAGE_KEY, {
      open: chatbotPanel.classList.contains("open"),
      expanded: chatbotPanel.classList.contains("expanded"),
    });
  }

  function saveChatMessages() {
    chatMessages = chatMessages.slice(-MAX_STORED_CHAT_MESSAGES);
    writeStoredJson(CHAT_MESSAGES_STORAGE_KEY, chatMessages);
  }

  function rememberChatMessage(role, text) {
    const cleanText = String(text || "").trim();
    if (!cleanText || (role !== "user" && role !== "bot")) return;
    chatMessages.push({ role: role, text: cleanText });
    saveChatMessages();
  }

  function cleanChatLine(line) {
    return line
      .replace(/^#{1,6}\s+/, "")
      .replace(/^\s*[-*•]\s+/, "")
      .replace(/\*\*(.*?)\*\*/g, "$1")
      .replace(/\*(.*?)\*/g, "$1")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\s+/g, " ")
      .trim();
  }

  function appendChatText(msg, text, role) {
    const rawText = String(text || "").replace(/\r\n/g, "\n").trim();

    if (!rawText) {
      msg.textContent = rawText;
      return;
    }

    if (role !== "bot") {
      rawText.split("\n").forEach(function (line) {
        const paragraph = document.createElement("p");
        paragraph.textContent = line.trim();
        if (paragraph.textContent) msg.appendChild(paragraph);
      });
      return;
    }

    const lines = rawText
      .split("\n")
      .map(function (line) {
        return line.trim();
      })
      .filter(Boolean);

    let list = null;

    lines.forEach(function (line) {
      const numberedMatch = line.match(/^(\d+)[.)]\s+(.+)/);
      const isBullet = /^\s*[-*•]\s+/.test(line);
      const listText = numberedMatch ? numberedMatch[2] : cleanChatLine(line);

      if ((numberedMatch || isBullet) && listText) {
        if (!list || list.tagName.toLowerCase() !== (numberedMatch ? "ol" : "ul")) {
          list = document.createElement(numberedMatch ? "ol" : "ul");
          msg.appendChild(list);
        }
        const item = document.createElement("li");
        item.textContent = listText;
        list.appendChild(item);
        return;
      }

      list = null;
      const paragraph = document.createElement("p");
      paragraph.textContent = cleanChatLine(line);
      if (paragraph.textContent) msg.appendChild(paragraph);
    });

    if (!msg.textContent.trim()) {
      msg.textContent = cleanChatLine(rawText);
    }
  }

  function appendChatMessage(role, text, extraClass, shouldRemember) {
    if (!chatbotBody) return null;
    const msg = document.createElement("div");
    msg.className = "chat-msg " + role + (extraClass ? " " + extraClass : "");
    appendChatText(msg, text, role);
    chatbotBody.appendChild(msg);
    if (shouldRemember !== false && extraClass !== "pending") {
      rememberChatMessage(role, text);
    }
    scrollChatToBottom();
    return msg;
  }

  function setChatLoading(isLoading) {
    if (chatInput) chatInput.disabled = isLoading;
    if (chatFileInput) chatFileInput.disabled = isLoading;
    if (chatAttachButton) chatAttachButton.disabled = isLoading;
    if (chatSendBtn) chatSendBtn.disabled = isLoading;
    if (chatSendBtn) chatSendBtn.textContent = isLoading ? "..." : "Send";
  }

  function formatFileSize(bytes) {
    if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function renderChatAttachments() {
    if (!chatAttachmentList) return;
    chatAttachmentList.innerHTML = "";

    selectedChatFiles.forEach(function (file, index) {
      const chip = document.createElement("div");
      chip.className = "chat-attachment-chip";

      const label = document.createElement("span");
      label.textContent = file.name + " (" + formatFileSize(file.size) + ")";

      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.setAttribute("aria-label", "Remove " + file.name);
      removeButton.textContent = "x";
      removeButton.addEventListener("click", function () {
        selectedChatFiles.splice(index, 1);
        renderChatAttachments();
        if (chatInput) chatInput.focus();
      });

      chip.appendChild(label);
      chip.appendChild(removeButton);
      chatAttachmentList.appendChild(chip);
    });
  }

  function addChatFiles(files) {
    const incomingFiles = Array.prototype.slice.call(files || []);
    const acceptedFiles = [];
    const rejectedNames = [];

    incomingFiles.forEach(function (file) {
      if (selectedChatFiles.length + acceptedFiles.length >= MAX_CHAT_FILES) {
        rejectedNames.push(file.name + " (limit is " + MAX_CHAT_FILES + " files)");
        return;
      }
      if (file.size > MAX_CHAT_FILE_BYTES) {
        rejectedNames.push(file.name + " (max 8 MB)");
        return;
      }
      acceptedFiles.push(file);
    });

    selectedChatFiles = selectedChatFiles.concat(acceptedFiles);
    renderChatAttachments();

    if (rejectedNames.length) {
      appendChatMessage("bot", "I could not attach: " + rejectedNames.join(", ") + ".", "", false);
    }
  }

  if (chatForm && chatInputWrap) {
    chatAttachmentList = document.createElement("div");
    chatAttachmentList.className = "chat-attachment-list";
    chatInputWrap.insertBefore(chatAttachmentList, chatForm);

    chatFileInput = document.createElement("input");
    chatFileInput.type = "file";
    chatFileInput.className = "chat-file-input";
    chatFileInput.accept = CHAT_ACCEPTED_FILES;
    chatFileInput.multiple = true;

    chatAttachButton = document.createElement("button");
    chatAttachButton.type = "button";
    chatAttachButton.className = "chat-attach-button";
    chatAttachButton.setAttribute("aria-label", "Attach image or file");
    chatAttachButton.setAttribute("title", "Attach image or file");
    chatAttachButton.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24" focusable="false"><path d="M21.4 10.6l-8.7 8.7a6 6 0 0 1-8.5-8.5l9.4-9.4a4.2 4.2 0 0 1 5.9 5.9l-9.4 9.4a2.4 2.4 0 0 1-3.4-3.4l8.7-8.7"/></svg>';

    chatForm.insertBefore(chatAttachButton, chatForm.firstChild);
    chatForm.appendChild(chatFileInput);

    chatAttachButton.addEventListener("click", function () {
      chatFileInput.click();
    });

    chatFileInput.addEventListener("change", function () {
      addChatFiles(chatFileInput.files);
      chatFileInput.value = "";
    });
  }

  function syncChatExpandButton() {
    if (!chatbotPanel || !chatbotExpand) return;
    const isExpanded = chatbotPanel.classList.contains("expanded");
    chatbotExpand.classList.toggle("is-expanded", isExpanded);
    chatbotExpand.setAttribute("aria-label", isExpanded ? "Shrink chat window" : "Expand chat window");
    chatbotExpand.setAttribute("title", isExpanded ? "Shrink chat window" : "Expand chat window");
    chatbotExpand.setAttribute("aria-pressed", isExpanded ? "true" : "false");
  }

  if (chatbotHeader && chatbotClose && chatbotPanel) {
    const chatActions = document.createElement("div");
    chatActions.className = "chatbot-actions";

    chatbotExpand = document.createElement("button");
    chatbotExpand.type = "button";
    chatbotExpand.className = "chatbot-expand";
    chatbotExpand.setAttribute("aria-label", "Expand chat window");
    chatbotExpand.setAttribute("aria-pressed", "false");
    chatbotExpand.setAttribute("title", "Expand chat window");
    chatbotExpand.innerHTML = '<span class="chatbot-expand-icon" aria-hidden="true"></span>';

    chatbotClose.parentNode.insertBefore(chatActions, chatbotClose);
    chatActions.appendChild(chatbotExpand);
    chatActions.appendChild(chatbotClose);

    chatbotExpand.addEventListener("click", function () {
      chatbotPanel.classList.toggle("expanded");
      syncChatExpandButton();
      saveChatState();
      scrollChatToBottom();
      if (chatInput) chatInput.focus();
    });
  }

  function restoreChatMessages() {
    if (!chatbotBody) return;

    const storedMessages = readStoredJson(CHAT_MESSAGES_STORAGE_KEY, []);
    if (!Array.isArray(storedMessages) || !storedMessages.length) return;

    chatMessages = storedMessages
      .filter(function (item) {
        return item && (item.role === "user" || item.role === "bot") && typeof item.text === "string" && item.text.trim();
      })
      .slice(-MAX_STORED_CHAT_MESSAGES);

    if (!chatMessages.length) return;

    chatbotBody.innerHTML = "";
    chatMessages.forEach(function (item) {
      appendChatMessage(item.role, item.text, "", false);
    });
  }

  function restoreChatState() {
    if (!chatbotPanel) return;

    const state = readStoredJson(CHAT_STATE_STORAGE_KEY, {});
    chatbotPanel.classList.toggle("open", Boolean(state.open));
    chatbotPanel.classList.toggle("expanded", Boolean(state.expanded));
    syncChatExpandButton();
    scrollChatToBottom();
  }

  restoreChatMessages();
  restoreChatState();

  if (chatbotToggle && chatbotPanel) {
    chatbotToggle.addEventListener("click", function () {
      chatbotPanel.classList.toggle("open");
      saveChatState();
      if (chatbotPanel.classList.contains("open")) {
        scrollChatToBottom();
        if (chatInput) chatInput.focus();
      }
    });
  }

  if (chatbotClose && chatbotPanel) {
    chatbotClose.addEventListener("click", function () {
      chatbotPanel.classList.remove("open");
      saveChatState();
    });
  }

  if (chatForm && chatInput) {
    chatForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const message = chatInput.value.trim();
      if (!message && !selectedChatFiles.length) return;

      if (chatbotPanel && !chatbotPanel.classList.contains("open")) {
        chatbotPanel.classList.add("open");
        saveChatState();
      }

      const attachmentSummary = selectedChatFiles.length
        ? "\n\nAttached: " + selectedChatFiles.map(function (file) { return file.name; }).join(", ")
        : "";
      appendChatMessage("user", (message || "Please analyze this attachment.") + attachmentSummary);
      chatInput.value = "";
      setChatLoading(true);

      const pendingMessage = appendChatMessage("bot", "Thinking...", "pending", false);

      try {
        const body = new FormData();
        body.append("message", message);
        body.append("pageTitle", document.title);
        body.append("pagePath", window.location.pathname);
        selectedChatFiles.forEach(function (file) {
          body.append("attachments", file, file.name);
        });

        const res = await fetch("/api/chat", {
          method: "POST",
          credentials: "same-origin",
          body: body,
        });
        const data = await res.json();

        if (!res.ok || !data.success) {
          throw new Error(data.error || "Something went wrong.");
        }

        if (pendingMessage) pendingMessage.remove();
        appendChatMessage("bot", data.reply);
        selectedChatFiles = [];
        renderChatAttachments();
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

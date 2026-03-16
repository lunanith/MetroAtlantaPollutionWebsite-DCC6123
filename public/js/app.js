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
});
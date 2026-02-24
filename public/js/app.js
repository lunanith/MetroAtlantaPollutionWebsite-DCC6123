console.log("ATL Pollution site loaded");

document.addEventListener("submit", function (e) {
  if (e.target.id === "bugForm") {
    e.preventDefault();
    document.getElementById("status").textContent =
      "Thank you! Your report has been recorded.";
    e.target.reset();
  }
});
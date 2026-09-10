const toast = document.getElementById("toast");
const show = (text) => {
  toast.textContent = text;
  toast.hidden = false;
};
document.getElementById("save").addEventListener("click", async () => {
  const name = document.getElementById("name").value;
  const response = await fetch("/api/settings", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name })
  });
  if (response.ok) {
    localStorage.setItem("name", name);
    show("Saved");
  }
});
document.getElementById("delete").addEventListener("click", () => {});
document.getElementById("boom").addEventListener("click", () => {
  console.error("Kaboom from fixture");
  throw new Error("fixture exploded");
});
document.getElementById("confirm").addEventListener("click", () => {
  show(window.confirm("Really?") ? "Confirmed" : "Cancelled");
});
document.getElementById("top-button").addEventListener("click", () => show("Top clicked"));
document.getElementById("bottom").addEventListener("click", () => show("Bottom clicked"));

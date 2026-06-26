const stateEl = document.getElementById("state");
const reasonEl = document.getElementById("reason");
const checkedEl = document.getElementById("checked");
const refreshButton = document.getElementById("refresh");

function render(status) {
  stateEl.textContent = status?.state || "unknown";
  reasonEl.textContent = status?.reason || "no status yet";
  checkedEl.textContent = status?.checkedAt || "-";
}

async function loadStoredStatus() {
  const { gateStatus } = await chrome.storage.local.get("gateStatus");
  render(gateStatus);
}

refreshButton.addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "refreshGate" }, (response) => {
    render(response);
  });
});

loadStoredStatus();

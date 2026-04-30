const chatLog = document.getElementById("chatLog");
const promptList = document.getElementById("promptList");
const propertyList = document.getElementById("propertyList");
const propertyFilter = document.getElementById("propertyFilter");
const phoneInput = document.getElementById("phoneInput");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const resetBtn = document.getElementById("resetBtn");
const smokeBtn = document.getElementById("smokeBtn");
const smokeStatus = document.getElementById("smokeStatus");
const smokeResults = document.getElementById("smokeResults");
const versionLine = document.getElementById("versionLine");
const releaseNotesLink = document.getElementById("releaseNotesLink");

const smokeComplaintPrompt = "I called a number of times now, but have gotten no response :-(";
const smokeBudgetPrompt = "Show me anything under 2300";

const prompts = [
  "1913 Ridge Creek Ln",
  "How much is rent?",
  smokeComplaintPrompt,
  smokeBudgetPrompt,
  "Can I speak to a human?",
];

let properties = [];
const smokePhone = "+15555559099";

function esc(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function addBubble(role, text, meta = "") {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.innerHTML = `${esc(text)}${meta ? `<small>${esc(meta)}</small>` : ""}`;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderProperties(items) {
  propertyList.innerHTML = "";
  for (const p of items) {
    const card = document.createElement("div");
    card.className = "property-card";
    card.innerHTML = `
      <strong>${esc(p.name)}</strong>
      <span>${esc(p.address)}</span>
      <span>${p.bedrooms} bd / ${p.bathrooms} ba | $${Number(p.rent_per_month).toLocaleString()} / mo</span>
      <span>${esc(p.availability)} | Available from ${esc(p.available_from)}</span>
    `;
    propertyList.appendChild(card);
  }
}

function filteredProperties() {
  const query = (propertyFilter?.value || "").trim().toLowerCase();
  if (!query) {
    return properties;
  }
  return properties.filter((p) => {
    const haystack = [p.name, p.address, p.property_id, p.listing_id, p.city, p.state]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

function renderPrompts() {
  promptList.innerHTML = "";
  for (const prompt of prompts) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "prompt-chip";
    chip.textContent = prompt;
    chip.addEventListener("click", () => {
      messageInput.value = prompt;
      messageInput.focus();
    });
    promptList.appendChild(chip);
  }
}

async function loadProperties() {
  const res = await fetch("/api/properties");
  const data = await res.json();
  properties = data.properties || [];
  renderProperties(properties);
}

async function loadAppInfo() {
  try {
    const res = await fetch("/api/app-info");
    if (!res.ok) return;
    const data = await res.json();
    if (versionLine && data.version) {
      versionLine.textContent = `${data.app_name || "App"} v${data.version}`;
    }
    if (releaseNotesLink && data.release_notes_url) {
      releaseNotesLink.href = data.release_notes_url;
    }
  } catch (err) {
    if (versionLine) {
      versionLine.textContent = "Version unavailable";
    }
  }
}

function setSmokeStatus(text) {
  if (smokeStatus) {
    smokeStatus.textContent = text;
  }
}

function formatSmokeTime(date) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function renderSmokeResult(label, ok, detail) {
  if (!smokeResults) return;
  const row = document.createElement("div");
  row.className = `smoke-result ${ok ? "pass" : "fail"}`;
  row.innerHTML = `<strong>${esc(ok ? "PASS" : "FAIL")}:</strong> ${esc(label)}${detail ? `<br />${esc(detail)}` : ""}`;
  smokeResults.appendChild(row);
}

function pickSmokeProperty(items) {
  const liveProperty = items.find((p) => typeof p.property_id === "string" && p.property_id.trim().length > 0 && p.address);
  return liveProperty || items[0] || null;
}

async function postMessage(phone, text) {
  const res = await fetch("/api/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, text }),
  });
  return res.json();
}

async function resetPhone(phone) {
  await fetch(`/api/reset?phone=${encodeURIComponent(phone)}`, { method: "POST" });
}

async function runSmokeTest(auto = false) {
  if (smokeBtn) {
    smokeBtn.disabled = true;
  }
  setSmokeStatus(auto ? "Running auto smoke test..." : "Running smoke test...");
  if (smokeResults) {
    smokeResults.innerHTML = "";
  }

  try {
    await resetPhone(smokePhone);

    const healthRes = await fetch("/healthz");
    const healthText = (await healthRes.text()).trim();
    renderSmokeResult("Health endpoint returns ok", healthRes.ok && healthText === "ok", `status=${healthRes.status}, body=${healthText || "-"}`);

    const propRes = await fetch("/api/properties");
    const propData = await propRes.json();
    const smokeProps = propData.properties || [];
    const sample = pickSmokeProperty(smokeProps);
    renderSmokeResult("Property list loads", propRes.ok && smokeProps.length > 0, `properties=${smokeProps.length}`);

    if (!sample) {
      setSmokeStatus("Smoke test failed");
      return;
    }

    const exact = await postMessage(smokePhone, sample.address);
    const exactOk = exact.intent === "property_qna" && typeof exact.reply === "string" && exact.reply.length > 0;
    renderSmokeResult(
      `Exact address lookup for ${sample.address}`,
      exactOk,
      `intent=${exact.intent || "-"} | reply=${exact.reply || "-"}`
    );

    if (sample.city) {
      const city = await postMessage(smokePhone, sample.city);
      const cityOk = city.intent === "area_list" || city.intent === "budget_list";
      renderSmokeResult(
        `City lookup for ${sample.city}`,
        cityOk,
        `intent=${city.intent || "-"} | reply=${city.reply || "-"}`
      );
    }

    const handoff = await postMessage(smokePhone, smokeComplaintPrompt);
    const handoffOk = handoff.intent === "human_handoff";
    renderSmokeResult(
      "Complaint-style handoff message",
      handoffOk,
      `intent=${handoff.intent || "-"} | reply=${handoff.reply || "-"}`
    );

    await resetPhone(smokePhone);
    const budget = await postMessage(smokePhone, smokeBudgetPrompt);
    const budgetOk = budget.intent === "budget_list";
    renderSmokeResult(
      "Budget lookup fallback",
      budgetOk,
      `intent=${budget.intent || "-"} | reply=${budget.reply || "-"}`
    );

    setSmokeStatus(`Smoke test passed at ${formatSmokeTime(new Date())}`);
  } catch (err) {
    renderSmokeResult("Smoke test execution", false, err?.message || String(err));
    setSmokeStatus("Smoke test failed");
  } finally {
    if (smokeBtn) {
      smokeBtn.disabled = false;
    }
  }
}

function refreshPropertyList() {
  renderProperties(filteredProperties());
}

async function sendMessage() {
  const phone = phoneInput.value.trim();
  const text = messageInput.value.trim();
  if (!phone || !text) return;

  addBubble("user", text, phone);
  messageInput.value = "";
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone, text }),
    });
    const data = await res.json();
    addBubble("assistant", data.reply, `intent: ${data.intent}${data.property_id ? ` | ${data.property_id}` : ""}`);
  } catch (err) {
    addBubble("assistant", "Sorry, the demo server had a problem responding.");
  } finally {
    sendBtn.disabled = false;
  }
}

async function resetConversation() {
  const phone = phoneInput.value.trim();
  await fetch(`/api/reset?phone=${encodeURIComponent(phone)}`, { method: "POST" });
  chatLog.innerHTML = "";
  addBubble("assistant", "Hi, I am the VP Realty SMS assistant demo. Send a property address or listing ID to get started.", "system");
}

sendBtn.addEventListener("click", sendMessage);
resetBtn.addEventListener("click", resetConversation);
if (smokeBtn) {
  smokeBtn.addEventListener("click", () => runSmokeTest(false));
}
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    sendMessage();
  }
});

renderPrompts();
loadAppInfo();
loadProperties();
resetConversation();

if (propertyFilter) {
  propertyFilter.addEventListener("input", refreshPropertyList);
}

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

const smokeRealCases = [
  {
    label: "Exact property lookup",
    prompt: "1009 Riverstone Trail Princeton, TX 75407",
    expectedIntent: "property_qna",
    expectedTerms: ["1009 Riverstone Trail", "rent $2,195"],
  },
  {
    label: "Budget search from logs",
    prompt: "I am looking for property under 2300 in frisco",
    expectedIntent: "budget_list",
    expectedTerms: ["Frisco under $2,300", "budget options"],
  },
  {
    label: "Tour follow-up from logs",
    prompt:
      "Good morning, I requested a showing for 1009 Riverstone Trail in Princeton for tomorrow at 1130 am. Is there a better time for tomorrow I can show it?",
    expectedIntent: "property_qna",
    expectedTerms: ["1009 Riverstone Trail", "For more details"],
  },
  {
    label: "Contact request from logs",
    prompt: "Who should I contact for details? 100 Stovall Lane Caddo Mills, TX 75135",
    expectedIntent: "property_qna",
    expectedTerms: ["903-213-3818", "nishant@vprealtyservices.com"],
  },
  {
    label: "Entry code from logs",
    prompt: "What is the entry code for this property? 100 Stovall Lane Caddo Mills, TX 75135",
    expectedIntent: "property_qna",
    expectedTerms: ["The entry code is 1975", "property manager at 903-213-3818"],
  },
  {
    label: "Area typo",
    prompt: "Princton",
    expectedIntent: "area_list",
    expectedTerms: ["Princeton", "options"],
  },
  {
    label: "Buyer intent from logs",
    prompt:
      "Hi Niketu, thanks. We're looking to buy (not rent) in Allen/Frisco/Plano-ideally a fixer that needs work. Do you have anything like that available or coming up soon? If so, what's the address?",
    expectedIntent: "area_list",
    expectedTerms: ["Frisco", "options"],
  },
  {
    label: "Call request",
    prompt: "Can you please give me a call about this property?",
    expectedIntent: "area_list",
    expectedTerms: ["options"],
  },
  {
    label: "Property not listed status",
    prompt: "This link says property is not listed on any platform. Can you update me on status?",
    expectedIntent: "area_list",
    expectedTerms: ["options"],
  },
  {
    label: "Tour request",
    prompt:
      "Hi, I am interested in touring a property you have listed at 635 Beltrand Ln, in Fate TX. I have tried to contact someone several times and have not heard back. May I please have more information on the property and when I can tour please and thank you!",
    expectedIntent: "property_qna",
    expectedTerms: ["635 Beltrand", "972-591-8075", "anjali@vprealtyservices.com"],
  },
  {
    label: "No-response handoff",
    prompt: "I called a number of times now, but have gotten no response :-(",
    expectedIntent: "human_handoff",
    expectedTerms: ["leasing specialist"],
  },
  {
    label: "Application fee clarifier",
    prompt: "What is the application fee?",
    expectedIntent: "clarify_property",
    expectedTerms: ["Which area are you looking to rent"],
  },
  {
    label: "Availability lookup",
    prompt: "Is 1009 Riverstone Trail Princeton, TX 75407 still available for lease?",
    expectedIntent: "property_qna",
    expectedTerms: ["currently Vacant-Rented"],
  },
  {
    label: "Rent lookup",
    prompt: "How much is rent? 1009 Riverstone Trail Princeton, TX 75407",
    expectedIntent: "property_qna",
    expectedTerms: ["The rent for", "$2,195 per month"],
  },
  {
    label: "Property summary",
    prompt: "Thanks, Niketu-I appreciate the 1736 Hickory Chase Cir address.",
    expectedIntent: "property_qna",
    expectedTerms: ["1736 Hickory Chase", "4 bedrooms, 3.0 bathrooms"],
  },
];

const prompts = [
  "1009 Riverstone Trail Princeton, TX 75407",
  "I am looking for property under 2300 in frisco",
  "Princton",
  "Can you please give me a call about this property?",
  "What is the application fee?",
  "How much is rent? 1009 Riverstone Trail Princeton, TX 75407",
  "Who should I contact for details? 100 Stovall Lane Caddo Mills, TX 75135",
  "What is the entry code for this property? 100 Stovall Lane Caddo Mills, TX 75135",
  "I called a number of times now, but have gotten no response :-(",
  "Thanks, Niketu-I appreciate the 1736 Hickory Chase Cir address.",
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
    const haystack = [p.name, p.address, p.property_id, p.city, p.state]
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

function includesAny(text, terms) {
  const lower = (text || "").toLowerCase();
  return terms.some((term) => lower.includes(term.toLowerCase()));
}

function pickSmokeProperty(items) {
  const candidates = items.filter(
    (p) =>
      typeof p.property_id === "string" &&
      p.property_id.trim().length > 0 &&
      typeof p.address === "string" &&
      p.address.trim().length > 0
  );
  if (candidates.length === 0) {
    return items[0] || null;
  }
  const index = Math.floor(Math.random() * candidates.length);
  return candidates[index];
}

function hasCity(items, city) {
  const target = (city || "").trim().toLowerCase();
  if (!target) return false;
  return items.some((p) => (p.city || "").trim().toLowerCase() === target);
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
    renderSmokeResult("Property list loads", propRes.ok && smokeProps.length > 0, `properties=${smokeProps.length}`);

    for (const realCase of smokeRealCases) {
      await resetPhone(smokePhone);
      const response = await postMessage(smokePhone, realCase.prompt);
      const responseOk =
        response.intent === realCase.expectedIntent &&
        includesAny(response.reply, realCase.expectedTerms);
      renderSmokeResult(
        `Real question: ${realCase.label}`,
        responseOk,
        `intent=${response.intent || "-"} | reply=${response.reply || "-"}`
      );
    }

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
  addBubble("assistant", "Hi, I am the VP Realty SMS assistant demo. Send a property address to get started.", "system");
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

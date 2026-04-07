const chatLog = document.getElementById("chatLog");
const promptList = document.getElementById("promptList");
const propertyList = document.getElementById("propertyList");
const propertyFilter = document.getElementById("propertyFilter");
const phoneInput = document.getElementById("phoneInput");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const resetBtn = document.getElementById("resetBtn");

const prompts = [
  "Is 123 Main St available?",
  "How much is rent for Maple Ridge Apartments?",
  "How many bedrooms and bathrooms does 45 Cedar Park Blvd have?",
  "When is Sycamore Flats available from?",
  "Can I speak to a human?",
];

let properties = [];

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
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    sendMessage();
  }
});

renderPrompts();
loadProperties();
resetConversation();

if (propertyFilter) {
  propertyFilter.addEventListener("input", refreshPropertyList);
}

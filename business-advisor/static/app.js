const form = document.querySelector("#queryForm");
const queryInput = document.querySelector("#queryInput");
const runButton = document.querySelector("#runButton");
const systemState = document.querySelector("#systemState");
const clarificationPanel = document.querySelector("#clarificationPanel");
const clarificationQuestion = document.querySelector("#clarificationQuestion");
const clarificationForm = document.querySelector("#clarificationForm");
const clarificationInput = document.querySelector("#clarificationInput");
const messagePanel = document.querySelector("#messagePanel");

let activeQuery = queryInput.value.trim();

function setRunning(isRunning) {
  runButton.disabled = isRunning;
  runButton.textContent = isRunning ? "Running" : "Run Mission";
  systemState.classList.toggle("running", isRunning);
  systemState.lastChild.textContent = isRunning ? " Running" : " Ready";
}

function chipList(id, values) {
  const target = document.querySelector(id);
  const items = values && values.length ? values : ["none"];
  target.innerHTML = items.map((value) => `<span class="chip">${escapeHtml(value)}</span>`).join("");
}

function setStage(name) {
  document.querySelectorAll(".stage").forEach((stage) => {
    stage.classList.remove("active", "done");
    if (stage.dataset.stage === name) stage.classList.add("active");
  });
}

function markAllStagesDone() {
  document.querySelectorAll(".stage").forEach((stage) => {
    stage.classList.remove("active");
    stage.classList.add("done");
  });
}

function showMessage(report) {
  clarificationPanel.classList.add("hidden");
  messagePanel.classList.remove("hidden");
  messagePanel.innerHTML = `
    <strong>${escapeHtml(report.action || "Advisor")}</strong>
    <p>${escapeHtml(report.message || report.planner_notes || "No message returned.")}</p>
    <p><strong>Planner:</strong> ${escapeHtml(report.planner || "-")}</p>
  `;
}

function showClarification(report) {
  messagePanel.classList.add("hidden");
  clarificationPanel.classList.remove("hidden");
  clarificationQuestion.textContent = report.clarification_question;
  clarificationInput.value = "";
  clarificationInput.focus();
}

function renderReport(report) {
  clarificationPanel.classList.add("hidden");
  messagePanel.classList.add("hidden");
  markAllStagesDone();

  document.querySelector("#plannerBadge").textContent = report.planner || "llm";
  document.querySelector("#countryValue").textContent = report.country || "-";
  document.querySelector("#budgetValue").textContent = report.budget_usd ? `USD ${Number(report.budget_usd).toLocaleString()}` : "-";
  document.querySelector("#focusValue").textContent = report.focus || "-";
  document.querySelector("#actionValue").textContent = report.action || "-";
  document.querySelector("#plannerNotes").textContent = report.planner_notes || "-";
  document.querySelector("#budgetSummary").textContent = report.budget_summary || "-";

  chipList("#identifiedTools", report.identified_tools);
  chipList("#selectedTools", report.selected_tools);
  chipList("#identifiedAgents", report.identified_agent_capabilities);
  chipList("#selectedAgents", report.selected_agent_capabilities);

  renderA2A(report.a2a_events || []);
  renderRecommendations(report.recommendations || []);
}

function renderA2A(events) {
  const target = document.querySelector("#a2aTimeline");
  document.querySelector("#a2aCount").textContent = `${events.length} calls`;
  if (!events.length) {
    target.innerHTML = `<p class="empty">No external A2A agents were called for this request.</p>`;
    return;
  }

  target.innerHTML = events
    .map(
      (event, index) => `
        <article class="a2a-event">
          <h3>A2A-${index + 1}: ${escapeHtml(event.capability)}</h3>
          <dl>
            <dt>Agent Card</dt><dd>${escapeHtml(event.agent_name)} | ${escapeHtml(event.agent_id)} | v${escapeHtml(event.version)}</dd>
            <dt>Endpoint</dt><dd>${escapeHtml(event.endpoint)}</dd>
            <dt>Envelope</dt><dd>to=${escapeHtml(event.agent_id)} capability=${escapeHtml(event.capability)}</dd>
            <dt>Payload</dt><dd>${escapeHtml((event.payload_keys || []).join(", "))}</dd>
            <dt>Response</dt><dd>${event.response_items} product-level result(s)</dd>
          </dl>
        </article>
      `,
    )
    .join("");
}

function renderRecommendations(recommendations) {
  const target = document.querySelector("#recommendations");
  if (!recommendations.length) {
    target.innerHTML = `<p class="empty">No recommendations returned.</p>`;
    return;
  }

  target.innerHTML = recommendations
    .map(
      (item, index) => `
        <article class="recommendation">
          <div class="rec-head">
            <div>
              <h3>${index + 1}. ${escapeHtml(item.name)}</h3>
              <p>${escapeHtml(item.summary)}</p>
            </div>
            <div class="score">${item.score}</div>
          </div>
          <p class="status-line">${escapeHtml(item.budget_status)} | Startup cost USD ${Number(item.estimated_startup_cost).toLocaleString()}</p>
          <p><strong>Profit:</strong> ${escapeHtml(item.profit_potential)}</p>
          <p><strong>Market:</strong> ${escapeHtml(item.market_notes)}</p>
          ${item.supplier_notes ? `<p><strong>Supplier Agent:</strong> ${escapeHtml(item.supplier_notes)}</p>` : ""}
          ${item.finance_notes ? `<p><strong>Finance Agent:</strong> ${escapeHtml(item.finance_notes)}</p>` : ""}
          ${item.compliance_notes ? `<p><strong>Compliance Agent:</strong> ${escapeHtml(item.compliance_notes)}</p>` : ""}
          <div class="risk-list">${(item.risks || []).map((risk) => `<span>${escapeHtml(risk)}</span>`).join("")}</div>
        </article>
      `,
    )
    .join("");
}

function formatClarification(question, answer) {
  const normalized = question.toLowerCase();
  if (normalized.includes("country") && normalized.includes("budget")) return `Target country and budget: ${answer}.`;
  if (normalized.includes("budget")) return `Budget is USD ${answer}.`;
  if (normalized.includes("country")) return `Target country is ${answer}.`;
  return answer;
}

async function analyze(query) {
  setRunning(true);
  setStage("planner");
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const report = await response.json();
    if (!response.ok) throw new Error(report.error || report.message || "Request failed");

    if (report.action === "ask_clarification") {
      activeQuery = query;
      showClarification(report);
      return;
    }

    if (["out_of_scope", "planner_error", "unsupported_country", "server_error"].includes(report.action)) {
      showMessage(report);
      return;
    }

    renderReport(report);
  } catch (error) {
    showMessage({ action: "error", message: error.message, planner: "browser" });
  } finally {
    setRunning(false);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  activeQuery = queryInput.value.trim();
  analyze(activeQuery);
});

clarificationForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const answer = clarificationInput.value.trim();
  if (!answer) return;
  const clarification = formatClarification(clarificationQuestion.textContent, answer);
  activeQuery = `${activeQuery}\nClarification: ${clarification}`;
  queryInput.value = activeQuery;
  analyze(activeQuery);
});

document.querySelectorAll(".quick-prompts button").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.query;
    activeQuery = queryInput.value.trim();
  });
});

chipList("#identifiedTools", []);
chipList("#selectedTools", []);
chipList("#identifiedAgents", []);
chipList("#selectedAgents", []);

const consoleForm = document.querySelector("#consoleForm");
const consoleQuery = document.querySelector("#consoleQuery");
const runConsole = document.querySelector("#runConsole");
const terminalOutput = document.querySelector("#terminalOutput");
const stepCounter = document.querySelector("#stepCounter");
const prevStep = document.querySelector("#prevStep");
const nextStep = document.querySelector("#nextStep");
const playSteps = document.querySelector("#playSteps");
const showAll = document.querySelector("#showAll");
const clarificationBox = document.querySelector("#clarificationBox");
const clarificationText = document.querySelector("#clarificationText");
const clarificationForm = document.querySelector("#consoleClarificationForm");
const clarificationInput = document.querySelector("#consoleClarificationInput");
const errorBox = document.querySelector("#errorBox");

let activeQuery = consoleQuery.value.trim();
let steps = [];
let visibleIndex = 0;
let playTimer = null;

function setBusy(isBusy) {
  runConsole.disabled = isBusy;
  runConsole.textContent = isBusy ? "Building" : "Build Steps";
}

async function analyze(query) {
  setBusy(true);
  errorBox.classList.add("hidden");
  clarificationBox.classList.add("hidden");
  terminalOutput.innerHTML = `<article class="terminal-step visible"><p class="line muted">$ contacting Business Advisor Agent...</p></article>`;
  stepCounter.textContent = "Mission running";

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
      clarificationText.textContent = report.clarification_question;
      clarificationInput.value = "";
      clarificationBox.classList.remove("hidden");
      stepCounter.textContent = "Clarification needed";
      return;
    }

    if (["out_of_scope", "planner_error", "unsupported_country", "server_error"].includes(report.action)) {
      renderMessage(report);
      return;
    }

    steps = buildSteps(report);
    visibleIndex = 0;
    renderSteps();
  } catch (error) {
    renderMessage({ action: "error", message: error.message, planner_notes: "" });
  } finally {
    setBusy(false);
  }
}

function buildSteps(report) {
  const a2aBlocks = (report.a2a_events || [])
    .map(
      (event, index) => `
        <div class="block">
          <p class="line green">A2A-${index + 1}: ${esc(event.capability)}</p>
          <p class="line">Agent Card: ${esc(event.agent_name)} | ${esc(event.agent_id)} | v${esc(event.version)}</p>
          <p class="line">Endpoint: ${esc(event.endpoint)}</p>
          <p class="line">Task Envelope: to=${esc(event.agent_id)} capability=${esc(event.capability)}</p>
          <p class="line">Payload Keys: ${esc((event.payload_keys || []).join(", "))}</p>
          <p class="line">Response: ${event.response_items} product-level result(s)</p>
        </div>
      `,
    )
    .join("");

  const recBlocks = (report.recommendations || [])
    .map(
      (item, index) => `
        <div class="block">
          <p class="line green">${index + 1}. ${esc(item.name)} | Score ${item.score}/100</p>
          <p class="line">Startup Cost: USD ${Number(item.estimated_startup_cost).toLocaleString()}</p>
          <p class="line">Budget Status: ${esc(item.budget_status)}</p>
          <p class="line">Summary: ${esc(item.summary)}</p>
          <p class="line">Risks: ${esc((item.risks || []).join(", "))}</p>
        </div>
      `,
    )
    .join("");

  return [
    {
      title: "01 / User Request",
      html: `
        <p class="line muted">$ founder.query</p>
        <p class="line">${esc(report.raw_query).replaceAll("\n", " | ")}</p>
        <p class="line">Country: <span class="green">${esc(report.country)}</span></p>
        <p class="line">Budget: <span class="green">USD ${Number(report.budget_usd).toLocaleString()}</span></p>
      `,
    },
    {
      title: "02 / LLM Planner Decision",
      html: `
        <p class="line muted">$ advisor.planner.run(model="llm")</p>
        <p class="line">Focus: <span class="blue">${esc(report.focus)}</span></p>
        <p class="line">Planner: <span class="blue">${esc(report.planner)}</span></p>
        <div class="block">${esc(report.planner_notes)}</div>
      `,
    },
    {
      title: "03 / Discovery Surface",
      html: `
        <p class="line muted">$ registry.discover_available_tools()</p>
        <p class="line">Identified Tools: <span class="gold">${esc((report.identified_tools || []).join(", "))}</span></p>
        <p class="line muted">$ registry.discover_agent_capabilities()</p>
        <p class="line">Identified Agent Capabilities: <span class="gold">${esc((report.identified_agent_capabilities || []).join(", "))}</span></p>
      `,
    },
    {
      title: "04 / LLM Selection",
      html: `
        <p class="line muted">$ planner.selection</p>
        <p class="line">Selected Tools: <span class="green">${esc((report.selected_tools || []).join(", ") || "none")}</span></p>
        <p class="line">Selected Agent Capabilities: <span class="green">${esc((report.selected_agent_capabilities || []).join(", ") || "none")}</span></p>
        <p class="line">Execution Plan: <span class="blue">${esc((report.execution_plan || []).join(" -> "))}</span></p>
      `,
    },
    {
      title: "05 / A2A Message Exchange",
      html: a2aBlocks || `<p class="line muted">No external A2A agents were called for this request.</p>`,
    },
    {
      title: "06 / MCP And Advisor Trace",
      html: (report.trace || []).map((line) => `<p class="line">> ${esc(line)}</p>`).join(""),
    },
    {
      title: "07 / Budget Fit",
      html: `
        <p class="line muted">$ advisor.filter_by_budget()</p>
        <div class="block">${esc(report.budget_summary)}</div>
      `,
    },
    {
      title: "08 / Final Recommendations",
      html: recBlocks,
    },
    {
      title: "09 / Recommended Next Step",
      html: `
        <p class="line muted">$ advisor.next_step</p>
        <div class="block green">${esc(report.next_step)}</div>
      `,
    },
  ];
}

function renderSteps() {
  terminalOutput.innerHTML = steps
    .map(
      (step, index) => `
        <article class="terminal-step ${index <= visibleIndex ? "visible" : ""}">
          <h2>${step.title}</h2>
          ${step.html}
        </article>
      `,
    )
    .join("");
  stepCounter.textContent = `Showing step ${Math.min(visibleIndex + 1, steps.length)} of ${steps.length}`;
  terminalOutput.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
}

function renderMessage(report) {
  steps = [
    {
      title: "Advisor Response",
      html: `
        <p class="line red">${esc(report.action || "message")}</p>
        <div class="block">${esc(report.message || report.planner_notes || "No details returned.")}</div>
      `,
    },
  ];
  visibleIndex = 0;
  renderSteps();
}

function formatClarification(question, answer) {
  const normalized = question.toLowerCase();
  if (normalized.includes("country") && normalized.includes("budget")) return `Target country and budget: ${answer}.`;
  if (normalized.includes("budget")) return `Budget is USD ${answer}.`;
  if (normalized.includes("country")) return `Target country is ${answer}.`;
  return answer;
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

consoleForm.addEventListener("submit", (event) => {
  event.preventDefault();
  activeQuery = consoleQuery.value.trim();
  analyze(activeQuery);
});

clarificationForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const answer = clarificationInput.value.trim();
  if (!answer) return;
  const clarification = formatClarification(clarificationText.textContent, answer);
  activeQuery = `${activeQuery}\nClarification: ${clarification}`;
  consoleQuery.value = activeQuery;
  analyze(activeQuery);
});

nextStep.addEventListener("click", () => {
  if (!steps.length) return;
  visibleIndex = Math.min(visibleIndex + 1, steps.length - 1);
  renderSteps();
});

prevStep.addEventListener("click", () => {
  if (!steps.length) return;
  visibleIndex = Math.max(visibleIndex - 1, 0);
  renderSteps();
});

showAll.addEventListener("click", () => {
  if (!steps.length) return;
  visibleIndex = steps.length - 1;
  renderSteps();
});

playSteps.addEventListener("click", () => {
  if (!steps.length) return;
  if (playTimer) {
    clearInterval(playTimer);
    playTimer = null;
    playSteps.textContent = "Play";
    return;
  }
  playSteps.textContent = "Pause";
  playTimer = setInterval(() => {
    if (visibleIndex >= steps.length - 1) {
      clearInterval(playTimer);
      playTimer = null;
      playSteps.textContent = "Play";
      return;
    }
    visibleIndex += 1;
    renderSteps();
  }, 1200);
});

// PulseOps Console Client Logic
let currentConversationId = null;

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initChat();
  initQuickPills();
  initRefreshButtons();
  loadSystemHealth();
  loadTicketDrafts();
  loadPRSummaries();
  loadServices();
});

// Navigation Handling
function initNavigation() {
  const navTabs = document.querySelectorAll(".nav-item");
  const tabViews = document.querySelectorAll(".tab-view");

  navTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetViewId = tab.getAttribute("data-tab");
      
      navTabs.forEach((t) => t.classList.remove("active"));
      tabViews.forEach((v) => v.classList.remove("active"));

      tab.classList.add("active");
      const targetView = document.getElementById(targetViewId);
      if (targetView) targetView.classList.add("active");

      // Auto-refresh data when opening tabs
      if (targetViewId === "tickets-view") loadTicketDrafts();
      if (targetViewId === "prs-view") loadPRSummaries();
      if (targetViewId === "services-view") loadServices();
    });
  });
}

// Quick Scenario Pills
function initQuickPills() {
  const pills = document.querySelectorAll(".pill-btn");
  const input = document.getElementById("chat-input");
  const form = document.getElementById("chat-form");

  pills.forEach((pill) => {
    pill.addEventListener("click", () => {
      const prompt = pill.getAttribute("data-prompt");
      if (prompt) {
        input.value = prompt;
        form.dispatchEvent(new Event("submit"));
      }
    });
  });

  const newSessionBtn = document.getElementById("btn-new-conversation");
  if (newSessionBtn) {
    newSessionBtn.addEventListener("click", () => {
      currentConversationId = null;
      const chatMessages = document.getElementById("chat-messages");
      chatMessages.innerHTML = `
        <div class="message assistant-message initial-welcome">
          <div class="avatar"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg></div>
          <div class="message-bubble">
            <div class="message-text">Fresh session initialized. How can PulseOps help you today?</div>
          </div>
        </div>
      `;
    });
  }
}

// Refresh Buttons
function initRefreshButtons() {
  document.getElementById("btn-refresh-tickets")?.addEventListener("click", loadTicketDrafts);
  document.getElementById("btn-refresh-prs")?.addEventListener("click", loadPRSummaries);
  document.getElementById("btn-refresh-services")?.addEventListener("click", loadServices);
}

// System Health
async function loadSystemHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("status-engine").innerText = data.llm_mode || "mock";
    document.getElementById("status-model").innerText = data.default_model || "none";
  } catch (e) {
    console.error("Health check error:", e);
  }
}

// Chat Flow
function initChat() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const chatMessages = document.getElementById("chat-messages");
  const chatContainer = document.getElementById("chat-container");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    // Append User Message
    appendMessage("user", message);
    input.value = "";

    // Show Loading Bubble
    const loadingId = "loading-" + Date.now();
    appendLoadingBubble(loadingId);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          conversation_id: currentConversationId
        })
      });

      removeLoadingBubble(loadingId);

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        appendMessage("assistant", "⚠️ Error: " + (errData.detail || "Failed to process request."));
        return;
      }

      const data = await response.json();
      currentConversationId = data.conversation_id;

      // Append Assistant Message with Tool Traces Timeline
      appendMessage("assistant", data.answer, data.traces);
      chatContainer.scrollTop = chatContainer.scrollHeight;

      // Update badges
      loadTicketDrafts();
      loadPRSummaries();

    } catch (err) {
      removeLoadingBubble(loadingId);
      appendMessage("assistant", "⚠️ Connection error: " + err.message);
    }
  });
}

function appendMessage(role, text, traces = []) {
  const chatMessages = document.getElementById("chat-messages");
  const msgEl = document.createElement("div");
  msgEl.className = `message ${role}-message`;

  const avatarSvg = role === "user" 
    ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`
    : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`;

  let tracesHtml = "";
  if (traces && traces.length > 0) {
    const traceItems = traces.map((t) => `
      <div class="trace-item">
        <div class="trace-item-header">
          <span class="trace-tool-name">⚡ Tool: ${escapeHtml(t.tool_name)} (step ${t.step})</span>
          <span class="trace-status-badge">${t.ok ? "✓ SUCCESS" : "✗ ERROR"}</span>
        </div>
        <div class="trace-json"><strong>Args:</strong> ${escapeHtml(JSON.stringify(t.args))}</div>
        <div class="trace-json"><strong>Result:</strong> ${escapeHtml(JSON.stringify(t.result).substring(0, 180))}...</div>
      </div>
    `).join("");

    tracesHtml = `
      <div class="traces-timeline">
        <button class="traces-toggle-btn" onclick="toggleTraceTimeline(this)">
          🔍 View Tool Traces (${traces.length} steps)
        </button>
        <div class="trace-items-container" style="display: none;">
          ${traceItems}
        </div>
      </div>
    `;
  }

  // Basic markdown formatting
  let formattedText = escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="font-family:monospace;background:rgba(255,255,255,0.08);padding:2px 4px;border-radius:4px;">$1</code>')
    .replace(/\n/g, '<br>');

  msgEl.innerHTML = `
    <div class="avatar">${avatarSvg}</div>
    <div class="message-bubble">
      <div class="message-text">${formattedText}</div>
      ${tracesHtml}
    </div>
  `;

  chatMessages.appendChild(msgEl);
}

function toggleTraceTimeline(btn) {
  const container = btn.nextElementSibling;
  if (container.style.display === "none") {
    container.style.display = "flex";
    btn.innerText = "Hide Tool Traces";
  } else {
    container.style.display = "none";
    btn.innerText = "🔍 View Tool Traces";
  }
}

function appendLoadingBubble(id) {
  const chatMessages = document.getElementById("chat-messages");
  const msgEl = document.createElement("div");
  msgEl.id = id;
  msgEl.className = "message assistant-message";
  msgEl.innerHTML = `
    <div class="avatar"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg></div>
    <div class="message-bubble">
      <div class="message-text" style="color: var(--accent-cyan); display: flex; align-items: center; gap: 8px;">
        <span class="pulse-indicator"></span> Reasoning and dispatching tools...
      </div>
    </div>
  `;
  chatMessages.appendChild(msgEl);
}

function removeLoadingBubble(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// Load Ticket Drafts Table
async function loadTicketDrafts() {
  try {
    const res = await fetch("/api/ticket-drafts");
    if (!res.ok) return;
    const data = await res.json();
    const tbody = document.getElementById("tickets-tbody");
    const countBadge = document.getElementById("ticket-count-badge");
    if (countBadge) countBadge.innerText = data.count || 0;

    if (!data.ticket_drafts || data.ticket_drafts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No ticket drafts yet. Ask PulseOps to create one!</td></tr>`;
      return;
    }

    tbody.innerHTML = data.ticket_drafts.map((d) => `
      <tr>
        <td style="font-family:monospace; font-weight:600; color:var(--accent-cyan);">${escapeHtml(d.id)}</td>
        <td style="font-weight:500;">${escapeHtml(d.title)}</td>
        <td><span class="priority-tag priority-${d.priority}">${escapeHtml(d.priority)}</span></td>
        <td>${escapeHtml(d.team || "unassigned")}</td>
        <td>${(d.labels || []).map(l => `<span style="font-size:0.75rem; background:rgba(255,255,255,0.06); padding:2px 6px; border-radius:4px; margin-right:4px;">${escapeHtml(l)}</span>`).join("")}</td>
        <td style="font-size:0.8rem; color:var(--text-muted);">${new Date(d.created_at).toLocaleTimeString()}</td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load tickets:", err);
  }
}

// Load PR Summaries
async function loadPRSummaries() {
  try {
    const res = await fetch("/api/pr-summaries");
    if (!res.ok) return;
    const data = await res.json();
    const container = document.getElementById("prs-cards-container");
    const countBadge = document.getElementById("pr-count-badge");
    if (countBadge) countBadge.innerText = data.count || 0;

    if (!data.pr_summaries || data.pr_summaries.length === 0) {
      container.innerHTML = `<div class="empty-state-card" style="color:var(--text-muted); padding:30px;">No PR summaries saved yet. Use the prompt pill 'Summarize PR #101' to generate one.</div>`;
      return;
    }

    container.innerHTML = data.pr_summaries.map((item) => {
      const s = item.summary || {};
      const riskColor = s.risk_level === "HIGH" ? "var(--accent-rose)" : s.risk_level === "MEDIUM" ? "var(--accent-amber)" : "var(--accent-emerald)";
      return `
        <div class="card">
          <div class="card-title">PR #${item.pr_number}: ${escapeHtml(s.title || "Pull Request")}</div>
          <div class="card-meta">
            <span>Record: ${item.id}</span>
            <span>•</span>
            <span style="color:${riskColor}; font-weight:700;">Risk: ${escapeHtml(s.risk_level || "UNKNOWN")}</span>
          </div>
          <div class="card-desc">${escapeHtml(s.overview || "")}</div>
          <div style="font-size:0.8rem; margin-bottom:10px;">
            <strong style="color:var(--text-primary);">Risk Notes:</strong>
            <ul style="padding-left:16px; margin-top:4px; color:var(--text-secondary);">
              ${(s.risk_notes || []).map(n => `<li>${escapeHtml(n)}</li>`).join("")}
            </ul>
          </div>
          <div class="card-footer">
            <span>Service: <code>${escapeHtml(s.service || "unknown")}</code></span>
            <span>${new Date(item.created_at).toLocaleTimeString()}</span>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load PR summaries:", err);
  }
}

// Load Services
async function loadServices() {
  try {
    const res = await fetch("/api/services");
    if (!res.ok) return;
    const data = await res.json();
    const container = document.getElementById("services-cards-container");

    container.innerHTML = (data.services || []).map((s) => `
      <div class="card">
        <div class="card-title">${escapeHtml(s.name)}</div>
        <div class="card-meta">
          <span>Tier: ${escapeHtml(s.tier || "Tier-1")}</span>
          <span>•</span>
          <span>SLO: ${s.slo_availability}%</span>
          <span>•</span>
          <span>P99: ${s.slo_latency_p99_ms}ms</span>
        </div>
        <div class="card-desc">${escapeHtml(s.description || "")}</div>
        <div style="font-size:0.8rem; margin-bottom:12px; color:var(--text-secondary);">
          <div><strong>Team:</strong> ${escapeHtml(s.team)} (<code>${escapeHtml(s.oncall)}</code>)</div>
          <div><strong>Dependencies:</strong> ${(s.depends_on || []).map(d => `<code>${escapeHtml(d)}</code>`).join(", ") || "None"}</div>
        </div>
        <div class="card-footer">
          <span>Repo: ${escapeHtml(s.repo)}</span>
          <span style="font-family:monospace; color:var(--accent-cyan);">${escapeHtml(s.id)}</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Failed to load services:", err);
  }
}

function escapeHtml(str) {
  if (typeof str !== "string") return str ? String(str) : "";
  return str.replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  })[m]);
}

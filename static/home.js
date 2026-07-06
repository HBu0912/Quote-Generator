const searchInput = document.getElementById("search-input");
const resultsTable = document.querySelector("#results-table tbody");
const resultsEmpty = document.getElementById("results-empty");
const resultsTitle = document.getElementById("results-title");
const resultsCount = document.getElementById("results-count");

async function loadQuotes(query = "") {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  const res = await fetch(`/api/quotes/search?${params}`);
  const quotes = await res.json();
  renderResults(quotes, query);
}

function renderResults(quotes, query) {
  resultsTable.innerHTML = "";
  resultsTitle.textContent = query ? `Search Results for "${query}"` : "Recent Quotes";
  resultsCount.textContent = quotes.length ? `${quotes.length} quote${quotes.length === 1 ? "" : "s"}` : "";

  if (!quotes.length) {
    resultsEmpty.classList.remove("hidden");
    return;
  }
  resultsEmpty.classList.add("hidden");

  for (const q of quotes) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${esc(q.inquiry_no || "—")}</strong></td>
      <td>${esc(q.factory_name || "—")}</td>
      <td>${formatDate(q.quotation_date)}</td>
      <td>${q.part_count}</td>
      <td class="pn-cell">${esc((q.part_numbers || []).join(", "))}${q.part_count > 5 ? "…" : ""}</td>
      <td>${formatDateTime(q.updated_at)}</td>
      <td class="row-actions">
        <a href="/quote/${q.id}" class="btn secondary">Open</a>
        <button type="button" class="btn danger delete-quote-btn" data-id="${q.id}" data-inquiry="${esc(q.inquiry_no || "this quote")}">Delete</button>
      </td>
    `;
    resultsTable.appendChild(tr);
  }

  resultsTable.querySelectorAll(".delete-quote-btn").forEach((btn) => {
    btn.addEventListener("click", () => deleteQuote(btn.dataset.id, btn.dataset.inquiry, query));
  });
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
}

function formatDate(d) {
  if (!d) return "—";
  return new Date(d + "T00:00:00").toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function formatDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}

function doSearch() {
  loadQuotes(searchInput.value.trim());
}

async function deleteQuote(id, inquiry, query = searchInput.value.trim()) {
  const label = inquiry || "this quote";
  if (!confirm(`Delete quote "${label}"? This cannot be undone.`)) return;
  const res = await fetch(`/api/quotes/${id}`, { method: "DELETE" });
  if (!res.ok) {
    alert("Could not delete quote.");
    return;
  }
  loadQuotes(query);
}

document.getElementById("search-btn").addEventListener("click", doSearch);
searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });

loadQuotes();

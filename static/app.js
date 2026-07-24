const tbody = document.querySelector("#line-items tbody");
const customContainer = document.getElementById("custom-fields");
const gageListContainer = document.getElementById("gage-list");
const previewPanel = document.getElementById("preview-panel");
const quoteIdInput = document.getElementById("quote_id");
const saveStatus = document.getElementById("save-status");

const DEFAULT_COLUMN_LABELS = {
  part_number: "P/N",
  cast_dwg: "Cast DWG#",
  mach_dwg: "Mach DWG#",
  description: "Description",
  material: "Material",
  qty: "Quantity",
  factory_unit_price_vnd: "Unit Price FOB",
  factory_weight_kg: "Weight (kg)",
  factory_mold_fee_vnd: "Mold Fee",
  other_finish: "Other/Finish",
  pressure_testing: "Pressure Testing",
  sample_factory_cost_vnd: "Sample Fee",
  unit_price_markup_pct: "Unit Markup %",
  mold_fee_markup_pct: "Mold Markup %",
};

const LINE_ITEM_COLUMNS = Object.entries(DEFAULT_COLUMN_LABELS).map(([field, label]) => ({ field, label }));

let currentQuoteId = quoteIdInput?.value || window.QUOTE_ID || "";
let previewData = null;
let selectedScenario = new Map();

function buildColumnHeaders(savedLabels = {}) {
  const thead = document.getElementById("line-items-head");
  const tr = document.createElement("tr");
  tr.innerHTML = `<th class="row-num-col">#</th>` + LINE_ITEM_COLUMNS.map(({ field, label }) => {
    const value = savedLabels[field] || label;
    return `<th><input type="text" class="col-label" data-field="${field}" value="${esc(value)}" aria-label="Column name for ${esc(label)}"></th>`;
  }).join("") + `<th class="row-actions-col"></th>`;
  thead.innerHTML = "";
  thead.appendChild(tr);
}

function collectColumnLabels() {
  const labels = {};
  document.querySelectorAll(".col-label").forEach((input) => {
    const field = input.dataset.field;
    const value = input.value.trim();
    if (value) labels[field] = value;
  });
  return labels;
}

function applyColumnLabels(savedLabels = {}) {
  document.querySelectorAll(".col-label").forEach((input) => {
    const field = input.dataset.field;
    input.value = savedLabels[field] || DEFAULT_COLUMN_LABELS[field] || "";
  });
}

function formatQtyOptions(data) {
  if (Array.isArray(data.qty_options) && data.qty_options.length) {
    return data.qty_options.join(", ");
  }
  if (data.qty) return String(data.qty);
  return "";
}

function parseQtyOptions(str) {
  if (!str || !String(str).trim()) return [];
  return String(str)
    .split(/[,;\s]+/)
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !Number.isNaN(n) && n > 0);
}

function formatFactoryPrices(data) {
  if (Array.isArray(data.factory_unit_price_vnd_options) && data.factory_unit_price_vnd_options.length) {
    return data.factory_unit_price_vnd_options.join(", ");
  }
  if (data.factory_unit_price_vnd != null && data.factory_unit_price_vnd !== "") {
    return String(data.factory_unit_price_vnd);
  }
  return "";
}

function parseFactoryPrices(str) {
  if (!str || !String(str).trim()) return [];
  return String(str)
    .split(/[,;\s]+/)
    .map((s) => parseFloat(s.trim()))
    .filter((n) => !Number.isNaN(n) && n >= 0);
}

function resolveSampleCost(data) {
  if (data.sample_factory_cost_vnd != null && data.sample_factory_cost_vnd !== "") {
    return data.sample_factory_cost_vnd;
  }
  const unit = parseFloat(data.sample_factory_unit_price_vnd);
  if (Number.isNaN(unit) || unit <= 0) return "";
  const qty = parseInt(data.sample_qty, 10);
  return qty > 0 ? unit * qty : unit;
}

function addLineItem(data = {}) {
  const tr = document.createElement("tr");
  tr.className = "line-item-row";
  tr.innerHTML = `
    <td class="row-num"></td>
    <td><input name="part_number" value="${esc(data.part_number || "")}"></td>
    <td><textarea name="cast_dwg" rows="2">${esc(data.cast_dwg || "")}</textarea></td>
    <td><textarea name="mach_dwg" rows="2">${esc(data.mach_dwg || "")}</textarea></td>
    <td><textarea name="description" rows="2">${esc(data.description || "")}</textarea></td>
    <td><input name="material" value="${esc(data.material || "")}"></td>
    <td><input name="qty_options" class="qty-options" value="${esc(formatQtyOptions(data))}" placeholder="25, 50, 100" title="Comma-separated quantities — pairs with factory prices by position"></td>
    <td><input name="factory_unit_price_vnd" class="factory-prices" value="${esc(formatFactoryPrices(data))}" placeholder="120000, 100000" title="Comma-separated factory prices (VND) — one per quantity, left to right"></td>
    <td><input type="number" name="factory_weight_kg" value="${data.factory_weight_kg ?? ""}" step="0.001"></td>
    <td><input type="number" name="factory_mold_fee_vnd" value="${data.factory_mold_fee_vnd ?? ""}" step="1"></td>
    <td><textarea name="other_finish" rows="2">${esc(data.other_finish || "")}</textarea></td>
    <td><textarea name="pressure_testing" rows="2">${esc(data.pressure_testing || "")}</textarea></td>
    <td><input type="number" name="sample_factory_cost_vnd" value="${resolveSampleCost(data)}" step="1" min="0" placeholder="Total VND"></td>
    <td><input type="number" name="unit_price_markup_pct" value="${data.unit_price_markup_pct ?? ""}" placeholder="default" step="0.1"></td>
    <td><input type="number" name="mold_fee_markup_pct" value="${data.mold_fee_markup_pct ?? ""}" placeholder="default" step="0.1"></td>
    <td><button type="button" class="btn danger remove-row">×</button></td>
  `;
  tbody.appendChild(tr);
  tr.querySelector(".remove-row").addEventListener("click", () => { tr.remove(); renumber(); });
  renumber();
}

function renumber() {
  tbody.querySelectorAll("tr.line-item-row").forEach((tr, i) => { tr.querySelector(".row-num").textContent = i + 1; });
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function addCustomField(label = "", value = "") {
  const row = document.createElement("div");
  row.className = "custom-row";
  row.innerHTML = `
    <input placeholder="Field label" class="custom-label" value="${esc(label)}">
    <input placeholder="Field value" class="custom-value" value="${esc(value)}">
    <button type="button" class="btn danger remove-custom">×</button>
  `;
  row.querySelector(".remove-custom").addEventListener("click", () => row.remove());
  customContainer.appendChild(row);
}

function lineItemPartNumbers() {
  const parts = [];
  tbody.querySelectorAll("tr.line-item-row").forEach((tr) => {
    const pn = tr.querySelector('[name="part_number"]')?.value.trim();
    if (pn) parts.push(pn);
  });
  return [...new Set(parts)];
}

function addGageEntry(data = {}) {
  const row = document.createElement("div");
  row.className = "gage-row";
  const partOptions = lineItemPartNumbers()
    .map((pn) => `<option value="${esc(pn)}"></option>`)
    .join("");
  row.innerHTML = `
    <input name="gage_part_number" list="gage-pn-options" placeholder="P/N (optional)" value="${esc(data.part_number || "")}" title="Optional — match a line item part number">
    <input name="gage_value" placeholder="Gage" value="${esc(data.gage || "")}">
    <button type="button" class="btn danger remove-gage">×</button>
  `;
  row.querySelector(".remove-gage").addEventListener("click", () => row.remove());
  gageListContainer.appendChild(row);
  let datalist = document.getElementById("gage-pn-options");
  if (!datalist) {
    datalist = document.createElement("datalist");
    datalist.id = "gage-pn-options";
    document.body.appendChild(datalist);
  }
  datalist.innerHTML = partOptions;
}

function collectPayload() {
  const form = document.getElementById("quote-form");
  const fd = new FormData(form);
  const lineItems = [];
  tbody.querySelectorAll("tr.line-item-row").forEach((tr) => {
    const get = (name) => { const el = tr.querySelector(`[name="${name}"]`); return el ? el.value : ""; };
    const qtyOptions = parseQtyOptions(get("qty_options"));
    const factoryPriceStr = get("factory_unit_price_vnd");
    const factoryPrices = parseFactoryPrices(factoryPriceStr);
    const item = {
      part_number: get("part_number"), cast_dwg: get("cast_dwg"), mach_dwg: get("mach_dwg"),
      description: get("description"), material: get("material"),
      factory_unit_price_vnd: factoryPriceStr,
      factory_weight_kg: get("factory_weight_kg"),
      factory_mold_fee_vnd: get("factory_mold_fee_vnd"), other_finish: get("other_finish"),
      pressure_testing: get("pressure_testing"),
    };
    const um = get("unit_price_markup_pct");
    const mm = get("mold_fee_markup_pct");
    if (um) item.unit_price_markup_pct = um;
    if (mm) item.mold_fee_markup_pct = mm;
    const sampleCost = parseFloat(get("sample_factory_cost_vnd"));
    if (!Number.isNaN(sampleCost) && sampleCost > 0) item.sample_factory_cost_vnd = sampleCost;
    if (qtyOptions.length) {
      item.qty_options = qtyOptions;
      item.qty = qtyOptions[0];
      if (factoryPrices.length) item.factory_unit_price_vnd_options = factoryPrices;
      lineItems.push(item);
    }
  });

  const custom_fields = {};
  customContainer.querySelectorAll(".custom-row").forEach((row) => {
    const label = row.querySelector(".custom-label").value.trim();
    const value = row.querySelector(".custom-value").value.trim();
    if (label) custom_fields[label] = value;
  });

  const gage_list = [];
  gageListContainer.querySelectorAll(".gage-row").forEach((row) => {
    const part_number = row.querySelector('[name="gage_part_number"]')?.value.trim() || "";
    const gage = row.querySelector('[name="gage_value"]')?.value.trim() || "";
    if (gage || part_number) gage_list.push({ part_number, gage });
  });

  const payload = {
    inquiry_no: fd.get("inquiry_no"),
    quotation_date: fd.get("quotation_date"),
    factory_name: fd.get("factory_name"),
    show_factory_name_on_pdf: fd.get("show_factory_name_on_pdf") === "on",
    artmark: fd.get("artmark") === "on",
    exchange_rate_vnd: fd.get("exchange_rate_vnd"),
    export_inspection_fee_usd: fd.get("export_inspection_fee_usd"),
    unit_price_markup_pct: fd.get("unit_price_markup_pct"),
    mold_fee_markup_pct: fd.get("mold_fee_markup_pct"),
    sample_markup_pct: fd.get("sample_markup_pct"),
    sample_lead_time_days: (() => {
      const v = fd.get("sample_lead_time_days");
      return v === null || String(v).trim() === "" ? null : v;
    })(),
    production_lead_time_days: fd.get("production_lead_time_days"),
    validity_days: fd.get("validity_days"),
    other_notes: fd.get("other_notes"),
    custom_fields,
    gage_list,
    line_item_column_labels: collectColumnLabels(),
    line_items: lineItems,
  };
  if (currentQuoteId) payload.quote_id = currentQuoteId;
  return payload;
}

function showSaveStatus(msg, ok = true) {
  saveStatus.textContent = msg;
  saveStatus.className = `save-status ${ok ? "saved" : "error"}`;
  saveStatus.classList.remove("hidden");
  setTimeout(() => saveStatus.classList.add("hidden"), 3000);
}

function setQuoteId(id) {
  currentQuoteId = id || "";
  quoteIdInput.value = id || "";
  const deleteBtn = document.getElementById("delete-btn");
  if (deleteBtn) deleteBtn.classList.toggle("hidden", !id);
  if (id && !window.location.pathname.includes(id)) {
    history.replaceState(null, "", `/quote/${id}`);
  }
}

async function deleteQuote() {
  if (!currentQuoteId) return;
  const inquiry = document.querySelector('[name="inquiry_no"]')?.value || "this quote";
  if (!confirm(`Delete quote "${inquiry}"? This cannot be undone.`)) return;
  const res = await fetch(`/api/quotes/${currentQuoteId}`, { method: "DELETE" });
  if (!res.ok) {
    alert("Could not delete quote.");
    return;
  }
  window.location.href = "/";
}

async function saveQuote() {
  const payload = collectPayload();
  const res = await fetch("/api/quotes/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payload, quote_id: currentQuoteId || null }),
  });
  const data = await res.json();
  if (data.quote_id) {
    setQuoteId(data.quote_id);
    showSaveStatus("Quote saved");
  } else {
    showSaveStatus("Save failed", false);
  }
}

function populateForm(payload) {
  const form = document.getElementById("quote-form");
  const set = (name, val) => { const el = form.querySelector(`[name="${name}"]`); if (el) el.value = val ?? ""; };
  set("inquiry_no", payload.inquiry_no);
  set("quotation_date", payload.quotation_date);
  set("factory_name", payload.factory_name);
  form.querySelector("#show_factory_name_on_pdf").checked = !!payload.show_factory_name_on_pdf;
  form.querySelector("#artmark").checked = !!payload.artmark;
  set("exchange_rate_vnd", payload.exchange_rate_vnd);
  set("export_inspection_fee_usd", payload.export_inspection_fee_usd);
  set("unit_price_markup_pct", payload.unit_price_markup_pct);
  set("mold_fee_markup_pct", payload.mold_fee_markup_pct);
  set("sample_markup_pct", payload.sample_markup_pct ?? 25);
  set("sample_lead_time_days", payload.sample_lead_time_days ?? "");
  set("production_lead_time_days", payload.production_lead_time_days);
  set("validity_days", payload.validity_days);
  set("other_notes", payload.other_notes);

  tbody.innerHTML = "";
  customContainer.innerHTML = "";
  gageListContainer.innerHTML = "";
  buildColumnHeaders(payload.line_item_column_labels || {});
  (payload.line_items || []).forEach(addLineItem);
  if (!payload.line_items?.length) addLineItem();
  Object.entries(payload.custom_fields || {}).forEach(([k, v]) => addCustomField(k, v));
  (payload.gage_list || []).forEach(addGageEntry);
}

async function loadQuote(id) {
  const res = await fetch(`/api/quotes/${id}`);
  if (!res.ok) { alert("Quote not found"); window.location.href = "/"; return; }
  const record = await res.json();
  setQuoteId(record.id);
  populateForm(record.payload);
  showSaveStatus(`Loaded ${record.inquiry_no || "quote"}`);
}

async function preview() {
  const payload = collectPayload();
  const res = await fetch("/api/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, quote_id: currentQuoteId || null }),
  });
  let data;
  try {
    data = await res.json();
  } catch (_) {
    showSaveStatus("Preview failed — invalid response", false);
    return;
  }
  if (!res.ok || !Array.isArray(data.line_items)) {
    showSaveStatus(data.error || "Preview failed", false);
    return;
  }
  if (data.quote_id) setQuoteId(data.quote_id);
  previewPanel.classList.remove("hidden");
  renderPreviewPanel(data);
  showSaveStatus("Saved with preview");
}

function initScenarioSelection(data) {
  selectedScenario = new Map();
  const groups = groupPreviewRows(data.line_items);
  for (const rows of groups.values()) {
    selectedScenario.set(rows[0].item_no, rows[0]);
  }
}

function groupPreviewRows(lineItems) {
  const groups = new Map();
  lineItems.forEach((li, idx) => {
    const row = { ...li, _idx: idx };
    if (!groups.has(row.item_no)) groups.set(row.item_no, []);
    groups.get(row.item_no).push(row);
  });
  return groups;
}

function computeScenarioTotals() {
  if (!previewData) return null;
  const rows = [...selectedScenario.values()];
  if (!rows.length) {
    return {
      factoryOrder: 0,
      revenue: 0,
      exportFee: previewData.total_export_fee_allocated,
      unitProfit: 0,
      moldProfit: 0,
      productionNet: 0,
      netProfit: 0,
      qtyLabel: "No line items",
    };
  }
  return {
    factoryOrder: rows.reduce((s, li) => s + li.factory_unit_price_usd * li.qty, 0),
    revenue: rows.reduce((s, li) => s + li.unit_pricing_fob_usd * li.qty, 0),
    exportFee: previewData.total_export_fee_allocated,
    unitProfit: rows.reduce((s, li) => s + li.unit_price_profit, 0),
    moldProfit: rows.reduce((s, li) => s + li.mold_fee_profit, 0),
    productionNet: rows.reduce((s, li) => s + li.line_net_after_export, 0),
    netProfit: rows.reduce((s, li) => s + li.line_net_after_export, 0),
    qtyLabel: rows
      .map((li) => `${li.part_number || `Part ${li.item_no}`}: ${Number(li.qty).toLocaleString()} pcs`)
      .join(" · "),
  };
}

function updateScenarioSummary() {
  const totals = computeScenarioTotals();
  if (!totals) return;

  const hint = document.getElementById("preview-hint");
  if (hint) {
    hint.textContent = previewData.has_multiple_qty_options
      ? "Click a quantity row for each P/N to compare scenarios. Totals below reflect your selected combination."
      : "Totals for the entered quantities.";
  }

  let scenarioLabel = document.getElementById("preview-scenario-label");
  if (!scenarioLabel) {
    scenarioLabel = document.createElement("div");
    scenarioLabel.id = "preview-scenario-label";
    document.getElementById("preview-summary").before(scenarioLabel);
  }
  scenarioLabel.innerHTML = `<strong>Selected scenario:</strong> ${esc(totals.qtyLabel)}`;

  document.getElementById("preview-summary").innerHTML = `
    <div class="stat">P/N's<strong>${previewData.num_parts}</strong></div>
    <div class="stat">Factory Order (USD)<strong>$${fmt(totals.factoryOrder)}</strong></div>
    <div class="stat">Quoted Revenue (USD)<strong>$${fmt(totals.revenue)}</strong></div>
    <div class="stat">Export / Inspection Fee<strong>$${fmt(totals.exportFee)}</strong></div>
    <div class="stat">Unit Profit<strong>$${fmt(totals.unitProfit)}</strong></div>
    <div class="stat">Mold Profit<strong>$${fmt(totals.moldProfit)}</strong></div>
    <div class="stat">Production Net<strong>$${fmt(totals.productionNet)}</strong></div>
    <div class="stat stat-highlight">
      <span class="stat-highlight-label">Net Profit for Selected Scenario (USD)</span>
      <strong class="stat-highlight-value">$${fmt(totals.netProfit)}</strong>
      <span class="stat-highlight-note">After unit &amp; mold markups, minus export/inspection fees</span>
    </div>
  `;

  document.getElementById("preview-total-net").textContent = `$${fmt(totals.netProfit)}`;
  document.getElementById("preview-total-row").querySelector("td:first-child").innerHTML = `
    <strong>Net Profit (Selected Scenario)</strong>
    <span class="preview-total-note">${esc(totals.qtyLabel)}</span>`;
}

function renderPreviewTable(groups) {
  let rowsHtml = "";
  for (const rows of groups.values()) {
    rows.forEach((li, i) => {
      const selected = selectedScenario.get(li.item_no)?._idx === li._idx;
      rowsHtml += `<tr class="preview-qty-row${selected ? " selected" : ""}" data-item-no="${li.item_no}" data-idx="${li._idx}">`;
      if (i === 0) {
        const span = rows.length;
        rowsHtml += `<td rowspan="${span}" class="preview-group">${li.item_no}</td>`;
        rowsHtml += `<td rowspan="${span}" class="preview-group">${esc(li.part_number)}</td>`;
      }
      rowsHtml += `
        <td class="qty-cell">${Number(li.qty).toLocaleString()}</td>
        <td>$${fmt4(li.factory_unit_price_usd)}</td>
        <td>$${fmt4(li.export_fee_per_unit)}</td>
        <td>$${fmt4(li.unit_pricing_fob_usd)}</td>
        <td>$${fmt(li.tooling_fee_usd)}</td>
        <td>$${fmt(li.unit_price_profit)}</td>
        <td>$${fmt(li.mold_fee_profit)}</td>
        <td>$${fmt(li.line_net_after_export)}</td>
      </tr>`;
    });
  }

  const tbody = document.querySelector("#preview-table tbody");
  tbody.innerHTML = rowsHtml;
  tbody.onclick = (e) => {
    const tr = e.target.closest(".preview-qty-row");
    if (!tr) return;
    const itemNo = Number(tr.dataset.itemNo);
    const idx = Number(tr.dataset.idx);
    const row = previewData.line_items[idx];
    if (!row) return;
    selectedScenario.set(itemNo, { ...row, _idx: idx });
    renderPreviewTable(groupPreviewRows(previewData.line_items));
    updateScenarioSummary();
  };
}

function renderPreviewPanel(data) {
  previewData = data;
  initScenarioSelection(data);
  renderPreviewTable(groupPreviewRows(data.line_items));
  updateScenarioSummary();
}

async function download(fmt) {
  const payload = collectPayload();
  const res = await fetch(`/api/generate/${fmt}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, quote_id: currentQuoteId || null }),
  });
  if (!res.ok) {
    let msg = "Generation failed";
    try {
      const err = await res.json();
      if (err.error) msg = err.error;
    } catch (_) {}
    alert(msg);
    showSaveStatus(msg, false);
    return;
  }
  const savedId = res.headers.get("X-Quote-Id");
  if (savedId) setQuoteId(savedId);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = res.headers.get("Content-Disposition")?.match(/filename="?([^";]+)/)?.[1]
    || `quotation.${fmt === "excel" ? "xlsx" : "pdf"}`;
  a.click();
  URL.revokeObjectURL(url);
  showSaveStatus("Saved & downloaded");
}

function fmt(n) { return Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function fmt4(n) { return Number(n).toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 }); }

document.getElementById("add-row").addEventListener("click", () => addLineItem());
document.getElementById("add-custom").addEventListener("click", () => addCustomField());
document.getElementById("add-gage").addEventListener("click", () => addGageEntry());
document.getElementById("save-btn").addEventListener("click", saveQuote);
document.getElementById("preview-btn").addEventListener("click", preview);
document.getElementById("excel-btn").addEventListener("click", () => download("excel"));
document.getElementById("excel-customer-btn").addEventListener("click", () => download("excel-customer"));
document.getElementById("pdf-btn").addEventListener("click", () => download("pdf"));
document.getElementById("delete-btn").addEventListener("click", deleteQuote);

(async function init() {
  buildColumnHeaders();
  setQuoteId(currentQuoteId);
  if (currentQuoteId) {
    await loadQuote(currentQuoteId);
  } else {
    document.getElementById("quotation_date").value = new Date().toISOString().slice(0, 10);
    addLineItem();
  }
})();

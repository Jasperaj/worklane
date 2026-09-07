// app.js - no frameworks, just fetch() + DOM. Talks to the FastAPI backend
// under /api/*. Credentials are sent per-request and never stored in the browser.
const API = "";

const tabs = document.querySelectorAll(".rail-tab");
const panels = document.querySelectorAll(".panel");
tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    panels.forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.panel).classList.add("active");
  });
});

function setStatus(id, text, kind) {
  const el = document.getElementById(id);
  el.textContent = text || "";
  el.className = "status" + (kind ? " " + kind : "");
}

function linesToList(value) {
  return value.split("\n").map((s) => s.trim()).filter(Boolean);
}

async function postJSON(path, body) {
  const res = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { const err = await res.json(); detail = err.detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

async function postForFile(path, body, fallbackName) {
  const res = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { const err = await res.json(); detail = err.detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match ? match[1] : fallbackName;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function renderTable(rows) {
  if (!rows || rows.length === 0) return '<div class="result-empty">No rows returned.</div>';
  const cols = Object.keys(rows[0]);
  let html = '<div class="result-table-wrap"><table><thead><tr>';
  cols.forEach((c) => (html += `<th>${c}</th>`));
  html += "</tr></thead><tbody>";
  rows.forEach((row) => {
    html += "<tr>";
    cols.forEach((c) => {
      const v = row[c];
      html += `<td>${v === null || v === undefined ? "" : String(v)}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table></div>";
  return html;
}

function formToObject(form) {
  const data = {};
  new FormData(form).forEach((value, key) => (data[key] = value));
  return data;
}

const form1 = document.getElementById("form1");
const btn1Pdfs = document.getElementById("btn1-pdfs");
let lastTdsQuery = null;
form1.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = formToObject(form1);
  setStatus("status1", "Logging in and fetching TDS list...");
  document.getElementById("result1").innerHTML = "";
  btn1Pdfs.disabled = true;
  try {
    const { rows } = await postJSON("/api/tds-list", data);
    setStatus("status1", `Found ${rows.length} TDS transaction(s).`, "success");
    document.getElementById("result1").innerHTML = renderTable(rows);
    lastTdsQuery = data;
    btn1Pdfs.disabled = rows.length === 0;
  } catch (err) {
    setStatus("status1", err.message, "error");
  }
});
btn1Pdfs.addEventListener("click", async () => {
  if (!lastTdsQuery) return;
  setStatus("status1", "Building ZIP of all ETDS PDFs...");
  try {
    await postForFile("/api/tds-list/pdfs", lastTdsQuery, "etds_returns.zip");
    setStatus("status1", "ZIP downloaded.", "success");
  } catch (err) {
    setStatus("status1", err.message, "error");
  }
});

const form2 = document.getElementById("form2");
form2.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = formToObject(form2);
  const pan_list = linesToList(data.pan_list);
  if (pan_list.length === 0) { setStatus("status2", "Enter at least one PAN to check.", "error"); return; }
  setStatus("status2", "Logging in and checking filing status...");
  document.getElementById("result2").innerHTML = "";
  try {
    const { rows } = await postJSON("/api/vat-check", {
      pan: data.pan, username: data.username, password: data.password,
      tax_year: data.tax_year, period: data.period, pan_list,
    });
    document.getElementById("result2").innerHTML = renderTable(rows);
    setStatus("status2", "Done.", "success");
  } catch (err) {
    setStatus("status2", err.message, "error");
  }
});

const form3 = document.getElementById("form3");
form3.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = formToObject(form3);
  if (!confirm(`This submits a live extension application for PAN ${data.pan}. Continue?`)) return;
  setStatus("status3", "Submitting...");
  document.getElementById("result3").innerHTML = "";
  try {
    const { result } = await postJSON("/api/date-extension/apply", data);
    document.getElementById("result3").innerHTML = renderTable([result]);
    setStatus("status3", "Submitted.", "success");
  } catch (err) {
    setStatus("status3", err.message, "error");
  }
});

const form4 = document.getElementById("form4");
form4.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = formToObject(form4);
  setStatus("status4", "Logging in and downloading PDF...");
  try {
    await postForFile("/api/date-extension/pdf", data, `${data.pan}_date_extension.pdf`);
    setStatus("status4", "PDF downloaded.", "success");
  } catch (err) {
    setStatus("status4", err.message, "error");
  }
});

const form5 = document.getElementById("form5");
form5.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = formToObject(form5);
  setStatus("status5", "Looking up vouchers...");
  document.getElementById("result5").innerHTML = "";
  try {
    const { rows } = await postJSON("/api/etax-voucher", data);
    document.getElementById("result5").innerHTML = renderTable(rows);
    setStatus("status5", `Found ${rows.length} voucher(s).`, "success");
  } catch (err) {
    setStatus("status5", err.message, "error");
  }
});

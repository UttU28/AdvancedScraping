const fileInput = document.getElementById("fileInput");
const dropzone = document.getElementById("dropzone");
const statusEl = document.getElementById("status");
const tableBody = document.getElementById("tableBody");
const modeToggle = document.getElementById("modeToggle");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const downloadBtn = document.getElementById("downloadBtn");
const progressText = document.getElementById("progressText");
const progressBar = document.getElementById("progressBar");

const VIEW_COLUMNS = ["Full Name", "LinkedIn", "Mails"];
let loadedRows = [];
const emailsByUrl = new Map();
let processingTabId = null;

function setStatus(message) {
  statusEl.textContent = message;
}

function setProgress(done, total) {
  const safeTotal = Math.max(0, Number(total) || 0);
  const safeDone = Math.max(0, Number(done) || 0);
  const pending = Math.max(0, safeTotal - safeDone);
  progressText.textContent = `Done: ${safeDone} | Pending: ${pending} | Total: ${safeTotal}`;
  progressBar.max = safeTotal > 0 ? safeTotal : 1;
  progressBar.value = safeDone;
}

function normalizeKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replaceAll(/[_-]+/g, " ")
    .replaceAll(/\s+/g, " ");
}

function getValueByAliases(row, aliases) {
  const map = new Map();
  Object.keys(row).forEach((key) => {
    map.set(normalizeKey(key), row[key]);
  });

  for (const alias of aliases) {
    const value = map.get(normalizeKey(alias));
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return String(value).trim();
    }
  }
  return "";
}

function extractLinkedIn(row) {
  return getValueByAliases(row, [
    "LinkedIn",
    "LinkedIn URL",
    "LinkedIn Profile",
    "Profile URL",
    "Profile",
    "URL",
  ]);
}

function extractField(row, column) {
  const linkedInUrl = toSafeUrl(extractLinkedIn(row));
  switch (column) {
    case "Full Name":
      return getValueByAliases(row, ["Full Name", "Name", "Person Name"]);
    case "LinkedIn":
      return extractLinkedIn(row);
    case "Mails":
      return emailsByUrl.get(linkedInUrl) || "";
    default:
      return "";
  }
}

function toSafeUrl(value) {
  if (!value) {
    return "";
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  return `https://${value}`;
}

function toDisplayLinkedIn(value) {
  const fullUrl = toSafeUrl(value);
  if (!fullUrl) {
    return "";
  }
  const urlParts = /^https?:\/\/([^/]+)(\/.*)?$/i.exec(fullUrl);
  const host = String(urlParts?.[1] || "")
    .toLowerCase()
    .trim();
  const path = String(urlParts?.[2] || "/")
    .replace(/^\/+/, "")
    .replace(/\/+$/, "");
  const linkedInHost = /^([a-z0-9-]+)\.linkedin\.com$/i.exec(host);
  const subdomain = linkedInHost?.[1];

  if (subdomain && subdomain !== "www") {
    return `${subdomain}/${path}`;
  }
  if (host === "linkedin.com" || host === "www.linkedin.com") {
    return path;
  }
  return `${host || "linkedin.com"}/${path}`.replaceAll(/\/+$/g, "");
}

function renderRows(rows) {
  loadedRows = rows;
  tableBody.innerHTML = "";

  if (!rows.length) {
    startBtn.disabled = true;
    downloadBtn.disabled = true;
    setProgress(0, 0);
    setStatus("No rows found in this file.");
    return;
  }

  const fragment = document.createDocumentFragment();
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    VIEW_COLUMNS.forEach((column) => {
      const td = document.createElement("td");
      const value = extractField(row, column);
      if (column === "LinkedIn" && value) {
        const link = document.createElement("a");
        link.href = toSafeUrl(value);
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = toDisplayLinkedIn(value);
        td.appendChild(link);
      } else {
        td.textContent = value;
      }
      tr.appendChild(td);
    });
    fragment.appendChild(tr);
  });

  tableBody.appendChild(fragment);
  startBtn.disabled = !rows.some((row) => extractLinkedIn(row));
  downloadBtn.disabled = false;
  setStatus(`Loaded ${rows.length} row(s). Showing Full Name and LinkedIn.`);
}

function parseCsv(text) {
  const workbook = XLSX.read(text, { type: "string" });
  const firstSheet = workbook.SheetNames[0];
  if (!firstSheet) {
    return [];
  }
  return XLSX.utils.sheet_to_json(workbook.Sheets[firstSheet], { defval: "" });
}

function parseExcel(buffer) {
  const workbook = XLSX.read(buffer, { type: "array" });
  const firstSheet = workbook.SheetNames[0];
  if (!firstSheet) {
    return [];
  }
  return XLSX.utils.sheet_to_json(workbook.Sheets[firstSheet], { defval: "" });
}

function handleFile(file) {
  if (!file) {
    return;
  }

  const lower = file.name.toLowerCase();
  emailsByUrl.clear();
  setStatus(`Reading ${file.name}...`);

  if (lower.endsWith(".csv")) {
    file
      .text()
      .then((text) => {
        const rows = parseCsv(text);
        renderRows(rows);
      })
      .catch((error) => {
        setStatus(`Could not parse CSV: ${error.message}`);
      });
    return;
  }

  if (lower.endsWith(".xlsx") || lower.endsWith(".xls")) {
    file
      .arrayBuffer()
      .then((buffer) => {
        const rows = parseExcel(buffer);
        renderRows(rows);
      })
      .catch((error) => {
        setStatus(`Could not parse Excel: ${error.message}`);
      });
    return;
  }

  setStatus("Unsupported file type. Use .csv, .xlsx or .xls.");
}

function getLinkedInUrlsFromRows(rows) {
  return rows
    .map((row) => toSafeUrl(extractLinkedIn(row)))
    .filter((url) => /^https?:\/\/(www\.)?linkedin\.com\//i.test(url));
}

function queryActiveTab() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      const activeTab = tabs?.[0];
      if (!activeTab?.id) {
        reject(new Error("No active tab found."));
        return;
      }
      resolve(activeTab);
    });
  });
}

function sendStartMessage(payload) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: "START_PROCESSING", payload }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (!response?.ok) {
        reject(new Error(response?.error || "Processing failed."));
        return;
      }
      resolve({ report: response.report || [], stopped: Boolean(response.stopped) });
    });
  });
}

function sendStopMessage(payload) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: "STOP_PROCESSING", payload }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (!response?.ok) {
        reject(new Error("Stop request failed."));
        return;
      }
      resolve(Boolean(response.stopped));
    });
  });
}

function toCsvValue(value) {
  const text = String(value ?? "");
  if (text.includes(",") || text.includes("\"") || text.includes("\n")) {
    return `"${text.replaceAll("\"", "\"\"")}"`;
  }
  return text;
}

function downloadCurrentCsv() {
  if (!loadedRows.length) {
    setStatus("No rows to export.");
    return;
  }

  const header = ["Full Name", "LinkedIn", "Mails"];
  const lines = [header.join(",")];
  loadedRows.forEach((row) => {
    const name = getValueByAliases(row, ["Full Name", "Name", "Person Name"]);
    const linkedIn = extractLinkedIn(row);
    const mailValue = emailsByUrl.get(toSafeUrl(linkedIn)) || "";
    lines.push([name, linkedIn, mailValue].map(toCsvValue).join(","));
  });

  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "linkedin_enriched.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === "PROCESS_PROGRESS" && message.item) {
    const safeUrl = toSafeUrl(message.item.url);
    const emails = Array.isArray(message.item.emails) ? message.item.emails.filter(Boolean) : [];
    emailsByUrl.set(safeUrl, emails.length ? emails.join(", ") : "NaN");
    setProgress(message.done, message.total);
    renderRows(loadedRows);
    return;
  }

  if (message?.type === "PROCESS_STOPPED") {
    setStatus("Processing stopped.");
    startBtn.disabled = !loadedRows.some((row) => extractLinkedIn(row));
    stopBtn.disabled = true;
    processingTabId = null;
  }
});

fileInput.addEventListener("change", (event) => {
  handleFile(event.target.files?.[0]);
  event.target.value = "";
});

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    dropzone.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    dropzone.classList.remove("drag-over");
  });
});

dropzone.addEventListener("drop", (event) => {
  const file = event.dataTransfer?.files?.[0];
  handleFile(file);
});

startBtn.addEventListener("click", async () => {
  const urls = getLinkedInUrlsFromRows(loadedRows);
  if (!urls.length) {
    setStatus("No valid LinkedIn URLs found.");
    return;
  }

  const mode = modeToggle.checked ? "batch" : "single";
  startBtn.disabled = true;
  stopBtn.disabled = false;
  emailsByUrl.clear();
  renderRows(loadedRows);
  setProgress(0, urls.length);
  setStatus(`Starting ${mode} processing...`);

  try {
    const activeTab = await queryActiveTab();
    processingTabId = activeTab.id;
    const response = await sendStartMessage({ tabId: activeTab.id, urls, mode });
    const report = response.report || [];
    setProgress(report.length, urls.length);
    report.forEach((item) => {
      const safeUrl = toSafeUrl(item.url);
      const emails = Array.isArray(item.emails) ? item.emails.filter(Boolean) : [];
      emailsByUrl.set(safeUrl, emails.length ? emails.join(", ") : "NaN");
    });
    renderRows(loadedRows);
    const foundCount = report.filter((item) => (item.emails || []).length > 0).length;
    setStatus(
      response.stopped
        ? `Stopped: found emails on ${foundCount}/${report.length} processed profile(s).`
        : `Done: found emails on ${foundCount}/${report.length} profile(s).`
    );
  } catch (error) {
    setStatus(`Processing error: ${error.message}`);
  } finally {
    startBtn.disabled = false;
    stopBtn.disabled = true;
    processingTabId = null;
  }
});

stopBtn.addEventListener("click", async () => {
  if (!processingTabId) {
    setStatus("No active processing to stop.");
    return;
  }
  try {
    const stopped = await sendStopMessage({ tabId: processingTabId });
    setStatus(stopped ? "Stopping processing..." : "No active processing found.");
  } catch (error) {
    setStatus(`Stop error: ${error.message}`);
  }
});

downloadBtn.addEventListener("click", () => {
  downloadCurrentCsv();
});

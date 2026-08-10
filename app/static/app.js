const state = {
  config: null,
  picker: null,
  currentJob: null,
  toastTimer: null,
  lastJobs: [],
};

function t(key, vars) {
  return window.MWB_I18N ? window.MWB_I18N.t(key, vars) : key;
}

function tx(msg) {
  return window.MWB_I18N ? window.MWB_I18N.translateMessage(msg) : String(msg ?? "");
}

function kindLabel(kind) {
  return window.MWB_I18N ? window.MWB_I18N.kindLabel(kind) : kind;
}

function statusLabel(status) {
  return window.MWB_I18N ? window.MWB_I18N.statusLabel(status) : status;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    let message = data.detail || `${t("requestFailed")} (${response.status})`;
    if (Array.isArray(message)) message = message.map(item => item.msg).join("; ");
    throw new Error(tx(message));
  }
  return data;
}

function toast(message, error = false) {
  const node = document.getElementById("toast");
  node.textContent = tx(message);
  node.className = `toast show${error ? " error" : ""}`;
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => node.className = "toast", 3200);
}

function buildCmePaths() {
  document.querySelectorAll(".cme-paths").forEach(container => {
    const prefix = container.dataset.prefix;
    const defaultFolder = { cut: "_segments", merge: "_merged", extract: "_extract" }[prefix];
    container.innerHTML = `
      <label><span data-i18n="inputRoot">${t("inputRoot")}</span><select id="${prefix}InputRoot" class="root-select"></select></label>
      <label class="path-field"><span data-i18n="inputDir">${t("inputDir")}</span><span><input id="${prefix}InputPath" data-i18n-placeholder="inputPathPh" placeholder="${escapeHtml(t("inputPathPh"))}"><button type="button" class="browse" data-picker="${prefix}InputPath" data-root="${prefix}InputRoot" data-i18n="choose">${t("choose")}</button></span></label>
      <label><span data-i18n="outputRoot">${t("outputRoot")}</span><select id="${prefix}OutputRoot" class="root-select"></select></label>
      <label class="path-field"><span data-i18n="outputDirLabel">${t("outputDirLabel")}</span><span><input id="${prefix}OutputPath" data-default-folder="${defaultFolder}" placeholder="${escapeHtml(t("outputPathPhPrefix") + defaultFolder)}"><button type="button" class="browse" data-picker="${prefix}OutputPath" data-root="${prefix}OutputRoot" data-i18n="choose">${t("choose")}</button></span></label>`;
  });
}

function fillRootSelects() {
  if (!state.config) return;
  const options = state.config.roots.map(root =>
    `<option value="${escapeHtml(root.key)}" ${root.available ? "" : "disabled"}>${escapeHtml(root.label)}${root.available ? "" : t("unavailable")}</option>`
  ).join("");
  document.querySelectorAll(".root-select").forEach(select => {
    const prev = select.value;
    select.innerHTML = options;
    if (prev && [...select.options].some(o => o.value === prev && !o.disabled)) select.value = prev;
  });
}

function pathJoin(parent, child) {
  return [parent.replace(/^\/+|\/+$/g, ""), child.replace(/^\/+|\/+$/g, "")].filter(Boolean).join("/");
}

function autoOutput(prefix) {
  const input = document.getElementById(`${prefix}InputPath`);
  const output = document.getElementById(`${prefix}OutputPath`);
  if (!input || !output || output.dataset.edited === "true") return;
  const folder = output.dataset.defaultFolder || "converted";
  output.value = pathJoin(input.value, folder);
  const inputRoot = document.getElementById(`${prefix}InputRoot`);
  const outputRoot = document.getElementById(`${prefix}OutputRoot`);
  if (inputRoot && outputRoot) outputRoot.value = inputRoot.value;
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach(button => button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(tab => tab.classList.toggle("active", tab === button));
    document.querySelectorAll(".tool-panel").forEach(panel => panel.classList.toggle("active", panel.dataset.kind === button.dataset.tab));
  }));
}

function setupDefaults() {
  ["convert", "cut", "merge", "extract"].forEach(prefix => {
    const input = document.getElementById(`${prefix}InputPath`);
    const output = document.getElementById(`${prefix}OutputPath`);
    input?.addEventListener("change", () => autoOutput(prefix));
    input?.addEventListener("blur", () => autoOutput(prefix));
    document.getElementById(`${prefix}InputRoot`)?.addEventListener("change", () => autoOutput(prefix));
    output?.addEventListener("input", event => event.target.dataset.edited = event.target.value ? "true" : "false");
  });
  const output = document.getElementById("convertOutputPath");
  if (output) output.dataset.defaultFolder = "converted";
}

function commonPayload(prefix) {
  return {
    input_root: document.getElementById(`${prefix}InputRoot`).value,
    input_path: document.getElementById(`${prefix}InputPath`).value.trim(),
    output_root: document.getElementById(`${prefix}OutputRoot`).value,
    output_path: document.getElementById(`${prefix}OutputPath`).value.trim(),
  };
}

function contentPayload(prefix) {
  const container = document.querySelector(`.content-options[data-prefix="${prefix}"]`);
  return Object.fromEntries([...container.querySelectorAll("[data-content]")].map(input => [input.dataset.content, input.checked]));
}

function convertPayload() {
  return {
    ...commonPayload("convert"),
    mode: document.getElementById("convertMode").value,
    recursive: document.getElementById("recursive").checked,
    audio_codec: document.getElementById("audioCodec").value,
    audio_bitrate: document.getElementById("audioBitrate").value,
    sample_rate: Number(document.getElementById("sampleRate").value),
    channels: Number(document.getElementById("channels").value),
    video_codec: document.getElementById("videoCodec").value,
    crf: Number(document.getElementById("crf").value),
    resolution: document.getElementById("resolution").value,
    preset: document.getElementById("preset").value,
    video_format: document.getElementById("videoFormat").value,
    workers: Number(document.getElementById("convertWorkers").value),
    overwrite: document.getElementById("convertOverwrite").checked,
  };
}

function cutPayload() {
  return {
    ...commonPayload("cut"), content: contentPayload("cut"),
    segment_length: Number(document.getElementById("segmentLength").value),
    use_sg_align: document.getElementById("sgAlign").checked,
    workers: Number(document.getElementById("cutWorkers").value),
    overwrite: document.getElementById("cutOverwrite").checked,
  };
}

function mergePayload() {
  return {
    ...commonPayload("merge"), content: contentPayload("merge"),
    prefixes: document.getElementById("mergePrefixes").value.split(/\r?\n/).map(v => v.trim()).filter(Boolean),
    strict_triplets: document.getElementById("strictTriplets").checked,
    workers: Number(document.getElementById("mergeWorkers").value),
    overwrite: document.getElementById("mergeOverwrite").checked,
  };
}

function parseRanges(text) {
  return text.split(/\r?\n/).map(line => line.trim()).filter(Boolean).map(line => {
    const match = line.match(/^(\d+(?:\.\d+)?)\s*[-—–,]\s*(\d+(?:\.\d+)?)$/);
    if (!match) throw new Error(t("invalidRange", { line }));
    return { start: Number(match[1]), end: Number(match[2]) };
  });
}

function extractPayload() {
  return {
    ...commonPayload("extract"), content: contentPayload("extract"),
    base_name: document.getElementById("extractBase").value.trim(),
    ranges: parseRanges(document.getElementById("extractRanges").value),
    workers: Number(document.getElementById("extractWorkers").value),
    overwrite: document.getElementById("extractOverwrite").checked,
  };
}

async function submitJob(kind, payload) {
  if (!payload.output_path) throw new Error(t("setOutput"));
  const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({ kind, payload }) });
  toast(t("jobQueued", { id: job.id }));
  await loadJobs();
  document.querySelector(".jobs").scrollIntoView({ behavior: "smooth", block: "start" });
}

function setupForms() {
  const builders = { convert: convertPayload, cut: cutPayload, merge: mergePayload, extract: extractPayload };
  Object.entries(builders).forEach(([kind, builder]) => {
    document.getElementById(`${kind}Form`).addEventListener("submit", async event => {
      event.preventDefault();
      const button = event.submitter;
      try {
        button.disabled = true;
        await submitJob(kind, builder());
      } catch (error) {
        toast(error.message, true);
      } finally {
        button.disabled = false;
      }
    });
  });
}

function setupPresets() {
  document.querySelectorAll("[data-preset]").forEach(button => button.addEventListener("click", () => {
    const preset = button.dataset.preset;
    if (preset === "corpus") {
      document.getElementById("convertMode").value = "video_to_audio";
      document.getElementById("audioCodec").value = "pcm_s16le";
      document.getElementById("sampleRate").value = "16000";
      document.getElementById("channels").value = "1";
    } else if (preset === "mp3") {
      document.getElementById("convertMode").value = "audio_to_audio";
      document.getElementById("audioCodec").value = "libmp3lame";
      document.getElementById("audioBitrate").value = "192k";
      document.getElementById("sampleRate").value = "44100";
      document.getElementById("channels").value = "2";
    } else if (preset === "compress") {
      document.getElementById("convertMode").value = "compress";
      document.getElementById("videoCodec").value = "libx264";
      document.getElementById("crf").value = "28";
    } else if (preset === "qsv") {
      document.getElementById("convertMode").value = "video_to_video";
      document.getElementById("videoCodec").value = "h264_qsv";
      document.getElementById("crf").value = "23";
      document.getElementById("convertWorkers").value = "1";
    }
    toast(t("applied", { name: button.textContent.trim() }));
  }));
}

async function scanForm(button) {
  const form = button.closest("form");
  const prefix = form.dataset.kind;
  const common = commonPayload(prefix);
  const requestedMode = button.dataset.scanMode === "convert" ? document.getElementById("convertMode").value : "cme";
  const resultNode = document.getElementById(`${prefix}Scan`);
  resultNode.textContent = t("scanning");
  try {
    const result = await api("/api/scan", {
      method: "POST",
      body: JSON.stringify({ root: common.input_root, path: common.input_path, mode: requestedMode, recursive: document.getElementById("recursive")?.checked ?? false }),
    });
    if (requestedMode === "cme") {
      resultNode.textContent = t("foundGroups", {
        groups: result.groups,
        segments: result.segments,
        prefixes: result.prefixes.length,
      });
      if (prefix === "merge" && !document.getElementById("mergePrefixes").value.trim()) document.getElementById("mergePrefixes").value = result.prefixes.join("\n");
      if (prefix === "extract" && !document.getElementById("extractBase").value.trim() && result.items[0]) document.getElementById("extractBase").value = result.items[0].base;
    } else {
      resultNode.textContent = t("foundConvert", { count: result.count }) + (result.truncated ? t("preview500") : "");
    }
  } catch (error) {
    resultNode.textContent = "";
    toast(error.message, true);
  }
}

function setupScans() {
  document.querySelectorAll(".scan-button").forEach(button => button.addEventListener("click", () => scanForm(button)));
}

async function loadPicker(path = "") {
  const picker = state.picker;
  const query = new URLSearchParams({ root: picker.rootSelect.value, path });
  const data = await api(`/api/browse?${query}`);
  picker.path = data.path;
  picker.selectedFile = null;
  document.getElementById("pickerPath").textContent = `${picker.rootSelect.selectedOptions[0]?.textContent || picker.rootSelect.value}:/${data.path}`;
  document.getElementById("pickerSelection").textContent = "";
  document.getElementById("pickerUp").disabled = data.path === "";
  const items = document.getElementById("pickerItems");
  items.innerHTML = data.items.length ? "" : `<p class="empty">${escapeHtml(t("emptyDir"))}</p>`;
  data.items.forEach(item => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "picker-item";
    const icon = item.type === "directory" ? "📁" : "📄";
    const size = item.type === "directory" ? t("directory") : formatSize(item.size);
    button.innerHTML = `<span>${icon}</span><span>${escapeHtml(item.name)}</span><small>${size}</small>`;
    if (item.type === "directory") {
      button.addEventListener("click", () => loadPicker(item.path).catch(error => toast(error.message, true)));
    } else if (picker.allowFiles) {
      button.addEventListener("click", () => {
        items.querySelectorAll(".selected").forEach(node => node.classList.remove("selected"));
        button.classList.add("selected");
        picker.selectedFile = item.path;
        document.getElementById("pickerSelection").textContent = item.name;
      });
      button.addEventListener("dblclick", () => choosePicker(item.path));
    } else {
      button.disabled = true;
      button.style.opacity = ".45";
    }
    items.appendChild(button);
  });
}

function choosePicker(value = null) {
  const picker = state.picker;
  picker.input.value = value ?? picker.selectedFile ?? picker.path;
  picker.input.dataset.edited = picker.output ? "true" : picker.input.dataset.edited;
  document.getElementById("pickerDialog").close();
  if (!picker.output) autoOutput(picker.prefix);
  picker.input.dispatchEvent(new Event("change"));
}

function setupPicker() {
  const dialog = document.getElementById("pickerDialog");
  document.addEventListener("click", async event => {
    const button = event.target.closest("[data-picker]");
    if (!button) return;
    const input = document.getElementById(button.dataset.picker);
    const prefix = button.dataset.picker.match(/^(convert|cut|merge|extract)/)?.[1];
    const output = button.dataset.picker.includes("Output");
    state.picker = {
      input, prefix, output,
      rootSelect: document.getElementById(button.dataset.root),
      allowFiles: button.dataset.files === "true",
      path: "", selectedFile: null,
    };
    dialog.showModal();
    let start = input.value.trim();
    try {
      await loadPicker(start);
    } catch (_) {
      const parent = start.includes("/") ? start.split("/").slice(0, -1).join("/") : "";
      try { await loadPicker(parent); } catch (error) { dialog.close(); toast(error.message, true); }
    }
  });
  document.querySelector("[data-close-picker]").addEventListener("click", () => dialog.close());
  document.getElementById("pickerChoose").addEventListener("click", () => choosePicker());
  document.getElementById("pickerUp").addEventListener("click", () => {
    const parts = state.picker.path.split("/").filter(Boolean); parts.pop();
    loadPicker(parts.join("/")).catch(error => toast(error.message, true));
  });
}

function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return "";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes, unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit++; }
  return `${value.toFixed(unit ? 1 : 0)} ${units[unit]}`;
}

function formatTime(value) {
  if (!value) return "–";
  const locale = (window.MWB_I18N && window.MWB_I18N.lang === "en") ? "en-US" : "zh-CN";
  return new Date(value).toLocaleString(locale, { hour12: false });
}

function renderJobs(jobs) {
  const container = document.getElementById("jobList");
  state.lastJobs = jobs || [];
  if (!jobs.length) {
    container.innerHTML = `<p class="empty">${escapeHtml(t("noJobs"))}</p>`;
    return;
  }
  container.innerHTML = jobs.map(job => {
    const progress = Math.round((job.progress || 0) * 100);
    const canCancel = ["queued", "running", "cancelling"].includes(job.status);
    const canDelete = ["succeeded", "failed", "cancelled"].includes(job.status);
    const output = `${job.payload.output_root}:/${job.payload.output_path}`;
    return `<article class="job-row">
      <div><div class="job-kind">${escapeHtml(kindLabel(job.kind))}</div><span class="state ${job.status}">${escapeHtml(statusLabel(job.status))}</span></div>
      <div class="job-meta"><strong>${escapeHtml(tx(job.message || t("waiting")))}</strong><small>${escapeHtml(output)} · ${formatTime(job.created_at)}</small></div>
      <div class="job-progress"><div class="progress-track"><div class="progress-bar" style="width:${progress}%"></div></div><small>${progress}% · ${job.id}</small></div>
      <div class="job-actions"><button data-action="detail" data-id="${job.id}">${escapeHtml(t("detail"))}</button>${canCancel ? `<button data-action="cancel" data-id="${job.id}">${escapeHtml(t("stop"))}</button>` : ""}${canDelete ? `<button data-action="delete" data-id="${job.id}">${escapeHtml(t("delete"))}</button>` : ""}</div>
    </article>`;
  }).join("");
}

async function loadJobs() {
  try {
    const jobs = await api("/api/jobs?limit=100");
    renderJobs(jobs);
    if (state.currentJob && document.getElementById("jobDialog").open) showJob(state.currentJob, false);
  } catch (error) {
    document.getElementById("jobList").innerHTML = `<p class="empty">${escapeHtml(error.message)}</p>`;
  }
}

async function showJob(id, open = true) {
  const job = await api(`/api/jobs/${id}`);
  state.currentJob = id;
  document.getElementById("jobDialogTitle").textContent = `${kindLabel(job.kind)} · ${id}`;
  const files = job.result?.files || [];
  const results = files.length
    ? `<h3>${escapeHtml(t("resultFiles", { n: files.length }))}</h3><div class="result-list">${files.map((file, index) => `<a class="result-link" href="/api/jobs/${id}/result/${index}" target="_blank"><span>↗ ${escapeHtml(file.root)}:/${escapeHtml(file.path)}</span></a>`).join("")}</div>`
    : "";
  document.getElementById("jobDetail").innerHTML = `
    <dl class="detail-grid">
      <dt>${escapeHtml(t("status"))}</dt><dd><span class="state ${job.status}">${escapeHtml(statusLabel(job.status))}</span></dd>
      <dt>${escapeHtml(t("progress"))}</dt><dd>${Math.round(job.progress * 100)}% · ${escapeHtml(tx(job.message))}</dd>
      <dt>${escapeHtml(t("input"))}</dt><dd>${escapeHtml(job.payload.input_root)}:/${escapeHtml(job.payload.input_path)}</dd>
      <dt>${escapeHtml(t("output"))}</dt><dd>${escapeHtml(job.payload.output_root)}:/${escapeHtml(job.payload.output_path)}</dd>
      <dt>${escapeHtml(t("createdAt"))}</dt><dd>${formatTime(job.created_at)}</dd>
      <dt>${escapeHtml(t("finishedAt"))}</dt><dd>${formatTime(job.finished_at)}</dd>
    </dl>
    ${job.result?.summary ? `<p>${escapeHtml(tx(job.result.summary))}</p>` : ""}${results}
    <h3>${escapeHtml(t("runLog"))}</h3><pre class="log-view">${escapeHtml(job.logs || t("noLog"))}</pre>`;
  const log = document.querySelector(".log-view"); if (log) log.scrollTop = log.scrollHeight;
  if (open) document.getElementById("jobDialog").showModal();
}

function setupJobs() {
  document.getElementById("refreshJobs").addEventListener("click", loadJobs);
  document.getElementById("jobList").addEventListener("click", async event => {
    const button = event.target.closest("[data-action]"); if (!button) return;
    try {
      if (button.dataset.action === "detail") await showJob(button.dataset.id);
      if (button.dataset.action === "cancel") {
        await api(`/api/jobs/${button.dataset.id}/cancel`, { method: "POST" });
        toast(t("cancelSent"));
        await loadJobs();
      }
      if (button.dataset.action === "delete" && confirm(t("confirmDelete"))) {
        await api(`/api/jobs/${button.dataset.id}`, { method: "DELETE" });
        await loadJobs();
      }
    } catch (error) { toast(error.message, true); }
  });
  document.querySelector("[data-close-job]").addEventListener("click", () => {
    document.getElementById("jobDialog").close();
    state.currentJob = null;
  });
}

async function refreshHealth() {
  try {
    const health = await api("/health");
    const worker = document.getElementById("workerBadge");
    worker.textContent = health.worker_alive ? t("workerOk") : t("workerDown");
    worker.className = `badge ${health.worker_alive ? "good" : "bad"}`;
  } catch (_) {
    const worker = document.getElementById("workerBadge");
    worker.textContent = t("serviceError");
    worker.className = "badge bad";
  }
}

function refreshGpuBadge() {
  if (!state.config) return;
  const gpu = document.getElementById("gpuBadge");
  gpu.textContent = state.config.capabilities.intel_gpu ? t("gpuOk") : t("gpuNo");
  gpu.className = `badge ${state.config.capabilities.intel_gpu ? "good" : "muted"}`;
}

function onLangChange() {
  // rebuild dynamic path grids placeholders / labels, keep form values
  const saved = {};
  ["convert", "cut", "merge", "extract"].forEach(prefix => {
    ["InputRoot", "InputPath", "OutputRoot", "OutputPath"].forEach(suffix => {
      const el = document.getElementById(prefix + suffix);
      if (el) saved[prefix + suffix] = { value: el.value, edited: el.dataset.edited };
    });
  });
  buildCmePaths();
  setupDefaults();
  fillRootSelects();
  Object.entries(saved).forEach(([id, meta]) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = meta.value || "";
    if (meta.edited) el.dataset.edited = meta.edited;
  });
  // CME path placeholders for default folders
  document.querySelectorAll("[data-default-folder]").forEach(input => {
    if (!input.value) {
      input.placeholder = t("outputPathPhPrefix") + (input.dataset.defaultFolder || "");
    }
  });
  if (window.MWB_I18N) window.MWB_I18N.applyStatic();
  refreshGpuBadge();
  refreshHealth();
  renderJobs(state.lastJobs || []);
  // clear scan results (language-dependent)
  ["convert", "cut", "merge", "extract"].forEach(prefix => {
    const n = document.getElementById(`${prefix}Scan`);
    if (n) n.textContent = "";
  });
}

async function initialize() {
  buildCmePaths();
  setupTabs(); setupDefaults(); setupForms(); setupPresets(); setupScans(); setupPicker(); setupJobs();
  if (window.MWB_I18N) {
    window.MWB_I18N.init(onLangChange);
  }
  try {
    state.config = await api("/api/config");
    fillRootSelects();
    document.getElementById("versionBadge").textContent = `v${state.config.version}`;
    refreshGpuBadge();
    if (!state.config.capabilities.ffmpeg) toast(t("noFfmpeg"), true);
  } catch (error) { toast(error.message, true); }
  await Promise.all([loadJobs(), refreshHealth()]);
  setInterval(loadJobs, 2500);
  setInterval(refreshHealth, 10000);
}

initialize();

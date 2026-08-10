/**
 * Media Workbench UI i18n (zh / en).
 * Language: ?lang= · cookie mwb_lang · localStorage · Accept-Language-like default zh.
 */
(function (global) {
  const COOKIE = "mwb_lang";
  const STORAGE = "mwb_lang";
  const SUPPORTED = ["zh", "en"];

  const M = {
    zh: {
      eyebrow: "NAS MEDIA WORKBENCH",
      eyebrowLocal: "LOCAL MEDIA WORKBENCH",
      appTitle: "音视频与 TextGrid 处理工作台",
      appTitleLocal: "音视频与 TextGrid 处理工作台（本地版）",
      subtitle: "转换、同步切分、片段合并和区间抽取在 NAS 后台持续执行",
      subtitleLocal: "转换、同步切分、片段合并和区间抽取在本机后台持续执行",
      pathEyebrow: "NAS PATH",
      pathEyebrowLocal: "LOCAL PATH",
      workerChecking: "worker 检查中",
      workerOk: "worker 正常",
      workerDown: "worker 未就绪",
      serviceError: "服务异常",
      gpuChecking: "硬件加速检查中",
      gpuOk: "Intel QSV 可用",
      gpuNo: "Intel QSV 不可用",
      tabConvert: "格式转换",
      tabCut: "同步切分",
      tabMerge: "片段合并",
      tabExtract: "区间抽取",
      convertTitle: "格式转换",
      convertDesc: "支持单个文件或文件夹递归批量转换，并保留子目录结构。",
      scanFiles: "扫描文件",
      inputRoot: "输入位置",
      inputFileOrDir: "输入文件或目录",
      outputRoot: "输出位置",
      outputDir: "输出目录",
      choose: "选择",
      convertMode: "转换模式",
      modeV2A: "视频 → 音频",
      modeA2A: "音频 → 音频",
      modeV2V: "视频 → 视频",
      modeCompress: "视频压缩",
      audioCodec: "音频编码",
      sampleRate: "采样率",
      channels: "声道",
      mono: "单声道",
      stereo: "双声道",
      audioBitrate: "音频码率",
      videoCodec: "视频编码",
      qualityCrf: "质量 CRF / Q",
      resolution: "分辨率",
      keepResolution: "保持原分辨率",
      encodeSpeed: "编码速度",
      videoContainer: "视频容器",
      parallelFiles: "并行文件数",
      recursive: "递归扫描子目录",
      overwrite: "覆盖已有结果",
      quickPresets: "快捷预设",
      presetCorpus: "语料 WAV 16k 单声道",
      presetMp3: "MP3 192k",
      presetCompress: "视频压缩 CRF28",
      presetQsv: "Intel 快速转码",
      submitConvert: "提交转换任务",
      cutTitle: "同步切分",
      cutDesc: "按固定时长或最近的 SG 层边界同步切分 MP4、WAV 和 TextGrid。",
      scanGroups: "扫描文件组",
      segmentLength: "每段目标长度（秒）",
      parallelGroups: "并行文件组",
      audioWav: "音频 WAV",
      videoMp4: "视频 MP4",
      textgrid: "TextGrid",
      sgAlign: "强制寻找 SG 层边界",
      submitCut: "提交切分任务",
      mergeTitle: "片段合并",
      mergeDesc: "按 _segNNN 顺序合并，TextGrid 时长优先用于累计时间轴，避免漂移。",
      scanSegments: "扫描片段",
      mergePrefixes: "待合并前缀（每行一个；留空自动发现）",
      parallelMerge: "并行合并组",
      mergeHint: "默认严格检查三件套。某类文件不存在时，请取消勾选相应类型。",
      strictTriplets: "缺少配套文件时停止",
      submitMerge: "提交合并任务",
      extractTitle: "区间抽取",
      extractDesc: "从同名 MP4、WAV、TextGrid 中同步抽取多个时间区间。",
      baseName: "主文件名（不含扩展名）",
      rangeList: "区间列表（每行一个）",
      parallelRanges: "并行区间",
      submitExtract: "提交抽取任务",
      jobQueue: "任务队列",
      refreshNow: "立即刷新",
      loadingJobs: "正在读取任务……",
      noJobs: "还没有任务。可从上方任一功能页提交。",
      pickerTitle: "选择 NAS 文件或目录",
      pickerTitleLocal: "选择本地文件或目录",
      close: "关闭",
      upLevel: "上一级",
      chooseDir: "选择当前目录",
      jobDetail: "任务详情",
      inputDir: "输入目录",
      outputDirLabel: "输出目录",
      inputPathPh: "选择包含同名三件套的目录",
      outputPathPhPrefix: "默认在输入目录下建立 ",
      convertInPh: "例如：下载/YouTube_videos",
      convertOutPh: "例如：下载/converted",
      mergePrefixPh: "例如：hblvd-1",
      extractBasePh: "例如：hblvd-1",
      unavailable: "（不可用）",
      requestFailed: "请求失败",
      setOutput: "请设置输出目录",
      jobQueued: "任务 {id} 已进入队列",
      applied: "已应用：{name}",
      scanning: "正在扫描……",
      foundGroups: "发现 {groups} 个主文件组、{segments} 个分段、{prefixes} 个可合并前缀",
      foundConvert: "发现 {count} 个可转换文件",
      preview500: "（仅预览前 500 个）",
      emptyDir: "该目录为空",
      directory: "目录",
      waiting: "等待执行",
      detail: "详情",
      stop: "停止",
      delete: "删除",
      status: "状态",
      progress: "进度",
      input: "输入",
      output: "输出",
      createdAt: "创建时间",
      finishedAt: "完成时间",
      resultFiles: "结果文件（{n}）",
      runLog: "运行日志",
      noLog: "尚无日志",
      cancelSent: "已发送停止请求",
      confirmDelete: "只删除这条任务记录，不删除结果文件。确定继续吗？",
      noFfmpeg: "服务器未检测到 FFmpeg",
      invalidRange: "区间格式无效：{line}",
      kindConvert: "格式转换",
      kindCut: "同步切分",
      kindMerge: "片段合并",
      kindExtract: "区间抽取",
      stQueued: "排队中",
      stRunning: "执行中",
      stCancelling: "停止中",
      stSucceeded: "已完成",
      stFailed: "失败",
      stCancelled: "已取消",
      // common API / worker messages
      errNoMatchConvert: "所选路径中没有与转换模式匹配的媒体文件",
      errNoCutGroup: "输入目录中没有可切分的 .mp4、.wav 或 .TextGrid 文件组",
      errNoMergeSeg: "没有找到符合“前缀_segNNN”命名的待合并片段",
      errUnknownKind: "未知任务类型",
      errNeedDir: "切分、合并和抽取必须选择输入目录",
      errOutputDir: "输出路径必须是目录",
      errMissingBundle: "缺少已勾选的配套文件",
      errDuration: "存在无法确定时长的片段",
      errNoBase: "找不到主文件名",
      errSrcDuration: "无法确定源文件时长",
      errRangeBeyond: "抽取区间超出源文件时长",
    },
    en: {
      eyebrow: "NAS MEDIA WORKBENCH",
      eyebrowLocal: "LOCAL MEDIA WORKBENCH",
      appTitle: "Media & TextGrid Workbench",
      appTitleLocal: "Media & TextGrid Workbench (Local)",
      subtitle: "Convert, sync-cut, merge, and extract run in the background on the NAS",
      subtitleLocal: "Convert, sync-cut, merge, and extract run in the background on this PC",
      pathEyebrow: "NAS PATH",
      pathEyebrowLocal: "LOCAL PATH",
      workerChecking: "Checking worker…",
      workerOk: "Worker OK",
      workerDown: "Worker not ready",
      serviceError: "Service error",
      gpuChecking: "Checking hardware accel…",
      gpuOk: "Intel QSV available",
      gpuNo: "Intel QSV unavailable",
      tabConvert: "Convert",
      tabCut: "Sync cut",
      tabMerge: "Merge",
      tabExtract: "Extract",
      convertTitle: "Format conversion",
      convertDesc: "Convert a single file or a folder recursively, preserving subdirectory layout.",
      scanFiles: "Scan files",
      inputRoot: "Input location",
      inputFileOrDir: "Input file or folder",
      outputRoot: "Output location",
      outputDir: "Output folder",
      choose: "Browse",
      convertMode: "Mode",
      modeV2A: "Video → audio",
      modeA2A: "Audio → audio",
      modeV2V: "Video → video",
      modeCompress: "Video compress",
      audioCodec: "Audio codec",
      sampleRate: "Sample rate",
      channels: "Channels",
      mono: "Mono",
      stereo: "Stereo",
      audioBitrate: "Audio bitrate",
      videoCodec: "Video codec",
      qualityCrf: "Quality CRF / Q",
      resolution: "Resolution",
      keepResolution: "Keep original",
      encodeSpeed: "Encode speed",
      videoContainer: "Video container",
      parallelFiles: "Parallel files",
      recursive: "Scan subfolders recursively",
      overwrite: "Overwrite existing output",
      quickPresets: "Quick presets",
      presetCorpus: "Corpus WAV 16 kHz mono",
      presetMp3: "MP3 192k",
      presetCompress: "Video compress CRF28",
      presetQsv: "Intel fast encode",
      submitConvert: "Submit convert job",
      cutTitle: "Sync cut",
      cutDesc: "Cut MP4, WAV, and TextGrid together by fixed length or nearest SG-boundary alignment.",
      scanGroups: "Scan file groups",
      segmentLength: "Target segment length (s)",
      parallelGroups: "Parallel groups",
      audioWav: "Audio WAV",
      videoMp4: "Video MP4",
      textgrid: "TextGrid",
      sgAlign: "Snap to SG tier boundaries",
      submitCut: "Submit cut job",
      mergeTitle: "Merge segments",
      mergeDesc: "Merge by _segNNN order; TextGrid duration drives the timeline to avoid drift.",
      scanSegments: "Scan segments",
      mergePrefixes: "Prefixes to merge (one per line; leave empty to auto-detect)",
      parallelMerge: "Parallel merge groups",
      mergeHint: "Triplets are required by default. Uncheck a type if those files are missing.",
      strictTriplets: "Stop if companions are missing",
      submitMerge: "Submit merge job",
      extractTitle: "Range extract",
      extractDesc: "Extract multiple time ranges from same-stem MP4, WAV, and TextGrid together.",
      baseName: "Stem (no extension)",
      rangeList: "Ranges (one per line)",
      parallelRanges: "Parallel ranges",
      submitExtract: "Submit extract job",
      jobQueue: "Job queue",
      refreshNow: "Refresh now",
      loadingJobs: "Loading jobs…",
      noJobs: "No jobs yet. Submit one from a tool tab above.",
      pickerTitle: "Choose a NAS file or folder",
      pickerTitleLocal: "Choose a local file or folder",
      close: "Close",
      upLevel: "Up",
      chooseDir: "Use this folder",
      jobDetail: "Job detail",
      inputDir: "Input folder",
      outputDirLabel: "Output folder",
      inputPathPh: "Folder that holds matched media triplets",
      outputPathPhPrefix: "Default subfolder under input: ",
      convertInPh: "e.g. downloads/YouTube_videos",
      convertOutPh: "e.g. downloads/converted",
      mergePrefixPh: "e.g. hblvd-1",
      extractBasePh: "e.g. hblvd-1",
      unavailable: " (unavailable)",
      requestFailed: "Request failed",
      setOutput: "Please set an output folder",
      jobQueued: "Job {id} queued",
      applied: "Applied: {name}",
      scanning: "Scanning…",
      foundGroups: "Found {groups} stem group(s), {segments} segment(s), {prefixes} mergeable prefix(es)",
      foundConvert: "Found {count} convertible file(s)",
      preview500: " (preview first 500 only)",
      emptyDir: "This folder is empty",
      directory: "Folder",
      waiting: "Waiting",
      detail: "Detail",
      stop: "Stop",
      delete: "Delete",
      status: "Status",
      progress: "Progress",
      input: "Input",
      output: "Output",
      createdAt: "Created",
      finishedAt: "Finished",
      resultFiles: "Result files ({n})",
      runLog: "Run log",
      noLog: "No log yet",
      cancelSent: "Stop request sent",
      confirmDelete: "Delete this job record only (not result files). Continue?",
      noFfmpeg: "FFmpeg not found on the server",
      invalidRange: "Invalid range: {line}",
      kindConvert: "Convert",
      kindCut: "Sync cut",
      kindMerge: "Merge",
      kindExtract: "Extract",
      stQueued: "Queued",
      stRunning: "Running",
      stCancelling: "Stopping",
      stSucceeded: "Done",
      stFailed: "Failed",
      stCancelled: "Cancelled",
      errNoMatchConvert: "No media files match the selected convert mode under this path",
      errNoCutGroup: "No cuttable .mp4 / .wav / .TextGrid groups in the input folder",
      errNoMergeSeg: "No segments matching prefix_segNNN naming were found",
      errUnknownKind: "Unknown job type",
      errNeedDir: "Cut, merge, and extract require an input directory",
      errOutputDir: "Output path must be a directory",
      errMissingBundle: "Missing selected companion files",
      errDuration: "Some segments have unknown duration",
      errNoBase: "Stem not found",
      errSrcDuration: "Could not determine source duration",
      errRangeBeyond: "Extract range exceeds source duration",
    },
  };

  // Chinese API/error → English (prefix / full-string) for runtime toast
  const ZH_ERR = [
    ["所选路径中没有与转换模式匹配的媒体文件", "errNoMatchConvert"],
    ["输入目录中没有可切分的 .mp4、.wav 或 .TextGrid 文件组", "errNoCutGroup"],
    ["没有找到符合“前缀_segNNN”命名的待合并片段", "errNoMergeSeg"],
    ["未知任务类型", "errUnknownKind"],
    ["切分、合并和抽取必须选择输入目录", "errNeedDir"],
    ["输出路径必须是目录", "errOutputDir"],
    ["缺少已勾选的配套文件", "errMissingBundle"],
    ["存在无法确定时长的片段", "errDuration"],
    ["找不到主文件名", "errNoBase"],
    ["无法确定源文件时长", "errSrcDuration"],
    ["抽取区间超出源文件时长", "errRangeBeyond"],
    ["请设置输出目录", "setOutput"],
    ["服务器未检测到 FFmpeg", "noFfmpeg"],
    ["请求失败", "requestFailed"],
  ];

  let lang = "zh";
  /** @type {"nas"|"local"} */
  let deployment = "nas";

  /** Keys that switch wording for local Windows edition vs NAS. */
  const DEPLOY_KEYS = {
    eyebrow: { nas: "eyebrow", local: "eyebrowLocal" },
    appTitle: { nas: "appTitle", local: "appTitleLocal" },
    subtitle: { nas: "subtitle", local: "subtitleLocal" },
    pathEyebrow: { nas: "pathEyebrow", local: "pathEyebrowLocal" },
    pickerTitle: { nas: "pickerTitle", local: "pickerTitleLocal" },
  };

  function resolveKey(key) {
    const map = DEPLOY_KEYS[key];
    if (!map) return key;
    return map[deployment] || map.nas || key;
  }

  function normalize(v) {
    if (!v) return null;
    v = String(v).trim().toLowerCase().replace("_", "-");
    if (v === "zh" || v.startsWith("zh")) return "zh";
    if (v === "en" || v.startsWith("en")) return "en";
    return null;
  }

  function detect() {
    try {
      const q = new URLSearchParams(location.search).get("lang");
      const fromQ = normalize(q);
      if (fromQ) return fromQ;
    } catch (_) {}
    try {
      const c = document.cookie.split(";").map(s => s.trim()).find(s => s.startsWith(COOKIE + "="));
      if (c) {
        const fromC = normalize(c.split("=").slice(1).join("="));
        if (fromC) return fromC;
      }
    } catch (_) {}
    try {
      const fromL = normalize(localStorage.getItem(STORAGE));
      if (fromL) return fromL;
    } catch (_) {}
    return "zh";
  }

  function persist(next) {
    lang = next;
    try {
      localStorage.setItem(STORAGE, next);
    } catch (_) {}
    try {
      document.cookie = `${COOKIE}=${next};path=/;max-age=${60 * 60 * 24 * 365};SameSite=Lax`;
    } catch (_) {}
    document.documentElement.lang = next === "en" ? "en" : "zh-CN";
    document.documentElement.setAttribute("data-lang", next);
  }

  function t(key, vars) {
    const resolved = resolveKey(key);
    const table = M[lang] || M.zh;
    let s = table[resolved] ?? M.zh[resolved] ?? table[key] ?? M.zh[key] ?? key;
    if (vars) {
      Object.entries(vars).forEach(([k, v]) => {
        s = s.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
      });
    }
    return s;
  }

  function setDeployment(next) {
    const d = String(next || "nas").toLowerCase() === "local" ? "local" : "nas";
    if (d === deployment) {
      applyStatic();
      return;
    }
    deployment = d;
    document.documentElement.setAttribute("data-deployment", deployment);
    applyStatic();
  }

  function translateMessage(msg) {
    if (msg == null) return "";
    let s = String(msg);
    if (lang !== "en") return s;
    for (const [zh, key] of ZH_ERR) {
      if (s.includes(zh)) {
        s = s.split(zh).join(t(key));
      }
    }
    // 区间格式无效：line
    const m = s.match(/^区间格式无效：(.+)$/);
    if (m) return t("invalidRange", { line: m[1] });
    return s;
  }

  function applyStatic() {
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.getAttribute("data-i18n");
      if (!key) return;
      if (el.dataset.i18nHtml === "1") el.innerHTML = t(key);
      else el.textContent = t(key);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (key) el.placeholder = t(key);
    });
    document.querySelectorAll("[data-i18n-title]").forEach(el => {
      const key = el.getAttribute("data-i18n-title");
      if (key) el.title = t(key);
    });
    document.querySelectorAll("[data-i18n-aria]").forEach(el => {
      const key = el.getAttribute("data-i18n-aria");
      if (key) el.setAttribute("aria-label", t(key));
    });
    // option labels
    document.querySelectorAll("option[data-i18n]").forEach(el => {
      const key = el.getAttribute("data-i18n");
      if (key) el.textContent = t(key);
    });
    const title = t("appTitle");
    document.title = title;
    // switcher active state
    document.querySelectorAll(".langsw a").forEach(a => {
      a.classList.toggle("on", a.dataset.lang === lang);
    });
  }

  function kindLabel(kind) {
    return ({ convert: t("kindConvert"), cut: t("kindCut"), merge: t("kindMerge"), extract: t("kindExtract") })[kind] || kind;
  }

  function statusLabel(status) {
    return ({
      queued: t("stQueued"),
      running: t("stRunning"),
      cancelling: t("stCancelling"),
      succeeded: t("stSucceeded"),
      failed: t("stFailed"),
      cancelled: t("stCancelled"),
    })[status] || status;
  }

  function setupSwitcher(onChange) {
    const row = document.querySelector(".health-row");
    if (!row || document.querySelector(".langsw")) return;
    const box = document.createElement("span");
    box.className = "langsw";
    box.setAttribute("role", "group");
    box.setAttribute("aria-label", "Language");
    box.innerHTML = `
      <a href="?lang=zh" data-lang="zh">中文</a>
      <a href="?lang=en" data-lang="en">EN</a>`;
    row.prepend(box);
    box.addEventListener("click", e => {
      const a = e.target.closest("a[data-lang]");
      if (!a) return;
      e.preventDefault();
      const next = a.dataset.lang;
      if (next === lang) return;
      persist(next);
      applyStatic();
      if (typeof onChange === "function") onChange(next);
      // clean query without reload if present
      try {
        const u = new URL(location.href);
        if (u.searchParams.has("lang")) {
          u.searchParams.set("lang", next);
          history.replaceState(null, "", u.pathname + u.search + u.hash);
        }
      } catch (_) {}
    });
  }

  function init(onChange) {
    persist(detect());
    setupSwitcher(onChange);
    applyStatic();
  }

  global.MWB_I18N = {
    t,
    translateMessage,
    kindLabel,
    statusLabel,
    applyStatic,
    setDeployment,
    init,
    get lang() {
      return lang;
    },
    get deployment() {
      return deployment;
    },
    setLang(next, onChange) {
      const n = normalize(next) || "zh";
      persist(n);
      applyStatic();
      if (typeof onChange === "function") onChange(n);
    },
  };
})(window);

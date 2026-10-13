/* Frontend-only adapter. All API calls stay in this browser; nothing is sent. */
(() => {
  const clone = value => JSON.parse(JSON.stringify(value));
  const cache = new Map();
  const prefix = "zhilai-frontend-demo:";
  window.DemoStorage = {
    getItem(key) {
      try { return localStorage.getItem(prefix + key) ?? cache.get(key) ?? null; }
      catch (_) { return cache.get(key) ?? null; }
    },
    setItem(key, value) {
      cache.set(key, String(value));
      try { localStorage.setItem(prefix + key, String(value)); } catch (_) { /* memory fallback */ }
    },
    removeItem(key) {
      cache.delete(key);
      try { localStorage.removeItem(prefix + key); } catch (_) { /* memory fallback */ }
    }
  };
  const storageKey = "state-v1";
  const data = clone(window.FrontendDemoData);
  try {
    const saved = JSON.parse(DemoStorage.getItem(storageKey) || "null");
    if (saved?.version === 1 && saved.config?.candidate && saved.config?.preferences && Array.isArray(saved.applications)) {
      data.config = saved.config;
      data.applications = saved.applications;
      if (Array.isArray(saved.events)) data.events = saved.events;
    }
  } catch (_) { /* corrupted/blocked storage is not a startup blocker */ }
  const stages = ["准备投递", "沟通中", "提交待确认", "已投递", "测评", "面试", "Offer", "已结束"];
  const now = () => new Date().toISOString();
  function persist() {
    DemoStorage.setItem(storageKey, JSON.stringify({version: 1, config: data.config, applications: data.applications, events: data.events}));
  }
  function recordEvent(type, id, payload) {
    data.events.unshift({id: Date.now(), entity_type: "application", entity_id: String(id), event_type: type, payload_json: JSON.stringify(payload), occurred_at: now()});
    data.events = data.events.slice(0, 30);
  }
  function progress(payload, existing, jobId) {
    if (!stages.includes(payload.stage)) throw new Error("请选择有效求职阶段");
    if (payload.note !== undefined && (typeof payload.note !== "string" || payload.note.length > 2000)) throw new Error("备注最多 2000 字");
    let row = existing;
    if (!row) {
      const job = data.jobs.find(item => item.id === jobId);
      if (!job) throw new Error("演示岗位不存在");
      const id = Math.max(0, ...data.applications.map(item => item.id)) + 1;
      row = {id, job_id: job.id, title: job.title, company: job.company, location: job.location, source: job.source, channel: job.source, url: job.url, apply_url: job.apply_url, strategy: job.strategy, overall_score: job.overall_score, status: "需要人工处理", greeting: null, external_id: null, evidence: null, error: null, created_at: now(), updated_at: now(), progress_note: ""};
      data.applications.unshift(row);
    }
    Object.assign(row, {recruitment_stage: payload.stage, progress_source: "manual", progress_updated_at: now()});
    if (payload.note !== undefined) row.progress_note = payload.note;
    recordEvent("演示进度已更新", row.id, {stage: payload.stage, source: "manual"});
    persist();
    return row;
  }
  function validateConfig(config) {
    if (!config || !config.candidate || !config.preferences || !Array.isArray(config.official_sites)) throw new Error("请保留完整的演示配置结构");
    for (const key of ["boss", "mail", "greetings", "fixed_answers"]) {
      if (!config[key] || typeof config[key] !== "object") throw new Error(`缺少配置：${key}`);
    }
    if (!Array.isArray(config.candidate.skills) || !config.candidate.skills.every(item => typeof item === "string")) throw new Error("能力关键词应为文本数组");
    for (const key of ["target_titles", "locations", "excluded_keywords", "blacklisted_companies", "employment_types", "work_modes", "boss_keywords", "official_keywords", "culture_preferences", "community_risk_avoidances"]) {
      if (!Array.isArray(config.preferences[key])) throw new Error(`偏好 ${key} 应为数组`);
    }
  }
  const getRoutes = {
    "/api/dashboard": "dashboard", "/api/jobs": "jobs", "/api/recommendations": "recommendations",
    "/api/applications": "applications", "/api/events": "events", "/api/config": "config",
    "/api/resume": "resume", "/api/channels": "channels", "/api/knowledge/status": "knowledgeStatus",
    "/api/knowledge/documents": "knowledgeDocuments"
  };
  async function route(path, method, body) {
    if (method === "GET" && getRoutes[path]) return data[getRoutes[path]];
    if (method === "PUT" && path === "/api/config") {
      validateConfig(body);
      data.config = clone(body);
      persist();
      return data.config;
    }
    if (method === "POST" && path === "/api/applications/manual") {
      if (!Number.isSafeInteger(body.job_id) || body.job_id <= 0) throw new Error("岗位 ID 无效");
      return progress(body, data.applications.find(item => item.job_id === body.job_id), body.job_id);
    }
    const match = path.match(/^\/api\/applications\/(\d+)\/progress$/);
    if (method === "PUT" && match) {
      const existing = data.applications.find(item => item.id === Number(match[1]));
      if (!existing) throw new Error("演示记录不存在");
      return progress(body, existing, existing.job_id);
    }
    if (method === "POST" && path === "/api/resume") throw new Error("纯前端演示不解析真实简历，请沿用演示简历");
    if (method === "POST" && path === "/api/run/discover") {
      return {completed: 1, created: 0, message: "演示结果已加载，未进行网络采集", sources: [{source: "demo", records: data.jobs.length, created: 0, status: "合成演示"}]};
    }
    if (method === "POST" && path === "/api/run/evaluate") return {evaluated: data.jobs.length, message: "展示预设评估，不执行模型推理"};
    if (method === "POST" && path === "/api/run/plan-all") return {planned: 0, message: "演示模式不生成真实投递任务，请使用记录进度"};
    if (method === "POST" && path === "/api/demo/seed") return {created: data.jobs.length, message: "当前已是合成演示数据"};
    if (method === "POST" && path === "/api/run/execute-all") {
      if (body.live) throw new Error("前端演示不能真实投递或发送消息");
      return {processed: 0, message: "仅展示演练入口，无外部操作"};
    }
    if (method === "POST" && ["/api/run/replies", "/api/run/receipts"].includes(path)) return {processed: 0, message: "演示模式不访问邮箱或招聘网站"};
    if (method === "POST" && path === "/api/knowledge/fetch") return {status: "demo", message: "纯前端演示不读取外网页面"};
    if (method === "POST" && path === "/api/knowledge/documents") return {status: "needs_review", chunks: 0, reasons: ["演示仅展示表单，不执行文档准入或向量化"]};
    throw new Error("此功能需要完整后端，当前只提供前端演示");
  }
  window.fetch = async (input, options = {}) => {
    const requested = typeof input === "string" ? input : input.url;
    // A root path under file:// on Windows inherits its drive (/C:/api/...).
    const path = requested.startsWith("/api/") ? requested.split("?")[0] : new URL(requested, location.href).pathname;
    if (!path.startsWith("/api/")) return new Response(JSON.stringify({message: "演示模式不发送网络请求"}), {status: 403, headers: {"Content-Type": "application/json"}});
    try {
      const method = (options.method || "GET").toUpperCase();
      const payload = options.body ? JSON.parse(options.body) : {};
      const result = await route(path, method, payload);
      return new Response(JSON.stringify(result), {status: 200, headers: {"Content-Type": "application/json"}});
    } catch (error) {
      return new Response(JSON.stringify({message: error.message}), {status: 400, headers: {"Content-Type": "application/json"}});
    }
  };
  document.querySelector("#reset-demo").addEventListener("click", () => {
    if (!confirm("重置本演示的浏览器记录与配置？不影响原项目或其他网站。")) return;
    DemoStorage.removeItem(storageKey);
    DemoStorage.removeItem("job-agent-selected-channels");
    location.reload();
  });
  document.addEventListener("click", event => {
    const anchor = event.target.closest("a[target='_blank']");
    if (!anchor) return;
    event.preventDefault();
    if (typeof window.toast === "function") window.toast("演示中的岗位与来源链接为示例，不访问招聘平台");
  });
})();

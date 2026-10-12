const state = {
  dashboard: {},
  jobs: [],
  applications: [],
  events: [],
  config: null,
  resume: {configured: false, available: false, filename: "", path: "", profile_source: "manual", text_available: false},
  channels: [],
  knowledgeStatus: {documents: {}, chunks: 0, scopes: []},
  knowledgeDocuments: [],
  channelDialogMode: "discover",
  taskStep: "resume",
  taskRunning: false
};

const STRATEGY_PRESETS = {
  stretch: {"冲高": 0.55, "持平": 0.35, "保底": 0.10},
  balanced: {"冲高": 0.25, "持平": 0.50, "保底": 0.25},
  safe: {"冲高": 0.10, "持平": 0.30, "保底": 0.60}
};

const KNOWLEDGE_ROLE_LABELS = {product: "产品", data: "数据分析", algorithm: "算法", backend: "后端"};
const KNOWLEDGE_TOPIC_LABELS = {
  duties: "职责", skills: "技能", interview: "面试", workload: "强度", compensation: "薪酬",
  culture: "文化", growth: "成长", stability: "稳定性", work_style: "办公方式"
};
const KNOWLEDGE_POLICY_LABELS = {accepted: "已入库", needs_review: "待复核", rejected: "已拒绝", duplicate: "重复"};

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

const navigationIcons = {recommendations: "spark", overview: "home", jobs: "briefcase", applications: "document", knowledge: "book", config: "settings", audit: "clock"};
$$('.nav-item').forEach(button => button.insertAdjacentHTML('afterbegin', JobIcons.icon(navigationIcons[button.dataset.view])));
$("#refresh").insertAdjacentHTML('afterbegin', JobIcons.icon("refresh"));
$$('.header-actions [data-open-task]').forEach(button => button.insertAdjacentHTML('afterbegin', JobIcons.icon("search")));
$(".recommendation-search").insertAdjacentHTML('afterbegin', JobIcons.icon("search"));

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json"},
    ...options
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.error || "请求失败");
  return data;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function toast(message, error = false) {
  const box = $("#toast");
  box.textContent = message;
  box.className = error ? "show error" : "show";
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => box.className = "", 4600);
}

function chip(value) {
  const text = String(value || "—");
  const shown = text === "不投" ? "不投（过滤）" : text;
  const className = text.includes("不投") || text.includes("失败") || text.includes("过滤")
    ? "red" : text.includes("冲高") || text.includes("等待")
      ? "orange" : text.includes("持平") || text.includes("确认")
        ? "blue" : "";
  return `<span class="chip ${className}">${escapeHtml(shown)}</span>`;
}

function strategyLabel(value) {
  return ({campus_api: "校园官网公开接口", json_api: "配置型 JSON 接口", browser: "浏览器页面"})[value] || value || "未配置";
}

function autofillLabel(capabilities = {}) {
  return ({
    planned: "自动填表待适配",
    experimental: "自动填表实验能力",
    available: "自动填表已适配",
    not_planned: "不含自动填表"
  })[capabilities.autofill_status] || "自动填表待适配";
}

function fallbackChannels(config, dashboard) {
  const latest = Object.fromEntries((dashboard.sources || []).map(item => [item.source, item]));
  const statusLabel = status => ({
    api_fetched: "正常：API 已提取真实岗位",
    browser_fetched: "正常：浏览器已提取真实岗位",
    portal_unparsed: "需维护：未提取到稳定岗位",
    auth_required: "需要登录或恢复会话"
  })[status] || status || "尚未检查";
  const bossEnabled = config.boss?.enabled === true;
  const bossReady = bossEnabled && (config.preferences?.boss_keywords || []).length > 0;
  const bossRun = latest.boss;
  const channels = [{
    id: "boss", name: "BOSS直聘", type: "boss", enabled: bossEnabled, ready: bossReady,
    keywords: config.preferences?.boss_keywords || [], strategy: "browser",
    url: "https://www.zhipin.com/web/geek/jobs",
    health: !bossEnabled ? "disabled" : !bossReady ? "not_ready" : bossRun?.status || "never_run",
    health_label: !bossEnabled ? "未启用" : !bossReady ? "配置不完整" : statusLabel(bossRun?.status),
    missing: !bossEnabled ? ["需要启用 BOSS 渠道"] : []
  }];
  for (const site of config.official_sites || []) {
    const id = `official:${site.id || "invalid"}`;
    const enabled = site.enabled !== false;
    const ready = enabled && Boolean(site.id && site.list_url && site.strategy && (site.strategy !== "campus_api" || site.adapter));
    const run = latest[id];
    const autofill = site.autofill || {};
    channels.push({
      id, name: site.name || site.id || "未命名官网渠道", type: "official", enabled, ready,
      keywords: config.preferences?.official_keywords || [], strategy: site.strategy || "未配置",
      url: site.list_url || "", health: !enabled ? "disabled" : !ready ? "not_ready" : run?.status || "never_run",
      health_label: !enabled ? "未启用" : !ready ? "配置不完整" : statusLabel(run?.status),
      missing: ready ? [] : ["渠道定义不完整"],
      capabilities: {
        discovery: site.strategy === "browser" ? "browser_optional" : "available",
        autofill_status: autofill.status || (site.form ? "experimental" : "planned"),
        autofill_profile: autofill.profile || ""
      }
    });
  }
  return channels;
}

async function load() {
  const recommendationsReady = refreshRecommendations();
  const [dashboard, jobs, applications, events, config, resume] = await Promise.all([
    api("/api/dashboard"), api("/api/jobs"), api("/api/applications"), api("/api/events"), api("/api/config"), api("/api/resume")
  ]);
  let knowledgeStatus = dashboard.knowledge || {documents: {}, chunks: 0, scopes: []};
  let knowledgeDocuments = [];
  try {
    [knowledgeStatus, knowledgeDocuments] = await Promise.all([
      api("/api/knowledge/status"), api("/api/knowledge/documents")
    ]);
  } catch (error) {
    knowledgeStatus = {...knowledgeStatus, error: error.message};
  }
  let channels = dashboard.channels || [];
  try {
    channels = await api("/api/channels");
  } catch (_) {
    channels = fallbackChannels(config, dashboard);
  }
  Object.assign(state, {dashboard, jobs, applications, events, config, resume, channels, knowledgeStatus, knowledgeDocuments});
  await recommendationsReady;
  render();
  $("#last-refresh").textContent = `更新于 ${new Date().toLocaleTimeString("zh-CN", {hour: "2-digit", minute: "2-digit"})}`;
}

let recommendationRequest = 0;
async function refreshRecommendations() {
  const request = ++recommendationRequest;
  Recommendations.setLoading();
  try {
    const data = await api("/api/recommendations");
    if (request === recommendationRequest) Recommendations.setData(data);
  } catch (error) {
    if (request === recommendationRequest) Recommendations.setError(error.message);
  }
}

function render() {
  renderMetrics();
  renderStrategies();
  renderChannels();
  renderJobs();
  renderApplications();
  renderKnowledge();
  renderConfig();
  renderEvents();
}

function renderMetrics() {
  const dashboard = state.dashboard;
  const total = Object.values(dashboard.jobs || {}).reduce((sum, count) => sum + count, 0);
  const eligible = Object.entries(dashboard.strategies || {})
    .filter(([name]) => name !== "不投")
    .reduce((sum, [, count]) => sum + count, 0);
  const planned = (dashboard.applications || {})["待执行"] || 0;
  const confirmed = (dashboard.applications || {})["投递已确认"] || 0;
  const values = [
    ["已收录岗位", total, "BOSS 与官网统一汇总"],
    ["通过评估", eligible, "进入三种投递策略"],
    ["待执行任务", planned, "受今日额度限制"],
    ["已确认投递", confirmed, "平台证据或邮件回执"]
  ];
  $("#metrics").innerHTML = values.map(item => `
    <div class="metric"><span>${item[0]}</span><b>${item[1]}</b><small>${item[2]}</small></div>
  `).join("");
}

function renderStrategies() {
  const data = state.dashboard.strategies || {};
  const strategyNames = ["冲高", "持平", "保底"];
  const max = Math.max(1, ...strategyNames.map(name => data[name] || 0));
  $("#strategy-chart").innerHTML = strategyNames.map(name => `
    <div class="bar-row"><b>${name}</b><div class="bar"><i style="width:${((data[name] || 0) / max) * 100}%"></i></div><span>${data[name] || 0}</span></div>
  `).join("");
  const skipped = data["不投"] || 0;
  $("#skip-summary").innerHTML = skipped
    ? `<b>${skipped} 个岗位已过滤</b><span>原因可能是硬条件不满足、能力差距过大、岗位明显过低或公司位于不投名单。</span>`
    : `<b>暂无过滤岗位</b><span>不投岗位不会占用任何每日投递额度。</span>`;
}

function healthClass(health) {
  if (["api_fetched", "browser_fetched"].includes(health)) return "healthy";
  if (["disabled", "never_run"].includes(health)) return "neutral";
  return "warning";
}

function renderChannels() {
  const container = $("#source-health");
  if (!state.channels.length) {
    container.innerHTML = `<div class="empty-state"><b>尚未配置渠道</b><span>请先配置 BOSS 或固定官网/ATS。</span><button class="button ghost small" data-go-config>前往配置</button></div>`;
    bindGoConfig();
    return;
  }
  container.innerHTML = state.channels.map(channel => {
    const run = channel.last_run;
    const detail = run
      ? `${run.records_count} 条记录 · ${new Date(run.finished_at).toLocaleString("zh-CN")}`
      : (channel.missing || []).join("、") || "还没有运行记录";
    return `<div class="source-item channel-health-item">
      <div><b>${escapeHtml(channel.name)}</b><small>${escapeHtml(detail)}</small></div>
      <span class="status-dot ${healthClass(channel.health)}">${escapeHtml(channel.health_label)}</span>
    </div>`;
  }).join("");
}

function renderJobs() {
  const statuses = [...new Set(state.jobs.map(job => job.status))];
  const select = $("#job-status-filter");
  const selected = select.value;
  select.innerHTML = '<option value="">全部状态</option>' + statuses
    .map(status => `<option ${status === selected ? "selected" : ""}>${escapeHtml(status)}</option>`).join("");
  const query = $("#job-search").value.toLowerCase();
  const rows = state.jobs.filter(job =>
    (!select.value || job.status === select.value) &&
    (!query || `${job.title} ${job.company} ${job.location} ${job.source}`.toLowerCase().includes(query))
  );
  $("#jobs-body").innerHTML = rows.length ? rows.map(job => `<tr>
    <td><strong>${escapeHtml(job.title)}</strong><small>${escapeHtml(job.company)} · ${escapeHtml(job.location)}</small></td>
    <td>${chip(job.source)}</td><td>${chip(job.strategy)}</td>
    <td><span class="score">${job.match_score == null ? "—" : job.match_score}</span><small>${escapeHtml(job.evaluation_reason || "")}</small></td>
    <td><span class="score">${job.need_score == null ? "—" : job.need_score}</span></td><td>${chip(job.status)}</td>
    <td><a class="button ghost small table-action" href="${escapeHtml(job.apply_url || job.url)}" target="_blank" rel="noopener noreferrer">查看岗位</a></td>
  </tr>`).join("") : '<tr><td colspan="7" class="empty">没有符合当前条件的岗位</td></tr>';
}

function renderApplications() {
  $("#applications-body").innerHTML = state.applications.length ? state.applications.map(application => `<tr>
    <td><strong>${escapeHtml(application.title)}</strong><small>${escapeHtml(application.company)} · ${escapeHtml(application.location)}</small></td>
    <td>${chip(application.channel)}</td><td>${chip(application.strategy)}</td><td>${chip(application.status)}</td>
    <td>${new Date(application.updated_at).toLocaleString("zh-CN")}</td><td><small>${escapeHtml(application.error || application.evidence || "—")}</small></td>
  </tr>`).join("") : '<tr><td colspan="6" class="empty">还没有投递计划。先评估岗位并生成计划。</td></tr>';
}

function knowledgeStatusClass(status) {
  if (status === "accepted") return "healthy";
  if (["needs_review", "duplicate"].includes(status)) return "warning";
  return "neutral";
}

function knowledgeSourceLabel(source) {
  return ({nowcoder: "牛客", xiaohongshu: "小红书", manual: "其他公开来源"})[source] || source || "未知来源";
}

function knowledgeMethodLabel(method) {
  return ({manual_import: "人工导入", browser_visible: "浏览器可见", public_html: "公开页面"})[method] || method || "未知方式";
}

function knowledgeEmploymentLabel(value) {
  return ({full_time: "正职", internship: "实习", unknown: "未确认"})[value] || value || "未确认";
}

function renderKnowledgeScopeOptions() {
  const knowledge = state.config?.knowledge || {};
  const companySelect = $("#knowledge-company");
  const roleSelect = $("#knowledge-role");
  const currentCompany = companySelect.value;
  const currentRole = roleSelect.value;
  const companies = Object.keys(knowledge.company_aliases || {"腾讯": [], "阿里": [], "美团": [], "快手": [], "百度": []});
  const roles = Object.keys(knowledge.role_families || KNOWLEDGE_ROLE_LABELS);
  companySelect.innerHTML = companies.map(company => `<option value="${escapeHtml(company)}">${escapeHtml(company)}</option>`).join("");
  roleSelect.innerHTML = roles.map(role => `<option value="${escapeHtml(role)}">${escapeHtml(KNOWLEDGE_ROLE_LABELS[role] || role)}</option>`).join("");
  if (companies.includes(currentCompany)) companySelect.value = currentCompany;
  if (roles.includes(currentRole)) roleSelect.value = currentRole;
}

function renderKnowledge() {
  renderKnowledgeScopeOptions();
  const status = state.knowledgeStatus || {};
  const documents = status.documents || {};
  const accepted = documents.accepted || 0;
  const pending = (documents.needs_review || 0) + (documents.rejected || 0) + (documents.duplicate || 0);
  $("#knowledge-state").innerHTML = status.error ? `
    <div class="knowledge-state-error"><b>暂不可用</b><span>${escapeHtml(status.error)}；岗位池和规则评分仍可使用。</span></div>
  ` : `
    <div><b>${accepted}</b><span>可检索帖子</span></div>
    <div><b>${status.chunks || 0}</b><span>决策证据块</span></div>
    <div><b>${pending}</b><span>未进入向量库</span></div>
    <div><b>${status.raw_text_retained ? "保留" : "不保留"}</b><span>整篇原文</span></div>
  `;
  const rows = state.knowledgeDocuments || [];
  $("#knowledge-body").innerHTML = status.error
    ? `<tr><td colspan="6" class="empty">岗位情报库暂不可用：${escapeHtml(status.error)}。其他求职流程不受影响。</td></tr>`
    : rows.length ? rows.map(document => {
    const statusLabel = KNOWLEDGE_POLICY_LABELS[document.policy_status] || document.policy_status;
    const reasons = (document.policy_reasons || []).join("；") || "已通过确定性准入检查";
    const topics = (document.topics || []).map(topic => KNOWLEDGE_TOPIC_LABELS[topic] || topic);
    const url = String(document.source_url || "");
    const title = /^https:\/\//i.test(url)
      ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHtml(document.title)}</strong></a>`
      : `<strong>${escapeHtml(document.title)}</strong>`;
    const dateValue = document.published_at || document.collected_at;
    const date = dateValue ? new Date(dateValue).toLocaleDateString("zh-CN") : "未知";
    return `<tr>
      <td>${title}<small>${escapeHtml(knowledgeSourceLabel(document.source))} · ${escapeHtml(knowledgeMethodLabel(document.collection_method))}</small></td>
      <td><strong>${escapeHtml(document.company || "未识别")} · ${escapeHtml(knowledgeEmploymentLabel(document.employment_type))}</strong><small>${escapeHtml(KNOWLEDGE_ROLE_LABELS[document.role_family] || document.role_family || "未识别")}${document.business_unit ? ` · ${escapeHtml(document.business_unit)}` : ""}</small></td>
      <td><span class="status-dot ${knowledgeStatusClass(document.policy_status)}">${escapeHtml(statusLabel)}</span><small title="${escapeHtml(reasons)}">${escapeHtml(reasons)}</small></td>
      <td>${topics.length ? topics.map(topic => `<span class="chip">${escapeHtml(topic)}</span>`).join(" ") : "—"}<small>${document.chunk_count || 0} 个证据块</small></td>
      <td>${escapeHtml(date)}<small>${document.published_at ? "发布" : "采集"}</small></td>
      <td><button class="button ghost small table-action" type="button" data-delete-knowledge="${document.id}">删除</button></td>
    </tr>`;
  }).join("") : '<tr><td colspan="6" class="empty">还没有帖子。先导入一篇能影响岗位判断的真实经历。</td></tr>';
  $$('[data-delete-knowledge]').forEach(button => button.onclick = () => deleteKnowledgeDocument(Number(button.dataset.deleteKnowledge)));
}

async function refreshKnowledge() {
  const [knowledgeStatus, knowledgeDocuments] = await Promise.all([
    api("/api/knowledge/status"), api("/api/knowledge/documents")
  ]);
  Object.assign(state, {knowledgeStatus, knowledgeDocuments});
  renderKnowledge();
  await refreshRecommendations();
}

async function importKnowledge(event) {
  event.preventDefault();
  const button = $("#knowledge-import");
  const resultBox = $("#knowledge-import-result");
  const content = $("#knowledge-content").value.trim();
  if (content.length < 120) {
    resultBox.textContent = "正文至少需要 120 字。";
    $("#knowledge-content").focus();
    return;
  }
  const payload = {
    source: $("#knowledge-source").value,
    collection_method: $("#knowledge-method").value,
    company: $("#knowledge-company").value,
    role_family: $("#knowledge-role").value,
    employment_type: $("#knowledge-employment-type").value,
    url: $("#knowledge-url").value.trim(),
    title: $("#knowledge-title").value.trim(),
    published_at: $("#knowledge-published").value || null,
    business_unit: $("#knowledge-unit").value.trim(),
    city: $("#knowledge-city").value.trim(),
    seniority: $("#knowledge-seniority").value.trim(),
    content,
    approve_review: $("#knowledge-approve-review").checked
  };
  button.disabled = true;
  button.textContent = "正在检查…";
  resultBox.textContent = "";
  try {
    const result = await api("/api/knowledge/documents", {method: "POST", body: JSON.stringify(payload)});
    const label = KNOWLEDGE_POLICY_LABELS[result.status] || result.status;
    const reason = (result.reasons || []).join("；");
    resultBox.textContent = `${label} · ${result.chunks || 0} 个证据块${reason ? ` · ${reason}` : ""}`;
    toast(result.status === "accepted" ? "帖子已进入岗位情报库" : `准入结果：${label}`, result.status === "rejected");
    if (["accepted", "duplicate"].includes(result.status)) {
      $("#knowledge-url").value = "";
      $("#knowledge-title").value = "";
      $("#knowledge-published").value = "";
      $("#knowledge-unit").value = "";
      $("#knowledge-city").value = "";
      $("#knowledge-seniority").value = "";
      $("#knowledge-content").value = "";
      $("#knowledge-approve-review").checked = false;
      updateKnowledgeContentCount();
    }
    await refreshKnowledge();
  } catch (error) {
    resultBox.textContent = error.message;
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "检查并导入";
  }
}

async function fetchKnowledge(event) {
  event.preventDefault();
  const button = $("#knowledge-fetch");
  const resultBox = $("#knowledge-fetch-result");
  button.disabled = true;
  button.textContent = "正在读取…";
  try {
    const result = await api("/api/knowledge/fetch", {
      method: "POST",
      body: JSON.stringify({source: $("#knowledge-fetch-source").value, url: $("#knowledge-fetch-url").value.trim()})
    });
    const imported = result.import;
    resultBox.textContent = imported
      ? `${result.message} 准入结果：${KNOWLEDGE_POLICY_LABELS[imported.status] || imported.status}，${imported.chunks || 0} 个证据块。`
      : result.message;
    toast(imported?.status === "accepted" ? "公开页面已解析并入库" : result.message, ["access_limited", "portal_unparsed"].includes(result.status));
    await refreshKnowledge();
  } catch (error) {
    resultBox.textContent = `${error.message} 请确认这是单篇公开页面，或改用人工导入。`;
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "读取这一个页面";
  }
}

async function deleteKnowledgeDocument(documentId) {
  if (!window.confirm("删除这篇帖子及其证据块？该操作只影响本地岗位情报库。")) return;
  try {
    await api(`/api/knowledge/documents/${documentId}`, {method: "DELETE"});
    await refreshKnowledge();
    toast("帖子及其证据块已从本机删除");
  } catch (error) {
    toast(error.message, true);
  }
}

function updateKnowledgeContentCount() {
  $("#knowledge-content-count").textContent = `${$("#knowledge-content").value.length.toLocaleString("zh-CN")} / 20,000 字`;
}

function syncKnowledgeSource() {
  const source = $("#knowledge-source").value;
  if (source === "xiaohongshu") $("#knowledge-method").value = "browser_visible";
  if (source === "nowcoder" && $("#knowledge-method").value === "browser_visible") $("#knowledge-method").value = "manual_import";
  $("#knowledge-url").placeholder = source === "xiaohongshu"
    ? "https://www.xiaohongshu.com/explore/..."
    : source === "nowcoder" ? "https://www.nowcoder.com/discuss/..." : "https://...";
}

function syncKnowledgeFetchGuidance() {
  const isXhs = $("#knowledge-fetch-source").value === "xiaohongshu";
  $("#knowledge-fetch-url").placeholder = isXhs
    ? "https://www.xiaohongshu.com/explore/..."
    : "https://www.nowcoder.com/discuss/...";
  $("#knowledge-fetch-result").textContent = isXhs
    ? "小红书不会直接抓取；提交链接后只会返回登录后可见正文的安全导入说明。"
    : "牛客仅解析你提供的单篇公开讨论页，每次至少间隔 5 秒，不搜索、不翻页、不重试。";
}

function setValue(id, value) {
  const element = $(`#${id}`);
  if (element) element.value = value ?? "";
}

function listText(values) {
  return (values || []).join("、");
}

function parseList(value) {
  return [...new Set(String(value || "").split(/[，,、\n]/).map(item => item.trim()).filter(Boolean))];
}

function selectedValues(name) {
  return $$(`input[name="${name}"]:checked`).map(item => item.value);
}

function setCheckedValues(name, values) {
  const selected = new Set(values || []);
  $$(`input[name="${name}"]`).forEach(item => item.checked = selected.has(item.value));
}

function optionalNumber(value) {
  return String(value ?? "").trim() === "" ? null : Number(value);
}

function strategyPresetName(mix = {}) {
  return Object.entries(STRATEGY_PRESETS)
    .map(([name, preset]) => [name, Object.keys(preset).reduce((sum, key) => sum + Math.abs((mix[key] || 0) - preset[key]), 0)])
    .sort((a, b) => a[1] - b[1])[0][0];
}

function renderConfig() {
  if (!state.config) return;
  const config = state.config;
  const candidate = config.candidate || {};
  const preferences = config.preferences || {};
  setValue("cfg-name", candidate.name);
  setValue("cfg-headline", candidate.headline);
  setValue("cfg-years", candidate.years_experience);
  setValue("cfg-education", candidate.education || "不限");
  setValue("cfg-skills", listText(candidate.skills));
  setValue("cfg-resume", candidate.resume_path);
  $("#cfg-resume-name").textContent = state.resume.filename || "尚未上传";
  $("#cfg-resume-path").textContent = state.resume.available
    ? state.resume.path
    : state.resume.configured ? "原简历文件已不存在，请选择新文件替换。" : "上传后只保存在本机数据目录。";
  setValue("cfg-target-titles", listText(preferences.target_titles));
  setValue("cfg-locations", listText(preferences.locations));
  setValue("cfg-excluded", listText(preferences.excluded_keywords));
  setValue("cfg-blacklisted", listText(preferences.blacklisted_companies));
  setCheckedValues("cfg-employment", preferences.employment_types);
  setCheckedValues("cfg-work-mode", preferences.work_modes);
  setValue("cfg-workload-preference", preferences.workload_preference || "balanced");
  setValue("cfg-role-boundary-preference", preferences.role_boundary_preference || "no_preference");
  setValue("cfg-growth-priority", preferences.growth_priority || "medium");
  setValue("cfg-stability-priority", preferences.stability_priority || "medium");
  setValue("cfg-culture-preferences", listText(preferences.culture_preferences));
  setValue("cfg-community-risk-avoidances", listText(preferences.community_risk_avoidances));
  setValue("cfg-min-salary", preferences.minimum_salary);
  setValue("cfg-max-gap", preferences.max_experience_gap ?? 2);
  setValue("cfg-recent-days", preferences.published_within_days);
  setValue("cfg-unknown-policy", preferences.unknown_field_policy || "keep");
  setValue("cfg-tier-priority", listText(preferences.company_tiers?.["优先"]));
  setValue("cfg-tier-acceptable", listText(preferences.company_tiers?.["可接受"]));
  setValue("cfg-tier-skip", listText(preferences.company_tiers?.["不投"]));
  setValue("cfg-boss-limit", preferences.boss_daily_limit);
  setValue("cfg-official-limit", preferences.official_daily_limit);
  setValue("cfg-boss-keywords", listText(preferences.boss_keywords));
  setValue("cfg-official-keywords", listText(preferences.official_keywords));
  $("#cfg-boss-enabled").checked = config.boss?.enabled === true;
  setValue("cfg-boss-city-name", config.boss?.city_name);
  setValue("cfg-boss-city-code", config.boss?.city_code);
  setValue("cfg-greeting", config.greetings?.default);
  $("#cfg-auto-resume").checked = preferences.auto_send_resume_after_reply === true;
  $("#cfg-mail-enabled").checked = config.mail?.enabled === true;
  setValue("cfg-mail-host", config.mail?.host);
  setValue("cfg-mail-username", config.mail?.username);
  setValue("cfg-answer-phone", config.fixed_answers?.phone);
  setValue("cfg-answer-email", config.fixed_answers?.email);
  setValue("cfg-answer-city", config.fixed_answers?.current_city);
  setValue("cfg-answer-graduation", config.fixed_answers?.graduation_year);
  $("#config-editor").value = JSON.stringify(config, null, 2);

  const sites = config.official_sites || [];
  $("#configured-official-list").innerHTML = sites.length ? sites.map(site => {
    const autofill = site.autofill || {};
    const capabilities = {autofill_status: autofill.status || (site.form ? "experimental" : "planned")};
    return `<div class="configured-channel"><div><b>${escapeHtml(site.name || site.id)}</b><small>${escapeHtml(site.list_url || "未填写列表地址")}</small></div><div class="capability-chips"><span class="chip ${site.enabled === false ? "red" : "blue"}">${site.enabled === false ? "未启用" : escapeHtml(strategyLabel(site.strategy))}</span><span class="chip ${capabilities.autofill_status === "available" ? "" : "orange"}">${escapeHtml(autofillLabel(capabilities))}</span></div></div>`;
  }).join("") : `<div class="empty-state compact"><b>尚未添加官网渠道</b><span>因此现在只能使用演示数据；添加官网需要配置公开岗位 API 或页面选择器。</span></div>`;
}

function renderEvents() {
  $("#events").innerHTML = state.events.length ? state.events.map(event => `<div class="event">
    <time>${new Date(event.occurred_at).toLocaleString("zh-CN")}</time><code>${escapeHtml(event.entity_type)} #${escapeHtml(event.entity_id)}</code>
    <div><strong>${escapeHtml(event.event_type)}</strong><small>${escapeHtml(event.payload_json).slice(0, 260)}</small></div>
  </div>`).join("") : '<div class="empty">暂无事件</div>';
}

function switchView(view) {
  const focusedView = document.activeElement?.closest(".view");
  const restorePageFocus = focusedView && focusedView.id !== `view-${view}`;
  const titles = {recommendations: "智能推荐", overview: "求职工作台", jobs: "岗位池", applications: "投递台账", knowledge: "岗位情报库", config: "配置", audit: "审计日志"};
  $$(".nav-item").forEach(item => {
    item.classList.toggle("active", item.dataset.view === view);
    if (item.dataset.view === view) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  $$(".view").forEach(item => item.classList.toggle("active", item.id === `view-${view}`));
  $("#page-title").textContent = titles[view] || "求职工作台";
  $("#page-description").textContent = view === "recommendations"
    ? "看清值得投的理由，也看清要先确认的风险。"
    : "在本机筛选岗位，保留每一步决策依据。";
  if (restorePageFocus) $("#page-title").focus({preventScroll: true});
}

function bindGoConfig() {
  $$('[data-go-config]').forEach(button => {
    button.onclick = () => {
      if ($("#channel-dialog").open) $("#channel-dialog").close();
      switchView("config");
      setTimeout(() => $("#channel-settings").scrollIntoView({behavior: "smooth", block: "start"}), 50);
    };
  });
}

function validateResumeFile(file) {
  if (!file) return;
  if (!/\.(pdf|docx)$/i.test(file.name)) throw new Error("请选择 PDF 或 DOCX 简历");
  if (file.size > 10 * 1024 * 1024) throw new Error("简历不能超过 10 MB");
  if (file.size === 0) throw new Error("简历文件为空");
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.onerror = () => reject(new Error("无法读取所选简历"));
    reader.readAsDataURL(file);
  });
}

async function uploadResumeFile(file) {
  validateResumeFile(file);
  return api("/api/resume", {
    method: "POST",
    body: JSON.stringify({filename: file.name, content_base64: await fileToBase64(file)})
  });
}

function taskError(message = "") {
  const box = $("#task-error");
  box.textContent = message;
  box.hidden = !message;
}

function renderTaskResume() {
  const candidate = state.config?.candidate || {};
  const file = $("#task-resume-file").files[0];
  const hasCurrent = state.resume.available === true;
  $("#task-current-resume-name").textContent = state.resume.filename || candidate.resume_filename || "尚未上传简历";
  $("#task-current-resume-meta").textContent = hasCurrent
    ? String(state.resume.profile_source || "").startsWith("resume") ? "已从这份简历更新候选档案，可在配置页核对" : "将沿用这份简历和手动填写的候选档案"
    : state.resume.configured ? "原文件已不存在，需要选择新简历" : "首次使用需要上传 PDF 或 DOCX";
  $("#task-resume-state").textContent = hasCurrent ? "可沿用" : state.resume.configured ? "需替换" : "未就绪";
  $("#task-resume-state").className = `status-dot ${hasCurrent ? "healthy" : state.resume.configured ? "warning" : "neutral"}`;
  $("#task-resume-selection").textContent = file ? `已选择：${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB` : "单个文件，最大 10 MB";
  $("#task-current-resume").classList.toggle("will-replace", Boolean(file));
}

function renderTaskChannels() {
  const readyIds = state.channels.filter(item => item.ready).map(item => item.id);
  $("#task-start").disabled = readyIds.length === 0;
  $("#task-start").textContent = readyIds.length ? "开始获取岗位" : "先配置渠道";
  const previous = JSON.parse(localStorage.getItem("job-agent-selected-channels") || "[]");
  const selected = previous.filter(id => readyIds.includes(id));
  const defaults = selected.length ? selected : readyIds;
  const container = $("#task-channel-options");
  if (!state.channels.length) {
    container.innerHTML = `<div class="empty-state compact"><b>还没有岗位渠道</b><span>先到配置页启用一个已经适配的渠道。</span><button class="button ghost small" type="button" data-task-config>配置渠道</button></div>`;
  } else {
    const setup = readyIds.length ? "" : `<div class="empty-state compact span-2"><b>没有已就绪的真实渠道</b><span>完成一个渠道的启用和关键词配置后再运行；也可以先取消并在首页体验演示数据。</span><button class="button ghost small" type="button" data-task-config>前往配置渠道</button></div>`;
    container.innerHTML = setup + state.channels.map(channel => `<label class="channel-option ${channel.ready ? "" : "disabled"}">
      <input type="checkbox" name="task-channel" value="${escapeHtml(channel.id)}" ${defaults.includes(channel.id) ? "checked" : ""} ${channel.ready ? "" : "disabled"}>
      <div class="channel-option-main"><div><b>${escapeHtml(channel.name)}</b><span class="status-dot ${healthClass(channel.health)}">${escapeHtml(channel.health_label)}</span></div>
      <small>${escapeHtml(channel.type === "boss" ? "浏览器渠道" : `${strategyLabel(channel.strategy)} · ${autofillLabel(channel.capabilities)}`)}</small>
      <p>${channel.ready ? `关键词：${escapeHtml((channel.keywords || []).join("、") || "跟随本次岗位名称")}` : escapeHtml((channel.missing || []).join("、") || "配置不完整")}</p></div>
    </label>`).join("");
  }
  $$('[data-task-config]').forEach(button => button.onclick = () => {
    $("#task-dialog").close();
    switchView("config");
    setTimeout(() => $("#channel-settings").scrollIntoView({behavior: "smooth", block: "start"}), 50);
  });
}

function renderTaskDefaults() {
  const preferences = state.config?.preferences || {};
  $("#task-resume-file").value = "";
  setValue("task-titles", listText(preferences.target_titles));
  setValue("task-locations", listText(preferences.locations));
  setValue("task-excluded", listText(preferences.excluded_keywords));
  setValue("task-blacklisted", listText(preferences.blacklisted_companies));
  setCheckedValues("task-employment", preferences.employment_types);
  setCheckedValues("task-work-mode", preferences.work_modes);
  setValue("task-workload-preference", preferences.workload_preference || "balanced");
  setValue("task-role-boundary-preference", preferences.role_boundary_preference || "no_preference");
  setValue("task-growth-priority", preferences.growth_priority || "medium");
  setValue("task-stability-priority", preferences.stability_priority || "medium");
  setValue("task-culture-preferences", listText(preferences.culture_preferences));
  setValue("task-community-risk-avoidances", listText(preferences.community_risk_avoidances));
  setValue("task-min-salary", preferences.minimum_salary);
  setValue("task-max-gap", preferences.max_experience_gap ?? 2);
  setValue("task-recent-days", preferences.published_within_days);
  setValue("task-unknown-policy", preferences.unknown_field_policy || "keep");
  const preset = preferences.strategy_mode || strategyPresetName(preferences.strategy_mix);
  const presetInput = $(`input[name="task-strategy"][value="${preset}"]`);
  if (presetInput) presetInput.checked = true;
  renderTaskResume();
  renderTaskChannels();
}

function showTaskStep(step) {
  state.taskStep = step;
  const isResume = step === "resume";
  const isRules = step === "rules";
  const isLoading = step === "loading";
  $("#task-step-resume").hidden = !isResume;
  $("#task-step-rules").hidden = !isRules;
  $("#task-step-loading").hidden = !isLoading;
  $$(".wizard-step").forEach(item => item.classList.toggle("active", !item.hidden));
  $$("[data-progress]").forEach(item => {
    const progress = item.dataset.progress;
    item.classList.toggle("active", (isResume && progress === "resume") || (isRules && progress === "rules") || (isLoading && progress === "run"));
    item.classList.toggle("complete", (isRules && progress === "resume") || (isLoading && ["resume", "rules"].includes(progress)));
  });
  $("#task-actions").hidden = isLoading;
  $("#task-back").hidden = !isRules;
  $("#task-next").hidden = !isResume;
  $("#task-start").hidden = !isRules;
  $("#task-subtitle").textContent = isResume
    ? "可以沿用当前简历，也可以只为这次任务替换它。"
    : isRules ? "沿用上次条件并按需修改，不必每次重新填写。" : "各渠道独立执行，已经拿到的结果不会因单个渠道失败而丢失。";
  taskError();
}

function openTaskDialog() {
  if (!state.config) return toast("配置还在加载，请稍后再试", true);
  state.taskRunning = false;
  renderTaskDefaults();
  showTaskStep("resume");
  $("#close-task").disabled = false;
  $("#task-dialog").showModal();
  setTimeout(() => $("#task-resume-file").focus(), 50);
}

function resetLoadingStages() {
  $$(".loading-stages li").forEach(item => item.className = "");
}

function setLoadingStage(stage, message) {
  const order = ["resume", "config", "discover", "evaluate"];
  const index = order.indexOf(stage);
  $$(".loading-stages li").forEach(item => {
    const itemIndex = order.indexOf(item.dataset.stage);
    item.classList.toggle("complete", itemIndex < index);
    item.classList.toggle("active", itemIndex === index);
  });
  $("#task-loading-message").textContent = message;
}

function taskConfigPayload() {
  const config = JSON.parse(JSON.stringify(state.config));
  const titles = parseList($("#task-titles").value);
  config.preferences.target_titles = titles;
  config.preferences.locations = parseList($("#task-locations").value);
  config.preferences.excluded_keywords = parseList($("#task-excluded").value);
  config.preferences.blacklisted_companies = parseList($("#task-blacklisted").value);
  config.preferences.employment_types = selectedValues("task-employment");
  config.preferences.work_modes = selectedValues("task-work-mode");
  config.preferences.workload_preference = $("#task-workload-preference").value;
  config.preferences.role_boundary_preference = $("#task-role-boundary-preference").value;
  config.preferences.growth_priority = $("#task-growth-priority").value;
  config.preferences.stability_priority = $("#task-stability-priority").value;
  config.preferences.culture_preferences = parseList($("#task-culture-preferences").value);
  config.preferences.community_risk_avoidances = parseList($("#task-community-risk-avoidances").value);
  config.preferences.minimum_salary = optionalNumber($("#task-min-salary").value);
  config.preferences.max_experience_gap = Number($("#task-max-gap").value || 2);
  config.preferences.published_within_days = optionalNumber($("#task-recent-days").value);
  config.preferences.unknown_field_policy = $("#task-unknown-policy").value;
  const preset = $('input[name="task-strategy"]:checked')?.value || "balanced";
  config.preferences.strategy_mix = {...STRATEGY_PRESETS[preset]};
  config.preferences.strategy_mode = preset;
  config.preferences.boss_keywords = [...titles];
  config.preferences.official_keywords = [...titles];
  return config;
}

async function startTask() {
  const titles = parseList($("#task-titles").value);
  const channels = selectedValues("task-channel");
  if (!titles.length) {
    taskError("请至少填写一个岗位名称或方向。");
    $("#task-titles").focus();
    return;
  }
  if (!channels.length) {
    taskError("请至少选择一个已就绪的岗位渠道。");
    $("#task-channel-options").scrollIntoView({behavior: "smooth", block: "center"});
    return;
  }
  const resumeFile = $("#task-resume-file").files[0];
  try {
    validateResumeFile(resumeFile);
    state.taskRunning = true;
    $("#close-task").disabled = true;
    resetLoadingStages();
    showTaskStep("loading");
    setLoadingStage("resume", resumeFile ? "正在验证并替换当前简历…" : "正在沿用当前简历…");
    if (resumeFile) {
      const resume = await uploadResumeFile(resumeFile);
      state.config = resume.config;
      state.resume = {
        configured: true, available: true, filename: resume.filename, path: resume.path,
        profile_source: resume.config.candidate.profile_source, text_available: resume.extracted_characters > 0
      };
    }
    setLoadingStage("config", "正在保存本次岗位条件与策略…");
    state.config = await api("/api/config", {method: "PUT", body: JSON.stringify(taskConfigPayload())});
    localStorage.setItem("job-agent-selected-channels", JSON.stringify(channels));
    setLoadingStage("discover", "正在从所选渠道获取并标准化岗位…");
    const discovery = await api("/api/run/discover", {method: "POST", body: JSON.stringify({channels})});
    setLoadingStage("evaluate", "正在执行硬规则与能力关系评估…");
    const evaluation = await api("/api/run/evaluate", {method: "POST", body: "{}"});
    $$('.loading-stages li').forEach(item => {
      item.classList.remove("active");
      item.classList.add("complete");
    });
    $("#task-loading-message").textContent = `完成：新增 ${discovery.sources?.reduce((sum, item) => sum + (item.created || 0), 0) || 0} 个岗位，评估 ${evaluation.evaluated || 0} 个。`;
    await load();
    $("#task-dialog").close();
    switchView("recommendations");
    renderRunResult(discovery);
    toast(discovery.completed > 0 ? "岗位已获取并完成评估" : discovery.message, discovery.completed === 0);
  } catch (error) {
    showTaskStep("rules");
    taskError(error.message);
    toast(error.message, true);
  } finally {
    state.taskRunning = false;
    $("#close-task").disabled = false;
  }
}

function openChannelDialog(mode = "discover") {
  state.channelDialogMode = mode;
  const previous = JSON.parse(localStorage.getItem("job-agent-selected-channels") || "[]");
  const readyIds = state.channels.filter(item => item.ready).map(item => item.id);
  const selected = previous.filter(id => readyIds.includes(id));
  const defaults = selected.length ? selected : readyIds;
  $("#channel-options").innerHTML = state.channels.length ? state.channels.map(channel => `
    <label class="channel-option ${channel.ready ? "" : "disabled"}">
      <input type="checkbox" name="source" value="${escapeHtml(channel.id)}" ${defaults.includes(channel.id) ? "checked" : ""} ${channel.ready ? "" : "disabled"}>
      <div class="channel-option-main"><div><b>${escapeHtml(channel.name)}</b><span class="status-dot ${healthClass(channel.health)}">${escapeHtml(channel.health_label)}</span></div>
      <small>${escapeHtml(channel.type === "boss" ? "BOSS 浏览器渠道" : `官网 / ATS · ${strategyLabel(channel.strategy)} · ${autofillLabel(channel.capabilities)}`)}</small>
      <p>${channel.ready ? `关键词：${escapeHtml((channel.keywords || []).join("、") || "未限制")}` : escapeHtml((channel.missing || []).join("、") || "配置不完整")}</p></div>
    </label>
  `).join("") : `<div class="empty-state"><b>没有可配置渠道</b><span>请先到配置页面添加。</span></div>`;
  $("#start-discovery").disabled = readyIds.length === 0;
  $("#start-discovery").textContent = mode === "cycle" ? "抓取并继续评估" : "开始抓取";
  $("#channel-dialog").showModal();
  bindGoConfig();
}

function renderRunResult(result) {
  const panel = $("#run-result");
  const sources = result.sources || [];
  panel.hidden = false;
  panel.className = `run-result ${result.completed > 0 ? "success" : "warning"}`;
  panel.innerHTML = `<div><b>${escapeHtml(result.message || "抓取任务已完成")}</b><span>${sources.map(item => `${item.source}：${item.records ?? 0} 条（${item.status}）`).join("；") || "没有执行任何渠道"}</span></div><button class="icon-button" aria-label="关闭">×</button>`;
  panel.querySelector("button").onclick = () => panel.hidden = true;
}

async function startSelectedDiscovery() {
  const selected = $$('#channel-options input[name="source"]:checked').map(item => item.value);
  if (!selected.length) {
    toast("请至少选择一个已启用渠道", true);
    return;
  }
  localStorage.setItem("job-agent-selected-channels", JSON.stringify(selected));
  const button = $("#start-discovery");
  button.disabled = true;
  button.textContent = "抓取中…";
  try {
    const result = await api("/api/run/discover", {method: "POST", body: JSON.stringify({channels: selected})});
    $("#channel-dialog").close();
    switchView("jobs");
    renderRunResult(result);
    if (state.channelDialogMode === "cycle") {
      await api("/api/run/evaluate", {method: "POST", body: "{}"});
      await api("/api/run/plan-all", {method: "POST", body: "{}"});
    }
    toast(result.message || "抓取完成", result.completed === 0);
    await load();
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "开始抓取";
  }
}

async function saveBasicConfig() {
  try {
    const config = JSON.parse(JSON.stringify(state.config));
    config.candidate.name = $("#cfg-name").value.trim();
    config.candidate.headline = $("#cfg-headline").value.trim();
    config.candidate.years_experience = Number($("#cfg-years").value || 0);
    config.candidate.education = $("#cfg-education").value;
    config.candidate.skills = parseList($("#cfg-skills").value);
    config.candidate.profile_source = "manual";
    config.candidate.resume_path = $("#cfg-resume").value.trim();
    config.preferences.target_titles = parseList($("#cfg-target-titles").value);
    config.preferences.locations = parseList($("#cfg-locations").value);
    config.preferences.excluded_keywords = parseList($("#cfg-excluded").value);
    config.preferences.blacklisted_companies = parseList($("#cfg-blacklisted").value);
    config.preferences.employment_types = selectedValues("cfg-employment");
    config.preferences.work_modes = selectedValues("cfg-work-mode");
    config.preferences.workload_preference = $("#cfg-workload-preference").value;
    config.preferences.role_boundary_preference = $("#cfg-role-boundary-preference").value;
    config.preferences.growth_priority = $("#cfg-growth-priority").value;
    config.preferences.stability_priority = $("#cfg-stability-priority").value;
    config.preferences.culture_preferences = parseList($("#cfg-culture-preferences").value);
    config.preferences.community_risk_avoidances = parseList($("#cfg-community-risk-avoidances").value);
    config.preferences.minimum_salary = optionalNumber($("#cfg-min-salary").value);
    config.preferences.max_experience_gap = Number($("#cfg-max-gap").value || 2);
    config.preferences.published_within_days = optionalNumber($("#cfg-recent-days").value);
    config.preferences.unknown_field_policy = $("#cfg-unknown-policy").value;
    config.preferences.company_tiers = config.preferences.company_tiers || {};
    config.preferences.company_tiers["优先"] = parseList($("#cfg-tier-priority").value);
    config.preferences.company_tiers["可接受"] = parseList($("#cfg-tier-acceptable").value);
    config.preferences.company_tiers["不投"] = parseList($("#cfg-tier-skip").value);
    config.preferences.boss_daily_limit = Number($("#cfg-boss-limit").value || 0);
    config.preferences.official_daily_limit = Number($("#cfg-official-limit").value || 0);
    config.preferences.boss_keywords = parseList($("#cfg-boss-keywords").value);
    config.preferences.official_keywords = parseList($("#cfg-official-keywords").value);
    config.preferences.auto_send_resume_after_reply = $("#cfg-auto-resume").checked;
    config.boss.enabled = $("#cfg-boss-enabled").checked;
    config.boss.city_name = $("#cfg-boss-city-name").value.trim();
    config.boss.city_code = $("#cfg-boss-city-code").value.trim();
    config.greetings.default = $("#cfg-greeting").value.trim();
    config.fixed_answers.name = config.candidate.name;
    config.fixed_answers.phone = $("#cfg-answer-phone").value.trim();
    config.fixed_answers.email = $("#cfg-answer-email").value.trim();
    config.fixed_answers.current_city = $("#cfg-answer-city").value.trim();
    config.fixed_answers.graduation_year = $("#cfg-answer-graduation").value.trim();
    config.mail.enabled = $("#cfg-mail-enabled").checked;
    config.mail.host = $("#cfg-mail-host").value.trim();
    config.mail.username = $("#cfg-mail-username").value.trim();
    state.config = await api("/api/config", {method: "PUT", body: JSON.stringify(config)});
    toast("用户配置已验证并保存");
    await load();
  } catch (error) {
    toast(error.message, true);
  }
}

async function saveJsonConfig() {
  try {
    const parsed = JSON.parse($("#config-editor").value);
    state.config = await api("/api/config", {method: "PUT", body: JSON.stringify(parsed)});
    toast("高级配置已验证并保存");
    await load();
  } catch (error) {
    toast(error.message, true);
  }
}

async function uploadConfigResume() {
  const file = $("#cfg-resume-file").files[0];
  if (!file) return;
  const button = $("#cfg-resume-upload");
  button.disabled = true;
  button.textContent = "正在替换…";
  try {
    const result = await uploadResumeFile(file);
    state.config = result.config;
    state.resume = {
      configured: true, available: true, filename: result.filename, path: result.path,
      profile_source: result.config.candidate.profile_source, text_available: result.extracted_characters > 0
    };
    setValue("cfg-resume", result.path);
    $("#cfg-resume-name").textContent = result.filename;
    $("#cfg-resume-path").textContent = result.path;
    $("#cfg-resume-file").value = "";
    toast(result.profile_updated ? "当前简历已替换，候选人档案已从简历更新" : "简历已替换；未识别到结构化档案，请核对候选人配置");
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.textContent = "替换当前简历";
    button.disabled = !$("#cfg-resume-file").files.length;
  }
}

async function simpleAction(name) {
  try {
    let result;
    if (name === "seed") result = await api("/api/demo/seed", {method: "POST", body: "{}"});
    if (name === "evaluate") result = await api("/api/run/evaluate", {method: "POST", body: "{}"});
    if (name === "plan-all") {
      result = await api("/api/run/plan-all", {method: "POST", body: "{}"});
    }
    if (name === "dry-run") {
      result = await api("/api/run/execute-all", {method: "POST", body: JSON.stringify({live: false})});
    }
    if (name === "replies") result = await api("/api/run/replies", {method: "POST", body: JSON.stringify({send_resume: false})});
    if (name === "receipts") result = await api("/api/run/receipts", {method: "POST", body: "{}"});
    toast(`完成：${JSON.stringify(result).slice(0, 160)}`);
    await load();
  } catch (error) {
    toast(error.message, true);
  }
}

async function liveRun() {
  try {
    const result = await api("/api/run/execute-all", {method: "POST", body: JSON.stringify({live: true})});
    toast(`真实执行完成：共处理 ${result.processed} 条`);
    await load();
  } catch (error) {
    toast(error.message, true);
  }
}

$$(".nav-item").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));

$$('[data-action]').forEach(button => button.addEventListener("click", () => {
  const action = button.dataset.action;
  if (action === "discover") return openChannelDialog("discover");
  if (action === "live-run") {
    $("#confirm-text").value = "";
    return $("#confirm-dialog").showModal();
  }
  simpleAction(action);
}));

$("#channel-dialog").addEventListener("click", event => {
  if (event.target.matches("[data-close-channel]")) $("#channel-dialog").close();
});
$("#start-discovery").addEventListener("click", startSelectedDiscovery);
$("#confirm-dialog").addEventListener("close", () => {
  if ($("#confirm-dialog").returnValue === "confirm" && $("#confirm-text").value === "真实执行") liveRun();
  else if ($("#confirm-dialog").returnValue === "confirm") toast("确认文字不正确", true);
});
$("#refresh").addEventListener("click", () => load().catch(error => toast(error.message, true)));
$$('[data-open-task]').forEach(button => button.addEventListener("click", openTaskDialog));
$("#task-next").addEventListener("click", async () => {
  const button = $("#task-next");
  try {
    const file = $("#task-resume-file").files[0];
    validateResumeFile(file);
    if (!file && !state.resume.available) {
      taskError("首次使用需要上传一份 PDF 或 DOCX 简历。");
      return;
    }
    if (file) {
      button.disabled = true;
      button.textContent = "正在本地解析…";
      const result = await uploadResumeFile(file);
      state.config = result.config;
      state.resume = {
        configured: true, available: true, filename: result.filename, path: result.path,
        profile_source: result.config.candidate.profile_source, text_available: result.extracted_characters > 0
      };
      $("#task-resume-file").value = "";
      renderTaskResume();
      toast(result.profile_updated ? "已从简历更新技能、年限或学历，请稍后到配置页核对" : "未从简历识别到档案信息，将使用手动候选人配置");
    }
    showTaskStep("rules");
    if (!state.config?.candidate?.skills?.length) {
      taskError("尚未识别或填写能力关键词；当前可继续使用基础规则，建议先到配置页补充候选人档案。");
    }
    setTimeout(() => $("#task-titles").focus(), 50);
  } catch (error) {
    taskError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "下一步";
  }
});
$("#task-back").addEventListener("click", () => showTaskStep("resume"));
$("#task-start").addEventListener("click", startTask);
$("#task-cancel").addEventListener("click", () => {
  if (!state.taskRunning) $("#task-dialog").close();
});
$("#close-task").addEventListener("click", () => {
  if (!state.taskRunning) $("#task-dialog").close();
});
$("#task-dialog").addEventListener("cancel", event => {
  if (state.taskRunning) event.preventDefault();
});
$("#task-resume-file").addEventListener("change", () => {
  try {
    validateResumeFile($("#task-resume-file").files[0]);
    taskError();
  } catch (error) {
    taskError(error.message);
    $("#task-resume-file").value = "";
  }
  renderTaskResume();
});
$("#task-advanced-rules").addEventListener("toggle", event => {
  event.currentTarget.querySelector(".summary-action").textContent = event.currentTarget.open ? "收起" : "展开设置";
});
$("#job-search").addEventListener("input", renderJobs);
$("#job-status-filter").addEventListener("change", renderJobs);
$("#save-basic-config").addEventListener("click", saveBasicConfig);
$("#save-json-config").addEventListener("click", saveJsonConfig);
$("#cfg-resume-file").addEventListener("change", () => {
  const file = $("#cfg-resume-file").files[0];
  try {
    validateResumeFile(file);
    $("#cfg-resume-upload").disabled = !file;
    if (file) $("#cfg-resume-path").textContent = `已选择 ${file.name}，点击按钮后替换当前简历。`;
  } catch (error) {
    $("#cfg-resume-file").value = "";
    $("#cfg-resume-upload").disabled = true;
    toast(error.message, true);
  }
});
$("#cfg-resume-upload").addEventListener("click", uploadConfigResume);
$("#open-advanced-channel").addEventListener("click", () => {
  $("#advanced-config").open = true;
  $("#advanced-config").scrollIntoView({behavior: "smooth", block: "start"});
});
$("#knowledge-import-form").addEventListener("submit", importKnowledge);
$("#knowledge-fetch-form").addEventListener("submit", fetchKnowledge);
$("#knowledge-refresh").addEventListener("click", () => refreshKnowledge().catch(error => toast(error.message, true)));
$("#knowledge-content").addEventListener("input", updateKnowledgeContentCount);
$("#knowledge-source").addEventListener("change", syncKnowledgeSource);
$("#knowledge-fetch-source").addEventListener("change", syncKnowledgeFetchGuidance);

bindGoConfig();
Recommendations.bind({
  retry: refreshRecommendations,
  goToPool: () => switchView("jobs"),
  openTask: openTaskDialog
});
syncKnowledgeSource();
syncKnowledgeFetchGuidance();
load().catch(error => toast(error.message, true));

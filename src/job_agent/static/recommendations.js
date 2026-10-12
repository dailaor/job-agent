/* Evidence-linked job decisions; this view never submits an application. */
window.Recommendations = (() => {
  const local = {data: null, error: "", loading: true, retry: null, goToPool: null};
  const $ = selector => document.querySelector(selector);
  const escape = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
  const asList = value => Array.isArray(value) ? value : [];
  const icon = name => window.JobIcons.icon(name);
  function cleanCopy(value) {
    const template = document.createElement("template");
    template.innerHTML = String(value ?? "").replace(/<(?:br|\/p|\/div|\/li)\s*\/?\s*>/gi, " ");
    template.content.querySelectorAll("script, style, iframe, object, embed").forEach(node => node.remove());
    return (template.content.textContent || "").replace(/\s+/g, " ").trim();
  }
  const safeKey = value => String(value).replace(/[^a-zA-Z0-9_-]/g, "_");
  const sourceLabels = {boss: "BOSS直聘", demo: "演示岗位"};
  const typeLabels = {full_time: "正职", internship: "实习", unknown: "用工未核实"};

  function safeUrl(value) {
    try {
      const url = new URL(String(value));
      return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password ? url.href : "";
    } catch (_) { return ""; }
  }

  function dateLabel(value) {
    const date = value ? new Date(value) : null;
    return date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString("zh-CN") : "日期未确认";
  }

  function badge(text, tone = "neutral") {
    return `<span class="decision-badge ${tone}">${escape(text)}</span>`;
  }

  function proofLinks(card, ids) {
    const evidence = asList(card.evidence);
    const valid = new Set(evidence.map(item => String(item.id)));
    const linked = [...new Set(asList(ids).filter(id => valid.has(String(id))))];
    if (!linked.length) return "";
    const number = evidence.findIndex(item => String(item.id) === String(linked[0])) + 1;
    const label = linked.length > 1 ? `依据 ${linked.length} 条` : `依据 ${number}`;
    return `<button class="proof-link" type="button" data-proof-job="${escape(card.job_id)}" data-proof-id="${escape(linked[0])}" data-proof-ids="${escape(linked.join(","))}" aria-label="查看这条结论的 ${linked.length} 条证据">${label}${icon("chevron")}</button>`;
  }

  function factList(card, values, fallback, tone = "") {
    const items = asList(values);
    return items.length ? `<ul class="decision-facts ${tone ? "with-signs" : ""}">${items.map(item =>
      `<li>${tone ? `<span class="fact-sign ${tone}">${icon(tone === "positive" ? "check" : "warning")}</span>` : ""}<div><span>${escape(cleanCopy(typeof item === "string" ? item : item.text))}</span>${proofLinks(card, item.evidence_ids)}</div></li>`
    ).join("")}</ul>` : `<p class="decision-missing">${escape(fallback)}</p>`;
  }

  function fieldRows(card) {
    return `<dl class="decision-fields">${asList(card.compensation?.fields).map(field =>
      `<div><dt>${escape(field.label)}</dt><dd>${escape(cleanCopy(field.value || "未披露"))}${proofLinks(card, field.evidence_ids)}</dd></div>`
    ).join("")}</dl>`;
  }

  function evidenceItem(card, evidence) {
    const scope = evidence.scope || {};
    const scopeText = [scope.company || "公司未核实", scope.role_family || "岗位族未核实", typeLabels[scope.employment_type] || "用工未核实", scope.business_unit ? `团队：${scope.business_unit}` : "团队未核实", scope.city ? `城市：${scope.city}` : "城市未核实"].join(" · ");
    const url = safeUrl(evidence.url);
    const relevance = evidence.type === "jd" ? "岗位披露" : evidence.relevance === "direct" ? "同作用域经历" : evidence.relevance === "context" ? "背景参考" : "适用性待核实";
    return `<li class="evidence-entry" id="proof-${safeKey(card.job_id)}-${safeKey(evidence.id)}" tabindex="-1">
      <div class="evidence-entry-heading"><strong>${escape(evidence.source_label || evidence.source)}</strong>${badge(evidence.inference ? "本地规则核对" : relevance, evidence.relevance === "direct" ? "positive" : "neutral")}</div>
      <p class="evidence-title">${escape(evidence.title)}</p>
      <blockquote>${escape(cleanCopy(evidence.excerpt))}</blockquote>
      <p class="evidence-scope">${escape(scopeText)}</p>
      <div class="evidence-origin"><span>${escape(dateLabel(evidence.date))}</span>${url ? `<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">查看原始来源</a>` : '<span>暂无可核对链接</span>'}</div>
      ${asList(evidence.limitations).length ? `<p class="evidence-limit">${asList(evidence.limitations).map(escape).join("；")}</p>` : ""}
    </li>`;
  }

  function renderCard(card) {
    const id = safeKey(card.job_id);
    const decision = card.decision || {};
    const eligibility = card.eligibility || {};
    const ability = card.ability || {};
    const experience = asList(card.experience);
    const evidence = asList(card.evidence);
    const url = safeUrl(card.apply_url || card.url);
    const tone = decision.status === "recommend" ? "positive" : "caution";
    const source = sourceLabels[card.source] || (card.source?.startsWith("official:") ? "招聘官网" : card.source || "来源未确认");
    const monogram = Array.from(card.company || "岗")[0];
    const isKnownSalary = card.compensation?.status === "known";
    const shownTitle = card.is_demo ? String(card.title || "").replace(/\s*（演示(?:·[^）]+)?）$/, "") : card.title;
    return `<article class="job-decision-card decision-${tone}" aria-labelledby="decision-title-${id}">
      <div class="decision-card-heading">
        <div class="decision-identity"><span class="company-monogram" aria-hidden="true">${escape(monogram)}</span><div><h3 id="decision-title-${id}">${escape(shownTitle)}${card.is_demo ? badge("演示") : ""}</h3><p>${escape(card.company)}<span class="identity-dot" aria-hidden="true">·</span>${escape(card.location || "地点未披露")}</p></div></div>
        <div class="decision-heading-actions">${badge(decision.label || "先核实信息", tone)}${url ? `<a class="button primary" href="${escape(url)}" target="_blank" rel="noopener noreferrer">查看原岗位${icon("external")}</a>` : '<span class="decision-missing">原岗位链接待核实</span>'}</div>
      </div>
      <div class="decision-source-line"><span>${escape(source)}</span><span>${escape(card.evidence_summary?.label || "证据待补充")}</span><span class="decision-summary">${escape(decision.summary)}</span></div>
      <div class="decision-readouts">
        <div class="readout-salary">${icon("money")}<dl><dt>薪资待遇</dt><dd class="${isKnownSalary ? "salary-known" : "salary-unknown"}">${escape(card.compensation?.label || "未披露")}</dd></dl></div>
        <div>${icon("shield")}<dl><dt>可投性</dt><dd>${escape(eligibility.label || "门槛待核实")}</dd></dl></div>
        <div>${icon("chart")}<dl><dt>能力匹配</dt><dd>${escape(ability.label || "依据不足")}<small>依据档案与 JD</small></dd></dl></div>
        <div class="readout-qualification">${icon("info")}<p>提交资格仍需核实</p></div>
      </div>
      <div class="decision-body">
        <div class="decision-arguments">
          <section class="decision-reasons"><h4>值得了解的理由</h4>${factList(card, card.reasons, "暂无足够依据支持推荐，建议先补充档案与岗位事实。", "positive")}</section>
          <section class="decision-risks"><h4>风险与待确认</h4>${factList(card, card.risks, "仍需确认实际薪资、工作安排与招聘门槛。", "caution")}</section>
        </div>
        <section class="experience-preview" aria-label="六组工作体验"><h4>工作体验 <span>基于已知信息</span></h4><dl>${experience.map(item => {
          const fact = asList(item.facts)[0];
          const text = fact ? cleanCopy(fact.text).replace(/^(?:JD 披露：|同作用域社区样本：)/, "") : "待核实";
          const excerpt = text.length > 72 ? `${text.slice(0, 72)}…` : text;
          const experienceIcons = {time: "clock", pace: "pace", responsibility: "briefcase", culture: "users", growth: "growth", stability: "shield"};
          return `<div class="${fact ? "has-experience-fact" : "experience-unknown"}"><dt>${icon(experienceIcons[item.key] || "document")}${escape(item.label)}</dt><dd>${escape(excerpt)}${fact ? proofLinks(card, fact.evidence_ids) : ""}</dd></div>`;
        }).join("")}</dl><p class="experience-note">${icon("info")}披露或个人样本，实际安排仍需确认</p></section>
      </div>
      <details class="decision-details" id="decision-details-${id}">
        <summary>${icon("book")}<div><strong>待遇细项与决策依据</strong><small>岗位披露 / 个人经历，保留来源与时间</small></div><span>${evidence.length} 条来源记录</span>${icon("chevron")}</summary>
        <div class="decision-details-body">
          <section><h4>薪资结构</h4>${fieldRows(card)}</section>
          <section><h4>门槛与能力依据</h4>${factList(card, eligibility.reasons, "未发现已识别的硬条件冲突。")}${asList(eligibility.unknowns).length ? `<p class="decision-missing">待确认：${asList(eligibility.unknowns).map(escape).join("；")}</p>` : ""}<p>${escape(ability.summary)}</p>${asList(ability.matched).length ? `<p>已关联能力：${asList(ability.matched).map(escape).join("、")}</p>` : ""}${asList(ability.missing).length ? `<p>待补能力：${asList(ability.missing).map(escape).join("、")}</p>` : ""}</section>
          <section><h4>工作体验依据</h4><div class="experience-facts">${experience.map(item => `<div><h5>${escape(item.label)}</h5>${factList(card, item.facts, "没有直接适用的工作体验证据。")}${asList(item.unknowns).length ? `<p class="decision-missing">${asList(item.unknowns).map(escape).join("；")}</p>` : ""}</div>`).join("")}</div></section>
          <section><h4>建议向 HR 确认</h4><ol class="decision-questions">${asList(card.questions).map(question => `<li>${escape(question)}</li>`).join("")}</ol></section>
          <section class="evidence-chain"><h4>证据链</h4><p class="decision-missing">岗位披露与个人经历各自保留来源；背景参考不能证明当前团队情况。</p>${evidence.length ? `<ol class="evidence-list">${evidence.map(item => evidenceItem(card, item)).join("")}</ol>` : '<p class="decision-missing">暂无可回查证据，请先打开原岗位核对。</p>'}</section>
        </div>
      </details>
      <footer class="decision-card-footer"><span>${escape(card.next_step || (decision.status === "recommend" ? "了解岗位后，再决定是否投递" : "先确认未知信息，再决定是否投递"))}</span></footer>
    </article>`;
  }

  function render() {
    const container = $("#recommendation-results");
    const overview = $("#recommendation-overview");
    container.setAttribute("aria-busy", String(local.loading));
    if (local.loading) {
      overview.textContent = "正在整理岗位与证据…";
      container.innerHTML = '<div class="recommendation-empty" role="status"><h3>正在核对岗位决策依据</h3><p>读取本机的岗位和有效情报，整理理由、风险与待确认信息。</p></div>';
      return;
    }
    if (local.error) {
      overview.textContent = "推荐暂时无法更新，岗位池仍可查看。";
      container.innerHTML = `<div class="recommendation-empty" role="alert"><h3>未能生成推荐卡</h3><p>${escape(local.error)}</p><button class="button primary" data-recommendation-retry>重新加载</button><button class="button ghost" data-recommendation-pool>查看岗位池</button></div>`;
      return;
    }
    const data = local.data || {items: [], summary: {}};
    const summary = data.summary || {};
    const query = $("#recommendation-search").value.trim().toLowerCase();
    const status = $("#recommendation-status").value;
    const directOnly = $("#recommendation-evidence-only").checked;
    const visible = asList(data.items).filter(card => card.default_visible !== false);
    const filtered = visible.filter(card =>
      (!query || `${card.title} ${card.company} ${card.location}`.toLowerCase().includes(query)) &&
      (!status || card.decision?.status === status) &&
      (!directOnly || Number(card.evidence_summary?.experience_direct || 0) > 0)
    );
    $("#recommendation-reset").hidden = !(query || status || directOnly);
    overview.innerHTML = `<span><strong>${escape(summary.recommended || 0)}</strong> 个优先了解</span><span><strong>${escape(summary.verify || 0)}</strong> 个先核实</span><span><strong>${escape(summary.excluded || 0)}</strong> 个未进入推荐</span><button class="recommendation-pool-link" type="button" data-recommendation-pool>全部岗位在岗位池</button>`;
    $("#recommendation-order").textContent = `显示 ${filtered.length} 个候选 · 按门槛与直接适用的决策证据优先整理，不代表录用概率。`;
    if (!filtered.length) {
      const hasItems = visible.length > 0;
      container.innerHTML = `<div class="recommendation-empty"><h3>${hasItems ? "没有符合筛选的推荐" : summary.total ? "当前没有进入推荐的岗位" : "开始建立你的岗位候选清单"}</h3><p>${hasItems ? "试试清除筛选。缺少体验证据的岗位仍可查看，但会明确保留待核实信息。" : summary.total ? "当前岗位可能有硬条件冲突、已过期或重复。你可以在岗位池查看具体情况，或调整求职条件。" : "先获取岗位，卡片就会整理可投门槛、值得了解的理由、风险与证据。"}</p><button class="button primary" ${hasItems ? 'data-recommendation-clear' : 'data-open-task'}>${hasItems ? "清除筛选" : "寻找匹配岗位"}</button><button class="button ghost" data-recommendation-pool>查看岗位池</button></div>`;
      return;
    }
    container.innerHTML = filtered.map(renderCard).join("");
  }

  function clearFilters() {
    $("#recommendation-search").value = "";
    $("#recommendation-status").value = "";
    $("#recommendation-evidence-only").checked = false;
    render();
    $("#recommendation-search").focus();
  }

  function bind({retry, goToPool, openTask}) {
    local.retry = retry;
    local.goToPool = goToPool;
    $("#recommendation-search").addEventListener("input", render);
    $("#recommendation-status").addEventListener("change", render);
    $("#recommendation-evidence-only").addEventListener("change", render);
    $("#recommendation-reset").addEventListener("click", clearFilters);
    $("#view-recommendations").addEventListener("click", event => {
      const button = event.target.closest("button");
      if (!button) return;
      if (button.hasAttribute("data-recommendation-retry")) retry();
      if (button.hasAttribute("data-recommendation-pool")) goToPool();
      if (button.hasAttribute("data-recommendation-clear")) clearFilters();
      if (button.hasAttribute("data-open-task") && button.closest(".recommendation-empty")) openTask();
      if (button.hasAttribute("data-proof-id")) {
        const details = $(`#decision-details-${safeKey(button.dataset.proofJob)}`);
        if (details) details.open = true;
        if (details) {
          const linked = new Set((button.dataset.proofIds || button.dataset.proofId).split(","));
          details.querySelectorAll(".evidence-entry").forEach(entry => {
            const itemId = entry.id.slice(`proof-${safeKey(button.dataset.proofJob)}-`.length);
            entry.classList.toggle("is-linked", [...linked].some(value => safeKey(value) === itemId));
          });
        }
        const entry = $(`#proof-${safeKey(button.dataset.proofJob)}-${safeKey(button.dataset.proofId)}`);
        if (entry) { entry.scrollIntoView({behavior: "auto", block: "center"}); entry.focus({preventScroll: true}); }
      }
    });
    render();
  }

  return {
    bind,
    setData(data) { Object.assign(local, {data, loading: false, error: ""}); render(); },
    setError(error) { Object.assign(local, {error: error || "请检查本地服务是否正在运行。", loading: false}); render(); },
    setLoading() { Object.assign(local, {loading: true, error: ""}); render(); }
  };
})();

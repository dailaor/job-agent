# 维护手册

这份文档回答三个问题：改一项产品行为应该去哪里、改完要验证什么、怎样避免把渠道特例继续堆进主流程。

系统边界、组件关系、数据流、领域状态和扩展契约统一记录在 [技术架构](ARCHITECTURE.md)；本文只保留面向日常修改的代码地图和验证清单。

## 用户主流程

```mermaid
flowchart TD
    A["首页：开始智能匹配"] --> B{"已有可用简历？"}
    B -->|"是"| C["沿用当前简历"]
    B -->|"否"| D["上传 PDF 或 DOCX"]
    C --> E["岗位名称与地点"]
    D --> E
    E --> F["按需设置更多硬条件"]
    F --> G["选择冲刺 / 均衡 / 保底策略"]
    G --> H["选择本次已就绪渠道"]
    H --> I["各渠道独立采集"]
    I --> J["标准化与跨渠道去重"]
    J --> K["硬规则过滤"]
    K --> KA["可选：岗位情报两路检索"]
    KA --> L["双向评分、能力关系与策略排序"]
    L --> M["统一岗位池"]
    M --> N["跳转原始官网，由用户确认投递"]
    N --> O["投递台账与审计记录"]
```

再次使用时，简历上传不是必填项；没有选择新文件就沿用 `candidate.resume_path` 指向的本地副本。选择新文件后，服务端只保留一个 `current.pdf` 或 `current.docx`，并把可提取文本写入 `current.txt`。新文件、文本和配置更新失败时会恢复旧版本。

## 代码地图

| 目标 | 主要文件 | 维护边界 |
|---|---|---|
| 修改配置字段及校验 | `src/job_agent/config.py` | 新字段必须有默认值，保证旧 `config.json` 可读取 |
| 修改岗位/候选人数据 | `src/job_agent/models.py` | 同步检查 SQLite 行转换与前端字段 |
| 修改硬规则、能力分类、评分 | `src/job_agent/matching.py` | 硬规则与软排序保持分层；补充 `tests/test_matching.py` |
| 修改岗位情报准入、切块、向量或检索 | `src/job_agent/knowledge/`、`docs/RAG_KNOWLEDGE.md` | 保持一帖一父文档、两路主题隔离、硬规则前置；补 `tests/test_knowledge.py` |
| 接入 embedding 或 LLM 评分 | `knowledge/embeddings.py`、`scoring.py`、`orchestrator.py` | 通过 Protocol 注入；provider 名版本化；失败回退规则评分 |
| 修改简历解析、上传与替换 | `src/job_agent/resume.py`、`service.py`、`web.py`、`static/app.js` | 只接受 PDF/DOCX、10 MB；解析先于替换；补 `tests/test_service.py` |
| 新增或维护渠道 | `src/job_agent/connectors/campus.py`、`official.py`、`registry.py`、`config.example.json` | 内置校园协议集中在 `campus.py`；普通新渠道无需改编排器，专用多阶段写流程才增加明确执行器 |
| 修改采集编排 | `src/job_agent/orchestrator.py` | 负责通用调度、持久化和健康状态，不解析具体站点 |
| 修改本地 API | `src/job_agent/web.py` | 保持 JSON 错误结构 `{error, message}` |
| 修改页面流程 | `src/job_agent/static/` | 无构建步骤；同时验证键盘、桌面和移动宽度 |
| 修改数据表和台账 | `src/job_agent/database.py` | 迁移必须向前兼容已有本地数据库 |
| 修改便携包启动 | `src/job_agent/launcher.py`、`scripts/build_portable.ps1` | 用户数据固定写入程序旁的 `data/` |

## 分层关系

```text
浏览器页面
  ↓ JSON API
AgentService（配置、简历、本地查询）
  ↓
JobAgent（通用编排） ── ChannelRegistry（渠道注册）
  ↓               ↘          ↓
ScoringPort     KnowledgeService   具体 Connector
  ↓               ↓          ↓
matching.py    knowledge/*    外部招聘站
          ↘       ↓
           Database / SQLite
```

- `web.py` 不应包含业务判断，只负责路由、请求解析和错误码。
- `service.py` 负责跨配置和文件系统的协调操作；简历替换使用临时文件与失败回滚，但文件系统和 `config.json` 不是数据库式单事务，异常退出后的恢复逻辑必须保留测试。
- `orchestrator.py` 的发现、校验、评估和清单生成只认 `ChannelAdapter`。内置 BOSS 与官网保留不同执行协议；普通新渠道通过可选 `submit()` 接口接入，不能继续按新渠道 ID 堆分支。
- Connector 只产出标准 `Job`；空壳页面、搜索入口和无法验证的摘要不能作为岗位。
- `matching.py` 先返回硬规则原因，再做能力关系和排序。策略配额不能改变硬规则结论。
- `KnowledgeService` 只为通过硬规则的岗位生成 `EvidenceBundle`。当前规则评分忽略证据；未来 LLM 也不得用社区文本翻转硬拒绝。
- 新知识来源通过 `SourceRegistry`，新 embedding 通过 `EmbeddingProvider`，不得把平台或模型特例堆进编排器。

## 本地数据

便携包默认结构：

```text
JobAgent/
├─ JobAgent.exe
├─ docs/
└─ data/
   ├─ config.json
   ├─ job-agent.sqlite3
   └─ resumes/
      ├─ current.pdf 或 current.docx
      └─ current.txt
```

岗位情报文档、主题块、向量和岗位证据关系同样保存在 `job-agent.sqlite3` 的独立 `knowledge_*` / `evaluation_evidence` 表中；默认不保存整篇社区原文。

源代码运行时，默认数据位置由命令行参数决定。不要把 `data/`、真实简历、Cookie、Token、邮箱密码或 SQLite 文件提交到 Git。

## 配置兼容原则

1. 新增 dataclass 字段时提供安全默认值。
2. `config_from_dict` 必须能读取旧配置；删除或重命名字段需要显式迁移。
3. 保存配置前调用 `validate()`；配置文件采用同目录临时文件替换，避免半写入。
4. API 密钥只能通过环境变量或未来的本地密钥存储提供，不写入示例配置。
5. 页面常用字段和高级 JSON 最终都写回同一个 `config.json`，不能维护两套真相。

## 修改后的最低验证

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src tests
```

前端改动还需：

1. 启动 `job-agent serve`。
2. 在桌面宽度完成“沿用简历”和“替换简历”两条路径。
3. 在约 390 px 宽度检查向导、表单、表格和导航是否可操作。
4. 只用键盘完成打开向导、下一步、选择策略和取消。
5. 模拟无渠道、渠道未就绪、单渠道失败、空结果和 API 错误。

岗位情报改动还需：

1. 覆盖 accepted、needs_review、rejected、duplicate 四种准入状态；
2. 验证一帖一父文档、主题块上下文、父子溯源和 PII 脱敏；
3. 验证能力/需求主题隔离、需求侧公司精确匹配和同父文档块上限；
4. 验证硬规则失败时不调用证据提供方，检索失败时规则链继续；
5. 新来源现场冒烟只使用单个明确链接，并检查登录、403/429、验证码、超时和页面壳均停止。

真实网站测试与离线单元测试分开。没有最新页面证据时，不得宣称某个招聘渠道可用。

五个内置校园官网的只读现场冒烟命令：

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe .\scripts\smoke_campus_channels.py --keyword "产品经理"
```

维护者应核对每个渠道返回数量大于 0、示例标题符合关键词、详情 URL 可区分到具体岗位。滴滴 Moka 还要覆盖 Cookie 会话和 AES-CBC 解密；腾讯要确认搜索结果可取得完整详情。站点改变接口时，只把对应渠道标记为失败，不要用列表壳、搜索摘要或旧 fixture 伪装成功。

## Windows 便携包

```powershell
.\scripts\build_portable.ps1
```

脚本会拒绝非 64 位 x86 Python，把中间产物放入 `work/portable/`，最终 ZIP 放入 `outputs/JobAgent-windows-x64.zip`。GitHub tag `v*` 会触发 `.github/workflows/windows-portable.yml`，先跑离线测试再上传 Actions artifact；是否附加到 GitHub Release 由维护者另行执行，当前工作流不会自动创建 Release。

基础便携包包含本地页面、SQLite、规则匹配、岗位情报准入/切块/本地检索、简历解析、通用 JSON API 和五个 `campus_api` 校园官网适配器（含滴滴响应解密依赖），不包含 Playwright 或 Chromium。因此 BOSS 和 `strategy: browser` 的官网在基础 ZIP 中会明确提示缺少浏览器依赖；需要这些实验能力时从源码安装 `.[browser]`。ZIP 必须解压到当前用户可写目录，否则程序无法在同级创建 `data/`。

发布前至少验证：首次启动生成 `data/config.json`、自动打开浏览器、第二次启动保留配置和简历、端口被占用时能选择后续端口。

自动化冒烟测试可设置 `JOB_AGENT_NO_BROWSER=1`，避免启动器弹出默认浏览器；普通用户启动时不要设置该变量。

## 当前明确不做

- 绕过验证码、自动登录或接管用户账号。
- 从搜索入口或 SPA 加载壳推断岗位。
- 对不确定的真实写操作自动重试。
- 把演示数据、规则评分称为大模型判断。
- 批量爬取、自动搜索或翻页获取小红书/牛客社区帖子，或为了访问内容复用 Cookie、Token、密码和绕过验证码/限速。
- 把单篇社区经历直接写成公司或岗位的确定性事实，或让社区证据覆盖硬规则。
- 把基础便携包描述成已经包含 Playwright、登录态或浏览器扩展。
- 把 `autofill.status: planned` 描述成浏览器插件已经实现。
- 在默认用户流程中替用户点击最终官网提交；源码中的实验性写执行器必须显式确认且默认关闭。

## 智能推荐工作卡维护（2026-10-12）

- 后端入口：`src/job_agent/recommendations.py`。可投性、能力、待遇、六组体验、理由/风险与证据分开生成；只读GET不允许偷偷调用付费模型、检索写入或外网。
- 前端入口：`static/recommendations.js`；`app.js` 对接加载/导航；`index.html`和`styles.css`保留控制台风格。证据按钮打开对应details并聚焦出处。筛选结果数量由role=status宣读。
- 证据选择维护时必须覆盖组合学历、前/后置否定、跨样本冲突、面经中的出差、股票算法、日薪/月薪/仅薪资下限、同团队作用域、删帖/过期及12条上限下的direct优先。模型分数不能当录用概率。
- 修改档案、偏好或导入/删除情报后，重新读取推荐；旧REJECTED、旧LLM评分及旧检索快照不能当当前事实。
- 岗位池`#jobs-one-click-apply`保持disabled，未实现自动投递。不要把“生成计划”作为这个按钮的隐含行为。
- 新增测试：`tests/test_recommendations.py`（27项）。完整后端套件当前85项；界面验收`node scripts/test_recommendations_ui.cjs`，需要可用Playwright和Edge，使用`NODE_PATH`指向现有安装，不为项目新增运行依赖。
- 合成预览：`scripts/preview_recommendations.py --port 9876`，数据只放`work/recommendation-preview/`，公司/岗位均有演示标签，不读取真实简历。截图和验收日志放`work/recommendation-review/`。
- 当前`py -3.13`定位旧Python失败，维护者需用明确可用的Python可执行文件；测试执行环境使用Codex bundled Python。产品便携版不依赖全局Python。

## 商业化视觉与公开发布（v0.2.0）

用户确认决策信息完整后，按实际商业网站参考→三张生成效果图→选择横向工作卡→语义前端实现→独立代码/视觉复核的顺序重设计。选定效果图及提示在`docs/assets/design/recommendation-comp.png/json`，README实际截图在`docs/assets/readme/recommendations.png`和`recommendations-mobile.png`，不要把效果图冒充运行截图。

- `commercial.css`在旧`styles.css`之后加载，统一浅色导航/表单/按钮/岗位池并实现横向三分区卡片。更新视觉请维护同一组token，不再叠加多个主题文件。
- `ui-icons.js`是本机几何SVG图标，无新增运行依赖；`brand-icon.svg`保留本地品牌入口。
- 多证据用单一编号入口，`data-proof-ids`保留所有关联ID，点击后展开并高亮同一结论的全部来源，不丢引用。
- `cleanCopy`仅用于HTML格式源摘录：在inert template内去掉脚本/样式等不可见节点，提取文本后仍escape；岗位标题仍逐字转义。不要用innerHTML直接渲染招聘页正文。
- 页内跳转时若旧focus位于将隐藏的view，焦点转到新页标题；导航本身切换保持导航焦点。筛选数量继续polite状态宣读。
- 截图先scrollTo0并等待布局，避免全页捕获中的sticky侧栏落在图片中间；1448×1086与效果图同尺寸核对，另验收1440/1280/390宽度。
- v0.2.0本机85项后端+10组浏览器验收通过；成品测试还必须确认`commercial.css`/`ui-icons.js`可加载及实际浅色侧栏。发布前显式白名单stage，检查配置/简历/db未跟踪，README下载不要指向被忽略的outputs目录。
- v0.2.1修正干净checkout的测试初始化：`work/`被Git忽略，推荐测试必须先自行mkdir再创建临时目录；不能把本机已有目录当作CI前提。发布验收应至少有一次不带任何ignored文件的源码测试。

# 求职 Agent

一个可解压运行、本地优先、固定渠道的开源求职 Agent。核心链路包括：可选替换 PDF/DOCX 简历、岗位采集、跨渠道去重、扩展硬条件、双向匹配评分、冲高/持平/保底清单、原始岗位跳转和本地投递台账。已内置美团、滴滴、快手、腾讯、京东五个校园招聘官网的只读岗位适配器；BYOK/Ollama 和浏览器自动填表属于后续扩展。

## 核心原则

- 能力关系结果包括 `冲高 / 持平 / 保底 / 不投`；其中“不投”是过滤结果，只有前三种会进入清单。
- 排序分开计算“人匹配岗位”和“岗位满足人”：冲刺为 `35% / 65%`，均衡为 `50% / 50%`，保底为 `65% / 35%`；策略还会调整三类岗位的清单配额。
- 公司档位是独立排序维度，不能把“大公司”误判为“冲高”。
- 每日额度只限制最终执行数，不参与岗位策略分类。
- 默认流程只跳转原始岗位页，由用户确认并完成最终投递。
- 不针对岗位改写简历，不生成求职信、开放题答案或未经用户提供的事实。
- 不绕过验证码、不索取账号密码、不规避平台限制。

完整验收边界见 [TASK_ACCEPTANCE.md](TASK_ACCEPTANCE.md)。

## 用户怎么使用

```mermaid
flowchart LR
    A["首页开始匹配"] --> B["沿用或替换简历"]
    B --> C["岗位名称与地点"]
    C --> D["可选的更多硬条件"]
    D --> E["策略与渠道"]
    E --> F["采集、去重、过滤和评估"]
    F --> G["统一岗位池"]
    G --> H["跳转原始官网确认投递"]
    H --> I["投递台账"]
```

再次使用时无需重复上传简历；选择新 PDF/DOCX 才会覆盖本机保存的旧简历。岗位名称和地点始终可见，职位类型、办公方式、最低薪资、经验差距、发布时间、排除词和公司黑名单收在“更多硬性条件”中，并自动沿用上次值。

## Windows 解压即用

从 GitHub Actions artifact（或维护者手动附加的 Release 资产）下载 `JobAgent-windows-x64.zip`，解压到当前用户可写目录后双击 `JobAgent.exe`。程序会在同目录创建 `data/`，并自动打开本地控制台；配置、简历、岗位和台账都保存在这个目录中。

基础 ZIP 包含本地页面、规则匹配、简历解析、SQLite、通用 JSON API 和五个校园官网只读适配器，不包含 Playwright/Chromium。因此 BOSS 和浏览器型官网会提示缺少浏览器依赖；它们需要从源码安装可选依赖。工作流当前只上传 Actions artifact，不会自动创建 GitHub Release。

维护者可运行以下命令构建同样的便携包：

```powershell
.\scripts\build_portable.ps1
```

构建产物位于 `outputs/JobAgent-windows-x64.zip`。直接下载 GitHub Source code 的开发者版本仍需 Python；不开发代码的用户应下载便携包。

## 运行架构

```text
固定渠道采集
  ├─ 美团 / 滴滴 Moka / 快手 / 腾讯 / 京东校园官网（基础便携包）
  ├─ 配置型官网/ATS 公开 JSON API（基础便携包）
  └─ BOSS / 浏览器选择器（源码可选、默认关闭）
        ↓
标准化 → 跨渠道去重 → 时效与硬规则
        ↓
人匹配岗位 + 岗位满足人 + 能力关系分类
        ↓
按冲高/持平/保底组合生成每日队列
        ↓
原始岗位页跳转 → 用户确认投递
        ↓
SQLite 台账、渠道健康度、审计事件
```

## 从源码运行

要求 Python 3.11 或更高版本。核心依赖 `pypdf` 解析可读 PDF，`cryptography` 只用于解密滴滴 Moka 的公开岗位响应；真实浏览器渠道额外需要 Playwright。

```powershell
cd "<解压后的项目目录>"
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\job-agent.exe init
.\.venv\Scripts\job-agent.exe seed-demo
.\.venv\Scripts\job-agent.exe evaluate
.\.venv\Scripts\job-agent.exe plan --channel boss
.\.venv\Scripts\job-agent.exe plan --channel official
.\.venv\Scripts\job-agent.exe serve
```

打开 `http://127.0.0.1:8765`。演示岗位不会访问真实网站。

BOSS 和 `strategy: browser` 的官网实验能力需要：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[browser]"
.\.venv\Scripts\python.exe -m playwright install chromium
```

## 首次配置

1. 运行 `job-agent init` 生成 `config.json`。
2. 打开控制台，点击“开始智能匹配”，上传 PDF/DOCX；再次使用时可以直接沿用，也可以替换。可读文本会在本机提取明确技能、年限和学历，扫描版 PDF 或复杂版式需在配置页手动校正。
3. 填写岗位名称和地点；按需展开职位类型、办公方式、薪资、经验差距、发布时间、排除词和公司黑名单。
4. 选择投递策略和本次渠道。向导会保存本次条件、采集并评估岗位，再进入统一岗位池。
5. 初次保持 `boss.enabled=false`、`auto_send_resume_after_reply=false`；可先用演示数据验证分类。
6. 示例配置已启用五个校园官网，只会按本次岗位关键词做只读采集；可在配置页逐个取消勾选，单个官网失效不会中止其他官网。

如果 BOSS 会话页不暴露文件上传控件，而是从账号中已有简历选择，必须把 `boss.resume_display_name` 配置为页面实际显示的固定简历名称；Agent 无法确认名称一致时不会发送。

控制台中的“配置”页面面向两类使用场景：

- 日常用户表单：候选人能力、目标岗位、地点、排除条件、公司档位、BOSS/官网关键词、每日额度、开场白、固定答案和邮件回执。
- 高级 JSON：新增官网 API 映射、页面选择器和投递表单字段，主要用于开发或维护适配器。

配置决定“有哪些渠道可以运行”；岗位池的“选择渠道抓取”按钮决定“本次具体运行其中哪几个渠道”。所有渠道的岗位会汇总到统一岗位池，同时保留来源并按渠道优先级去重。

配置保存时会验证额度、策略和硬规则。简历上传接口会单独校验文件类型、内容结构和 10 MB 大小限制；上传后的简历与本地提取文本固定保存在数据库旁的 `resumes/` 中，并只保留当前版本。文件、文本或配置保存失败会恢复旧版本；即使旧文件被移动或删除，页面仍可打开并要求用户重新上传。

## 维护文档

- [维护手册](docs/MAINTENANCE.md)：架构、改动地图、数据目录、测试和便携包发布。
- [渠道适配指南](docs/CHANNEL_ADAPTERS.md)：配置型官网、Python 注册表扩展、健康状态和验收清单。
- [硬筛选字段说明](docs/HARD_FILTERS.md)：各字段的精确定义、未知值策略及与投递策略的关系。
- [贡献指南](CONTRIBUTING.md)：提交渠道和规则改动的最低要求。

## BOSS 直聘（源码实验能力）

本项目参考并吸收了用户提供的 `boss-agent-capability.zip`，同时修正了其中的关键搜索路径：

```text
正确：https://www.zhipin.com/web/geek/jobs?query=...&city=...
错误：https://www.zhipin.com/web/geek/job?query=...&city=...
```

BOSS 不包含在基础便携包能力中，默认关闭，且本项目当前不承诺处理登录或验证码。源码安装 Playwright 后可由维护者做只读适配验证；HTTP 200 的“加载中”壳不被当成岗位。当前选择器集中在 `src/job_agent/connectors/boss_selectors.py`。

登录：

```powershell
.\.venv\Scripts\job-agent.exe boss-login --timeout 5
```

以下命令仅供在用户明确授权、平台规则允许且自行管理会话时进行实验验证：

```powershell
# 1. 只读发现
.\.venv\Scripts\job-agent.exe discover --channel boss

# 2. 评估和生成计划
.\.venv\Scripts\job-agent.exe evaluate
.\.venv\Scripts\job-agent.exe plan --channel boss

# 3. 演练，不写站点
.\.venv\Scripts\job-agent.exe execute --channel boss

# 4. 明确确认后真实发送预设开场白
.\.venv\Scripts\job-agent.exe execute --channel boss --live
```

真实动作没有自动重试。点击动作后缺少成功证据会标记 `结果待核验`；验证码、登录失效和选择器变化会停止当前渠道。默认产品流程不依赖这些写操作。

检查回复：

```powershell
.\.venv\Scripts\job-agent.exe check-replies
```

只有检测到非系统的 HR 入站消息，应用才进入 `HR已有效回复`。发送简历仍建议先在控制台或命令行单独确认；启用自动发送前必须用自己的账号做一次人工批准的冒烟测试。

## 官网 / ATS 适配器

官网渠道是固定白名单，不动态适配任意网站。`official_sites` 中每项支持：

- `campus_api`：选择仓库内已经验收的校园官网专用适配器，当前值为 `meituan`、`didi_moka`、`kuaishou`、`tencent`、`jd`。
- `json_api`：从公开 JSON 岗位列表读取结构化数据。
- `browser`：源码安装 Playwright 后，从已知页面选择器读取可见岗位卡片。
- `form`：源码中的实验性执行协议；`live=false` 只演练填写，开放题或缺失映射转人工，默认用户流程仍由用户在官网提交。

五个内置渠道会把搜索关键词传给官网接口，并在本地再次核对岗位名称、JD 与地点；结果保留稳定岗位 ID、完整可取得的 JD、地点、发布时间和对应详情页。配置中的 `autofill.profile` 是未来浏览器插件的稳定路由键，页面会明确显示“自动填表待适配”；当前版本不会填写或提交任何表单，也不会处理登录和验证码。

| 渠道 | `adapter` | 采集方式 | 自动填表 |
|---|---|---|---|
| 美团校招 | `meituan` | 官方公开岗位 JSON | 待适配 |
| 滴滴校招 | `didi_moka` | Moka 岗位接口与响应解密 | 待适配 |
| 快手校招 | `kuaishou` | 官方公开岗位 JSON | 待适配 |
| 腾讯校招 | `tencent` | 官方搜索与岗位详情 JSON | 待适配 |
| 京东校招 | `jd` | 官方公开岗位 JSON | 待适配 |

JSON API 示例：

```json
{
  "id": "target-careers",
  "name": "目标公司招聘",
  "enabled": true,
  "strategy": "json_api",
  "list_url": "https://careers.example.com/api/jobs",
  "allowed_hosts": ["careers.example.com"],
  "records_path": "data.jobs",
  "mapping": {
    "id": "id",
    "title": "title",
    "company": "company",
    "location": "location",
    "description": "description",
    "url": "detailUrl",
    "apply_url": "applyUrl",
    "salary_min": "salaryMin",
    "salary_max": "salaryMax",
    "experience_min": "experienceMin",
    "experience_max": "experienceMax",
    "employment_type": "employmentType",
    "work_mode": "workMode",
    "published_at": "publishedAt",
    "deadline": "deadline"
  },
  "form": {
    "required_answer_keys": ["name", "phone", "email"],
    "fields": {
      "name": "input[name='name']",
      "phone": "input[name='phone']",
      "email": "input[name='email']"
    },
    "resume_selector": "input[type='file']",
    "submit_selector": "button[type='submit']",
    "success_selector": ".application-success",
    "success_text": "申请已提交"
  }
}
```

必须从目标官网当前页面重新确认每个选择器，不能把示例选择器直接用于生产。

## 邮件回执（源码实验能力）

基础版本不配置邮箱登录。源码保留默认关闭的 IMAP 回执检查器；启用后只在官网已提交记录的时间窗口内检查最多 200 封近期邮件，并同时匹配公司/岗位身份和成功/拒绝语义。

```powershell
$env:JOB_AGENT_IMAP_PASSWORD='应用专用密码'
.\.venv\Scripts\job-agent.exe check-receipts
```

如果页面已经点击提交但没有网页证据，状态会是 `结果待核验`，不会因暂时没有邮件而自动重投。

## 命令速查

```text
init                 创建示例配置（不覆盖已有文件）
serve                启动本地 Web 控制台
seed-demo            导入四条离线演示岗位
discover             从已启用固定渠道采集
evaluate             执行硬规则、能力分类和评分
plan                 按渠道额度与策略组合生成队列
execute              默认只演练；--live 才改变网站状态
boss-login           手动登录并保存本地会话
check-replies        检查 BOSS HR 有效回复
check-receipts       检查官网邮件回执
run-cycle            发现、评估、计划；--live 才执行写操作
```

## 测试

```powershell
$env:PYTHONPATH='src'
py -3.13 -m unittest discover -s tests -v
py -3.13 -m compileall -q src tests
```

单元测试不访问招聘网站。真实页面选择器、登录状态、简历按钮和官网成功证据必须在用户自己的账号、网络、授权和最新平台规则下单独冒烟验证。

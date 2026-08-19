# 渠道适配指南

渠道分为三种扩展方式：复用内置校园官网适配器、添加配置型通用官网、注册外部 Python 适配器。注册表统一负责发现、评估和生成清单；最终提交是否可自动演练取决于适配器是否实现 `submit()`。

## 内置校园官网适配器

`config.example.json` 已配置以下五个固定白名单渠道。它们使用 `strategy: "campus_api"`，由 `adapter` 选择 `src/job_agent/connectors/campus.py` 中的专用协议。

| 配置 ID | `adapter` | 列表协议 | 详情证据 |
|---|---|---|---|
| `meituan-campus` | `meituan` | POST 官方岗位 API，服务端关键词与分页 | 列表响应已含职责和要求 |
| `didi-campus` | `didi_moka` | Moka Cookie 会话、POST API、AES-CBC/PKCS7 响应解密 | API 返回完整 `jobDescription` |
| `kuaishou-campus` | `kuaishou` | POST 官方岗位 API，项目代码与分页 | 列表响应已含职责和要求 |
| `tencent-campus` | `tencent` | POST 搜索 API；命中后限量 GET 详情 | 详情 API 的 `desc` 与 `request` |
| `jd-campus` | `jd` | POST 官方岗位 API，关键词与分页 | 列表响应已含职责、要求和城市 |

所有适配器都会限制关键词数、结果数、响应大小、超时和域名；使用官网服务端关键词后仍会在本地对标题、JD 和地点做一次确定性核对。详情页依赖 `#/...` 的 SPA 会保留 URL fragment，不能在 URL 规范化时删除。

在已安装源码环境中做只读现场冒烟：

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe .\scripts\smoke_campus_channels.py --keyword "产品经理"
```

该命令会访问真实官网，因此不属于离线单元测试。接口结构的最后一次人工验证日期必须随维护记录更新；HTTP 200 不是成功标准，至少要取得稳定岗位 ID、标题和详情 URL。

要复用同一门户的另一家公司或招聘项目，优先新增一条 `official_sites` 配置，并把项目 ID、分享码做成配置字段。员工标识、内推 ERP、个人推荐码默认留空；确有需要时只写入被 Git 忽略的本机 `config.json`，不得放进示例配置或提交记录。只有请求或响应结构不同才修改 `campus.py`。新增一种内置协议时同时：

1. 在 `SUPPORTED_CAMPUS_ADAPTERS` 注册名称。
2. 增加 `_discover_<adapter>` 与独立映射函数。
3. 在 `_discover_sync` 路由一次，不在 `orchestrator.py` 增加公司分支。
4. 补 `tests/test_campus.py` 的离线映射、URL 和加密/分页边界测试。
5. 更新示例配置、上表和真实站点冒烟记录。

### 未来自动填表契约

内置配置包含：

```json
"autofill": {
  "status": "planned",
  "profile": "moka-campus-v1",
  "allowed_hosts": ["app.mokahr.com"]
}
```

`profile` 是未来浏览器扩展选择站点字段映射的稳定键；每个标准化 `Job.metadata` 也带同名值。`allowed_hosts` 是扩展未来可运行的最小域名集合，不能用通配符。当前实现只保留契约并返回 `needs_human`，没有扩展代码、自动填写、登录、验证码处理或最终提交；在真正实现和验收前，`status` 必须保持 `planned`。

## 方式一：添加配置驱动的官网

在 `official_sites` 中增加一项即可，不需要修改编排器。最小 JSON API 定义：

```json
{
  "id": "example-careers",
  "name": "示例公司招聘",
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
    "education": "education",
    "employment_type": "employmentType",
    "work_mode": "workMode",
    "published_at": "publishedAt",
    "deadline": "deadline"
  }
}
```

`id`、`list_url` 和 `strategy` 是就绪检查必填项。URL 必须是 HTTPS，并且初始地址、HTTP 跳转后的最终地址、岗位详情和申请地址都只能落在 `allowed_hosts`。`records_path` 与 `mapping` 使用点分路径读取 JSON。

JSON 映射契约如下：

- 字符串：`id`、`title`、`company`、`location`、`description`、`url`、`apply_url`、`education`、`published_at`、`deadline`。
- 数值：`salary_min`、`salary_max` 以“元/月”整数表示；`experience_min`、`experience_max` 以年表示。纯数字或带千位逗号的值会转换，`20k` 等展示字符串不会猜测。
- 元数据：`employment_type`、`work_mode` 可为字符串或字符串数组，分别写入 `Job.metadata` 供硬规则使用。

浏览器列表页使用 `strategy: "browser"`，并提供 `selectors.job_card`、`selectors.title` 和 `selectors.url`。还可提供与上述字段同名的选择器，例如 `salary_max`、`experience_min`、`employment_type` 和 `work_mode`。选择器必须来自当前真实页面，不能照抄示例；浏览器跳转后也会在读取或填写前复核域名白名单。

## 方式二：注册专用 Python 适配器

Connector 只需实现三个成员：

```python
class ExampleConnector:
    source = "custom:example"

    async def discover(self, keywords: list[str]) -> list[Job]:
        ...

    async def close(self) -> None:
        ...
```

然后用 provider 返回 `ChannelAdapter`：

```python
from job_agent.connectors.registry import ChannelAdapter


def provide_channels(config):
    yield ChannelAdapter(
        id="custom:example",
        name="示例招聘渠道",
        channel_type="custom",
        enabled=True,
        keywords=list(config.preferences.official_keywords),
        strategy="json_api",
        url="https://jobs.example.com",
        connector_factory=ExampleConnector,
        success_status="api_fetched",
        allowed_hosts={"jobs.example.com"},
        daily_limit=10,
    )
```

外部包可通过 entry point 注入，不需要修改本仓库：

```toml
[project.entry-points."job_agent.channels"]
example = "example_job_channel:provide_channels"
```

测试也可直接构造 `ChannelRegistry` 注入 `JobAgent`。参考 `tests/test_orchestrator.py` 的 `test_registered_channel_needs_no_orchestrator_branch`。

注册后无需修改 `database.py`、`orchestrator.py` 或前端即可进入以下链路：选择渠道 → 发现 → 硬规则/双向评分 → `plan_all()` 生成该渠道清单。`allowed_hosts` 至少包含 `url` 的主机；如果详情或申请页使用其他可信主机，必须显式补充。

默认执行方式是人工跳转。若扩展包需要支持表单演练，可在同一个 Connector 上额外实现：

```python
async def submit(self, job, fixed_answers, resume_path, *, live):
    # 返回 ActionResult；live=False 时不得点击最终提交。
    ...
```

未实现 `submit()` 的扩展渠道仍可完整发现、评估、排序和生成清单，执行阶段会返回 `needs_human` 与原始岗位链接，不会报未知渠道。BOSS 的“开场白 → 回复 → 简历”是内置的专用两阶段执行器；不要把它当成普通表单模板。

## 标准岗位证据

适配器返回的每个 `Job` 至少要有：

- 稳定的 `source` 与 `source_id`。
- 岗位名称和公司；地点能取得时必须填写，无法取得时保留空值供未知字段策略处理。
- 可打开的详情 URL；有独立申请页时填写 `apply_url`。
- 足以支持筛选的真实详情，而不是搜索引擎摘要。
- 能取得时填写薪资、经验、学历、发布时间、截止时间和职位类型等结构化字段。

`Job.source` 必须等于 `ChannelAdapter.id`；编排器会拒绝 source 不一致、缺少 `source_id/title/company/url`、非 HTTPS 或越过 `allowed_hosts` 的整个批次，避免部分脏数据进入岗位池。外部 entry point 加载失败时，渠道列表会显示“渠道扩展加载失败”，而不是静默跳过。

## 健康状态约定

| 状态 | 含义 |
|---|---|
| `api_fetched` | API 提取到至少一个真实岗位 |
| `browser_fetched` | 浏览器提取到至少一个真实岗位 |
| `portal_unparsed` | 页面可达但没有稳定岗位，或解析异常 |
| `auth_required` | 明确需要登录或恢复会话 |
| `not_ready` | 渠道禁用或缺少配置 |
| `not_configured` | 请求了注册表中不存在的渠道 |

返回 0 个岗位时不能记录成功状态。一个渠道失败只影响自己的 source run，不应中止其他渠道。

## 适配器验收清单

- 允许域名和 URL 跳转均经过白名单校验。
- 分页有明确上限，单次请求有超时。
- 去重使用稳定岗位 ID；没有 ID 时使用规范化详情 URL。
- 登录、验证码、加密接口和空白 SPA 被明确分类，不伪造结果。
- `close()` 在成功和失败路径都能释放浏览器/连接。
- 只读发现有离线 fixture 或可控测试；真实站点冒烟测试单独记录日期和证据。
- 没有对不确定写操作做自动重试。

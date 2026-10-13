---
name: "职来 Agent"
description: "深海蓝与冷灰白的本地求职工作台"
colors:
  ink: "#1c2c45"
  muted: "#5f6f84"
  line: "#dfe5ee"
  paper: "#f5f7fa"
  card: "#ffffff"
  primary: "#233b62"
  focus: "#315984"
  orange: "#a96313"
  red: "#a34535"
  blue: "#406c9b"
  nav-background: "#f0f3f8"
  nav-active: "#dfe9f7"
  nav-text: "#40516b"
  readout-blue: "#eef3fa"
  readout-amber: "#fcf7ed"
  positive-background: "#dff3e9"
  positive-text: "#19644b"
  caution-background: "#fff0d4"
  caution-text: "#8a5816"
  work-card-line: "#dfe5ee"
typography:
  headline:
    fontFamily: "\"Segoe UI Variable Text\", \"Microsoft YaHei UI\", Aptos, sans-serif"
    fontSize: "30px"
    fontWeight: 750
    lineHeight: 1.35
    letterSpacing: "-.03em"
  title:
    fontFamily: "\"Segoe UI Variable Text\", \"Microsoft YaHei UI\", Aptos, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "-.02em"
  body:
    fontFamily: "\"Segoe UI Variable Text\", \"Microsoft YaHei UI\", Aptos, sans-serif"
    fontSize: "13px"
    lineHeight: 1.85
  experience:
    fontFamily: "\"Segoe UI Variable Text\", \"Microsoft YaHei UI\", Aptos, sans-serif"
    fontSize: "12px"
    lineHeight: 1.8
  label:
    fontFamily: "\"Segoe UI Variable Text\", \"Microsoft YaHei UI\", Aptos, sans-serif"
    fontSize: "12px"
    fontWeight: 650
    lineHeight: 1.7
  action:
    fontFamily: "\"Segoe UI Variable Text\", \"Microsoft YaHei UI\", Aptos, sans-serif"
    fontSize: "13px"
    fontWeight: 650
  caption:
    fontFamily: "\"Segoe UI Variable Text\", \"Microsoft YaHei UI\", Aptos, sans-serif"
    fontSize: "10px"
    lineHeight: 1.7
  body-base:
    fontFamily: "\"Segoe UI Variable Text\", \"Microsoft YaHei UI\", Aptos, sans-serif"
    fontSize: "14px"
  mono:
    fontFamily: "Consolas, monospace"
    fontSize: "12px"
    lineHeight: 1.65
rounded:
  control: "8px"
  navigation: "9px"
  carousel: "10px"
  readout: "9px"
  badge: "5px"
  status: "999px"
  work-card: "14px"
  panel: "16px"
  dialog: "18px"
spacing:
  8: "8px"
  12: "12px"
  14: "14px"
  16: "16px"
  18: "18px"
  20: "20px"
  24: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.card}"
    typography: "{typography.action}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
  button-secondary:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.action}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
  input-search:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 14px 10px 42px"
    height: "42px"
  navigation-item:
    backgroundColor: "transparent"
    textColor: "{colors.nav-text}"
    typography: "{typography.body-base}"
    rounded: "{rounded.navigation}"
    padding: "13px 16px"
  status-positive:
    backgroundColor: "{colors.positive-background}"
    textColor: "{colors.positive-text}"
    typography: "{typography.label}"
    rounded: "{rounded.status}"
    padding: "5px 10px"
  status-caution:
    backgroundColor: "{colors.caution-background}"
    textColor: "{colors.caution-text}"
    typography: "{typography.label}"
    rounded: "{rounded.status}"
    padding: "5px 10px"
  work-card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.work-card}"
    padding: "21px 22px 0"
  evidence-group:
    textColor: "{colors.primary}"
    padding: "14px 0 10px"
  carousel-arrow:
    backgroundColor: "{colors.card}"
    textColor: "{colors.primary}"
    rounded: "{rounded.carousel}"
    width: "46px"
    height: "52px"
---

# Design System: 职来 Agent

## Overview

**Creative North Star: "可信招聘顾问工作台"**

“可信招聘顾问工作台”以深海蓝动作、冷灰白工作区、白色阅读面与浅蓝选中状态组织求职操作。品牌仍为职来 Agent；标题、事实、未知信息和证据入口各有明确层级，色彩与文字服务于核对而不是宣传。

本轮是用户明确指定配色、单卡切换与页面职责的定向迭代。实际界面以 [commercial.css](src/job_agent/static/commercial.css) 在 [styles.css](src/job_agent/static/styles.css) 之后的结果为准。品牌为卡片与勾的几何 SVG，控件为语义 HTML/CSS；[森林绿效果图](docs/assets/design/recommendation-comp.png)及其[生成记录](docs/assets/design/recommendation-comp.json)仅保留为历史来源，不再作为当前规范。

**Key Characteristics:**

- 深海蓝主动作、冷灰白背景与浅蓝选中面；green、amber、red 仅表达明确业务状态。
- 卡片与勾的平面品牌 SVG 与同组细线功能图标，无假公司 Logo。
- 内容容器平整、细边框分组，卡片高度由实际数据决定。
- 推荐页一次展示一张工作卡、两侧箭头切换；全部岗位为完整列表，求职进度为阶段记录。

## Colors

前置颜色记录实际生效的 CSS。侧车色带是预览元数据，不是新增应用配色。

### Primary

- **深海蓝 / 焦点蓝**（`primary` / `focus`）：主 CTA、链接及可见焦点。CSS 旧 `--green` / `--green-2` 是其兼容别名，不表示品牌仍为绿。

### Secondary

- **导航浅蓝 / 蓝灰读数底**（`nav-active` / `readout-blue`）：选中入口与工作卡读数，不编码录用概率。
- **琥珀读数底**（`readout-amber`）：需核实工作卡读数。
- **正向绿 / 待核实琥珀标签**（`positive-background`、`positive-text` / `caution-background`、`caution-text`）：与明确状态文字配对。

### Tertiary

- **待核实标签字**（`caution-text`）：琥珀状态中的可读文字。
- **辅助橙、错误红、辅助蓝**（`orange`、`red`、`blue`）：保留图表、危险操作和已有分类状态的语义。

### Neutral

- **冷灰白背景、白色卡面、导航冷灰**（`paper`、`card`、`nav-background`）：区分工作区与阅读面。
- **墨蓝、辅助蓝灰、导航文字**（`ink`、`muted`、`nav-text`）：正文及次级信息。
- **分隔冷灰 / 工作卡边框**（`line` / `work-card-line`）：平面容器与信息分组。

**The Evidence Tone Rule.** 主品牌蓝不替代业务状态；正向绿、待核实琥珀与错误红始终配明确文字，不能把色彩当作录用概率或保证。

## Typography

**Display Font:** Segoe UI Variable Text (with "Microsoft YaHei UI", Aptos, sans-serif)

**Body Font:** Segoe UI Variable Text (with "Microsoft YaHei UI", Aptos, sans-serif)

**Mono Font:** Consolas (with monospace)

**Character:** 中文无衬线与较开放的行高承担主要阅读，事实用字重区分已知与待核实；图标和短标签辅助扫描，不替代正文。

### Hierarchy

- **Headline**（30px，750，行高 1.35）：页面标题；移动宽度为（26px）。
- **Title**（22px，700，行高 1.4）：岗位标题；移动宽度为（18px）。
- **Body**（13px，行高 1.85）：推荐理由与风险；移动宽度为（12px）。
- **Experience**（12px，行高 1.8）：体验摘要；有事实时字重（500），待核实时（400）。
- **Label / Action**（12px／13px，650）：体验标签、状态与标准按钮。
- **Caption**（10px，行高 1.7）：来源摘要和证据辅助提示；关键正文不采用该层级。
- **Body Base / Mono**（14px／12px）：全局基础字号与既有 JSON 编辑器。

## Layout

桌面浅侧栏宽（248px），内容区内边距（26px 28px 42px）。在工作区断点（1180px）侧栏收窄（208px），内容区内边距改为（24px）。移动断点（720px）侧栏进入文档流，导航横向滚动，内容区内边距（20px 14px 32px）。既有配置和双栏面板仍在其断点（1120px）转为单列，表格保留横向滚动容器。

推荐页一次显示一张高推荐工作卡，没有固定卡片高度。桌面轮播为左按钮（46px）、自适应中卡、右按钮（46px），列间距（12px）；箭头随长卡阅读保持可访问。卡片上方为岗位身份与状态／原岗位动作，其下为三项读数及提交资格说明；正文是理由、风险、六组体验三分区。理由与证据保留自然换行，不以历史效果图高度限制内容。

在（1180px）内，体验区移到理由／风险下方，六组体验排为三列；在（720px）内，左右按钮各（30px）、列间距（6px），身份与动作分行、读数纵向排列、理由和风险依序排列，体验保持两列；（380px）以下体验为单列。展开依据区继续容纳完整事实、来源和作用域。求职进度用简短统计、筛选与记录表格，不复用推荐三分区。

## Elevation & Depth

当前工作区以浅背景、白卡面和细分隔线表达层次。导航、卡片、面板、指标及总览主区均取消投影，按钮悬停也不位移。提示消息使用当前通用轻阴影；模态对话框仍保留原有更高层级的阴影与遮罩。

### Shadow Vocabulary

- **提示消息**（`box-shadow: 0 5px 20px rgb(28 44 69 / 6%)`）：当前 `--shadow`。
- **模态对话框**（`box-shadow: 0 30px 80px rgb(20 35 59 / 28%)`）：浮层样式。

**The Flat Workspace Rule.** 导航、推荐卡、旧面板、指标卡与总览主区保持平面；只有提示消息与模态对话框保留浮层阴影。

## Shapes

控件圆角（8px）、导航与读数圆角（9px）、工作卡圆角（14px）形成克制层级。旧面板保留较大的圆角（16px），模态对话框为（18px）。通用小标签改为紧凑圆角（6px），推荐标题附近的演示标签为（5px），行动状态为胶囊。公司标记采用首字圆形，不伪装成公司 Logo。

品牌为本地卡片与勾的几何 SVG；功能图标来自 [ui-icons.js](src/job_agent/static/ui-icons.js)，统一（24×24 viewBox）、线宽（1.7）、圆线端点及 `currentColor`。左右箭头也使用同组 SVG，不以字符替代；实际尺寸随导航、按钮和体验标签调整，不引入远程图标字体。

## Components

### Buttons

- **Primary:** 深海蓝实色与白字，最小高度（41px），内边距已记录；悬停使用更深蓝。
- **Secondary / Ghost:** 白底细边框，悬停浅蓝灰；图标与文字水平排列。
- **State:** 背景和边框过渡（160ms ease），无上移或悬浮阴影；焦点为实色蓝轮廓（2px，外偏移 3px）。
- **Other variants:** 既有强调、危险、深底浅色与禁用按钮按业务职责保留；未开放入口使用明确禁用文案。

### Inputs / Fields

搜索框内置本地 SVG 搜索图标，隐藏标签仍保留可访问名称；搜索高度（42px），左留白（42px）。筛选、复选和配置字段保留语义控件与可见焦点，配置字段沿用聚焦边框和轻晕圈。移动搜索独占一行。

### Navigation

冷灰底、浅蓝选中面与线性图标；桌面项最小高度（50px），移动项（38px）。当前页同时用较重字重与 `aria-current="page"` 表达；设置低频入口前有分隔线。移动导航可横向滚动，主导航名称与实际页面职责一致。

### Chips

推荐行动状态采用薄荷／琥珀胶囊，状态文字（12px，650）；演示和来源标签更紧凑。分类标签保留原业务语义，只更新为较小圆角。状态不能仅靠背景色表达。

### Cards / Containers

旧面板、运行统计和设置保留任务行为，统一为平面细边框表面；运行统计主区为实色深海蓝。推荐工作卡内边距（21px 22px 0），移动宽度（17px 14px 0），标题、正文和读数随内容换行。没有与效果图绑定的固定高度。

### Recommendation Work Card & Evidence

工作卡同时显示薪资待遇、可投性、能力匹配，理由与风险配有同组符号；六组体验始终出现，缺少事实时显示待核实。已知薪资可用稍大的读数（17px），不把未披露信息写成推算值。

依据胶囊保留编号／数量，并指向完整证据组。点击后展开原生 `details`、高亮该结论关联的来源并把焦点移到首条；展开横条同时显示来源数量与出处提示。展开区保留待遇细项、门槛／能力、体验事实、HR 问题及证据的原文、日期、作用域和来源链接。收起时仍可识别证据入口，窄屏继续完整重排。

减少动态偏好沿用既有覆盖规则；新的按钮与展开箭头仅使用（160ms ease）状态过渡。

### Carousel & Progress

轮播左右按钮有上一张／下一张可访问名称、明确焦点和边界禁用态，不依赖卡片内容生成或移除。顺序状态使用简短序号；没有高推荐结果时显示空结果，不在卡片外添加重复介绍句。键盘左右切换局限于轮播区域，不影响文本输入。

求职进度以阶段、来源、更新时间与备注表达事实；统计用平面文字分组，筛选与表格共用现有控件。记录弹窗宽度随屏幕收缩，保存失败保留输入并显示错误。手工记录与真实投递分离提示属于必要边界，不能作为“冗余文案”删除。

## Do's and Don'ts

### Do:

- Do 优先使用当前覆盖样式的深海蓝、冷灰白、浅蓝选中面与文字层级。
- Do 让长标题、理由、风险和来源按内容换行，卡片自然增高。
- Do 保留六组体验、待核实文案、可展开证据和可见键盘焦点。

### Don't:

- Don't 恢复森林绿主品牌、树苗图标、旧推荐双列长卡或卡片悬浮投影。
- Don't 把效果图当成网页背景，或把效果图示例文案与固定高度当作真实数据约束。
- Don't 把推荐页三分区推广为所有页面模板，或添加虚假 Logo、匹配概率和确定性结论。

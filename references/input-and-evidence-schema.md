# 输入、双证据与结构化字段

第一阶段先创建 UTF-8 `project-manifest.json`。V2 模板位于 `assets/project-manifest-template.json`；字段缺失时保留 `unknown`、空列表、空对象或 `null`，不得自行补造。

## 根字段

```text
schema_version, project, audiences, brand_materials, space, constraints,
storyline, evidence, design_references, conflicts, assumptions, open_questions
```

- `schema_version` 固定为 `2.0`。
- 受众编号 `A##`；企业事实 `E###`；设计参考 `D###`。
- `project.adapters` 最多两个；证据不足时用 `generic`。
- `project.budget_tier` 只用 `basic`、`standard`、`flagship`、`unknown`。
- `space.confidence` 只用 `high`、`medium`、`low`、`unknown`。
- 旧版 manifest 由验证器在内存中规范化，不修改用户原文件。

## 项目与受众

`project` 至少包含项目名、企业名、建设目标、项目总体预计参观时长区间、预算档位和适配器。每个 `A##` 包含名称、接待场景、`expected_visit_minutes={min,max}`、核心疑问、离场记忆、期望行动和路线模式。多路线项目必须记录各受众时长，供路线校验使用。

## 品牌与空间资料

品牌资料记录名称、文件路径/URL、日期或版本、用途和可读状态。空间资料记录面积口径、层高、平面图、尺寸、现场照片、入口、出口、不可改造条件和置信度。图片、图纸或视频无法检查时记录未完成范围，不根据文件名推断内容。

## 企业事实证据 `[E###]`

允许 `source_type`：

- `user_formal_material`
- `company_official`
- `official_wechat`
- `annual_report`
- `government`
- `industry_association`

每条包含 `claim`、`source`、`locator`、发布日期/报告期、访问日期、状态、有效性和冲突信息。状态只用：`已核实`、`用户提供待核实`、`来源冲突`、`缺少来源`。

## 设计参考证据 `[D###]`

允许 `source_type`：

- `design_firm_official`
- `design_award`
- `professional_association`
- `government_standard`
- `public_cultural_institution`
- `manufacturer_technical`

每条包含 `source`、`purpose`、`takeaway`、`limitations`、定位、访问日期和版权/使用提醒。`D###` 只能支持方法、材料、互动、包容性和风险判断，不能证明企业事实。

## 冲突、假设与问题

- `conflicts`：相关证据、差异、影响对象、暂定处理、责任人和状态。
- `assumptions`：假设、依据、置信度、影响 `S/Z/R/X/P` 和验证方式。
- `open_questions`：问题、影响、责任建议、截止节点和阶段门。

不要静默选择较新或更有利的来源。

## 第二阶段门

进入第二阶段必须同时满足：

```json
{
  "confirmed": true,
  "selected_id": "S01",
  "confirmed_at": "2026-07-15T15:00:00+08:00",
  "confirmation_note": "用户选择 S01，并要求融合 S02 的案例章节。"
}
```

缺少任一字段都停止第二阶段。推荐运行：

```powershell
py -3 scripts/validate_project.py <成果目录> --stage phase1
```

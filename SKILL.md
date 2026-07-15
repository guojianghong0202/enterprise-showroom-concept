---
name: enterprise-showroom-concept
description: 将企业品牌与空间资料转化为两阶段、双证据、可验证的企业品牌展厅专业概念设计。用于企业展厅、企业馆和形象展厅的访客决策、信息架构、2–3 条故事—空间方向、展区面积与邻接、参观路线、展项互动、视觉导视、三档概念策略、包容性体验、效果图交接、策划母稿和 PPT 逐页脚本；支持科技制造、集团/产业园、服务平台、文化传承适配。资料不足时降级，不用于施工图、正式预算、法规符合性或工程结论。
---

# 企业品牌展厅专业概念设计 V2

先建立可追溯的项目与设计模型，再生成提案文件。`project-manifest.json` 管输入、事实和确认；`design-model.json` 管设计对象；Markdown 是人类交付视图。

## 不可违反

1. 第一阶段只输出诊断和 2–3 条故事—空间候选，然后停止。
2. 第二阶段必须有 `confirmed=true`、`selected_id`、`confirmed_at` 和 `confirmation_note`。
3. 企业事实只用 `[E###]` 官方证据；设计参考用 `[D###]`，不能证明企业事实。
4. 缺图纸、出入口或尺寸时降低空间置信度，只给邻接、比例和候选路线。
5. 不输出施工图、精确/正式预算、法规符合性或未经专业确认的工程结论。
6. 不覆盖既有成果；用初始化器创建版本目录。
7. 实际图片、PPTX、DOCX 或 PSD 仅在用户明确要求时生成。

## 初始化与输入

读取品牌文件、图纸、尺寸、现场照片、出入口、限制和官方入口。不能辨认的媒体明确记录，不根据文件名推断。

按 `references/input-and-evidence-schema.md` 建立数据；研究时遵守 `references/official-source-policy.md`。新项目可运行：

```powershell
py -3 scripts/init_project.py --project-name <项目名> --company-name <企业名> --output <成果父目录> --stage phase1
py -3 scripts/validate_project.py <成果目录> --stage phase1 --no-write
```

`BLOCKER` 先修正；`WARNING` 写入成果并按降级方式继续。只询问会改变方向或阻断阶段门的问题。

## 第一阶段：诊断与方向比选

1. 读取 `references/visitor-and-message-strategy.md`，建立 `A##` 访客决策和四层信息架构。
2. 依正式资料选择最多两个 `references/industry-adapters.md` 适配器；不足则用 `generic`。
3. 读取 `references/enterprise-narrative-frameworks.md` 与 `references/story-space-directions.md`。
4. 默认生成 3 条 `S##`；资料不足允许 2 条并说明原因。候选同时包含主张、空间母题、视觉 DNA、标志性展项、体验节奏、证据、依赖、风险和评分。
5. 任意两条候选至少在访客任务、叙事起点、空间原型、标志性展项、情绪推进、视觉母题中的三项实质不同。
6. 更新两个 JSON，按模板生成 01、02，执行 `validate_project.py --stage phase1`。
7. 停止，等待用户选择、融合或修改；不得提前生成 03–06。

## 第二阶段：专业概念设计

阶段门完整后：

1. 读取 `references/space-programming-system.md` 与 `references/zoning-and-visitor-flow.md`，建立 `Z##`、邻接图、面积区间、`R##` 路线、停留和置信度。
2. 读取 `references/exhibit-interaction-operations.md`，为每个 `X##` 定义目标、证据、载体、互动闭环、低技术替代、更新维护、包容性和预算档位。
3. 读取 `references/visual-direction-system.md`，形成品牌转译、色材光、图形、多媒体、导视、三档策略与反同质化说明。
4. 读取 `references/accessibility-and-inclusive-experience.md`，只做概念级检查并列专业复核。
5. 读取 `references/ppt-decision-storytelling.md`，建立带决策问题、对象映射、资产状态、讲解时间和异议的 `P##`。
6. 读取 `references/render-prompt-handoff.md`，为每个关键 `Z##` 生成模型无关交接卡。仅用户明确要求深化提示词/出图时调用 `advertising-render-prompts` 或图像能力。
7. 按 `references/output-contract.md` 和 `assets/` 生成 03–06；用 `references/quality-rubric.md` 复核。
8. 运行：

```powershell
py -3 scripts/validate_project.py <成果目录> --stage phase2
```

没有阻断且质量分达到 80 才标“概念提案可用”。

## 交付

控制文件：`project-manifest.json`、`design-model.json`、`validation-report.json`。

Markdown：

```text
01_需求诊断与证据台账.md
02_故事线比选与确认记录.md
03_企业展厅概念策划母稿.md
04_PPT逐页提案脚本.md
05_分区效果图提示词.md
06_来源与待确认清单.md
```

所有重要对象保留 `A/E/D/S/Z/R/X/P` 编号。结构化数据与 Markdown 冲突时阻断交付，以结构化模型为准同步修正。

## 失败与边界

- 官方来源不可访问：记录链接、失败原因、影响和替代材料，不用转载补位。
- 来源冲突：并列保留并关联受影响对象，等待权威确认。
- 空间资料不足：只输出关系、区间、假设和候选路线。
- 预算未知：比较三档策略和成本驱动，不推荐金额。
- 数字条件未知：每项提供静态或低技术替代。
- 效果图能力不可用：照常交付通用提示词和交接卡。
- 用户要求工程判断：说明边界并列出需要的注册专业人员、现场数据和下一步。

最终说明生成文件、适配器、假设/降级、验证状态、待确认项和绝对成果路径。

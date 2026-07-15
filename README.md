# Enterprise Showroom Concept V2

一个面向企业品牌展厅、企业馆与形象展厅的专业概念设计 Skill。它把品牌与空间资料转成结构化、可追溯、可验证的两阶段提案，并提供可直接制作 PPT 的逐页脚本。

## V2 能力

- 访客决策：接待场景、核心疑问、离场记忆和期望行动
- 四层信息：总主张、关键信息、证明材料和展示载体
- 双证据：企业事实 `[E###]` 与设计参考 `[D###]` 严格分流
- 故事—空间：2–3 条同时包含叙事、空间、视觉、展项和体验的候选
- 空间规划：展区 `Z##`、邻接、面积区间、路线 `R##`、停留和置信度
- 展项互动：展项 `X##`、互动闭环、低技术替代、更新维护和预算档位
- 视觉导视：品牌转译、色材光、图形、多媒体、导视和反同质化
- 包容性体验：概念级路线、文字、影音、互动和替代体验检查
- 提案表达：带决策问题、对象映射、资产状态和异议处理的 `P##` 页面卡
- 行业适配：科技制造、集团/产业园、服务平台、文化传承，可组合最多两个

## 两阶段

第一阶段只输出：

1. `01_需求诊断与证据台账.md`
2. `02_故事线比选与确认记录.md`

生成 2–3 条方向后停止。用户选择、融合或附条件批准，并完整记录确认时间和内容后，第二阶段再补充：

3. `03_企业展厅概念策划母稿.md`
4. `04_PPT逐页提案脚本.md`
5. `05_分区效果图提示词.md`
6. `06_来源与待确认清单.md`

每个项目还包含：

- `project-manifest.json`：输入、事实、参考、约束和用户确认
- `design-model.json`：故事、空间、路线、展项、视觉和 PPT 映射
- `validation-report.json`：阻断、警告、分数、降级和最终状态

## 推荐输入

- 企业介绍、品牌手册、产品/业务、案例、历程、文化和未来规划
- 平面图、尺寸、现场照片、入口、出口、固定结构和限制条件
- 项目目标、受众、接待场景、预计时长、预算档位和运维条件
- 企业官网、官方公众号、年报、政府/协会等官方入口

资料不足时保留 `unknown` 和待确认项，不虚构企业事实、空间尺寸或确定落位。

## 安装

```powershell
git clone https://github.com/guojianghong0202/enterprise-showroom-concept.git "$HOME/.codex/skills/enterprise-showroom-concept"
```

重新打开 Codex 后使用 `$enterprise-showroom-concept`。

## 快速开始

初始化第一阶段：

```powershell
py -3 scripts/init_project.py --project-name "未来体验中心" --company-name "某某企业" --output "成果" --stage phase1
```

验证：

```powershell
py -3 scripts/validate_project.py "成果/未来体验中心" --stage phase1
py -3 scripts/validate_project.py "成果/未来体验中心" --stage phase2
```

单项验证接口仍保留：

```powershell
py -3 scripts/validate_input_manifest.py <project-manifest.json> --stage phase1
py -3 scripts/validate_design_model.py <design-model.json> --manifest <project-manifest.json> --stage phase2
py -3 scripts/validate_concept_package.py <成果目录> --stage phase2
```

## 使用示例

```text
请使用 $enterprise-showroom-concept，检查我提供的企业资料、平面图和现场照片。
先完成需求诊断，并给出 3 条有明显故事、空间和展项差异的方向；第一阶段后停止。
```

确认后：

```text
选择 S02，融合 S01 的技术验证展项。请记录确认内容后进入第二阶段，
生成完整策划母稿、PPT 逐页脚本和分区效果图交接提示词。
```

效果图交接卡始终生成；只有用户明确要求时才深化提示词或实际生成图片。PPTX、DOCX、PSD 同样不会自动生成。

## 目录

- `SKILL.md`：两阶段编排、资源路由与边界
- `references/`：专业设计方法、证据政策、行业适配和质量规则
- `assets/`：三个 JSON 模板与六个 Markdown 模板
- `scripts/`：初始化、输入/模型/交付/聚合验证
- `tests/`：回归、结构化模型与跨文件一致性测试
- `.github/workflows/validate.yml`：Windows/Linux 持续集成

## 质量与边界

验证器检查编码、阶段门、编号、悬空引用、面积、邻接、路线、展项完整性、Markdown 映射、占位符和越界工程表达。没有阻断且质量分达到 80 才能标记“概念提案可用”。

本 Skill 只输出专业概念设计，不替代建筑、结构、消防、机电、无障碍、造价、设备安装、施工图或注册专业人员的审核；不输出正式预算或法规符合性结论。

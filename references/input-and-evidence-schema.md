# 输入清单与证据结构

在第一阶段开始时创建 UTF-8 JSON 清单。字段缺失时保留空值，并让验证脚本决定阻断或降级，不自行编造。

```json
{
  "project": {
    "name": "项目名称",
    "company_name": "企业名称",
    "objective": "建设目标",
    "audiences": ["客户", "合作伙伴"],
    "visit_duration_minutes": 30
  },
  "brand_materials": ["企业介绍.pdf", "品牌手册.pdf"],
  "space": {
    "area_sqm": 320,
    "ceiling_height_m": 4.2,
    "floor_plan": "展厅平面图.pdf",
    "entrances": ["东侧主入口"],
    "exits": ["西侧出口"],
    "photos": ["现场照片01.jpg"]
  },
  "storyline": {
    "confirmed": false,
    "selected_id": null
  },
  "evidence": [
    {
      "id": "E001",
      "claim": "企业事实",
      "source_type": "annual_report",
      "source": "2025年度报告",
      "locator": "第12页",
      "accessed_at": "2026-07-11",
      "status": "已核实"
    }
  ],
  "conflicts": []
}
```

## 允许的来源类型

- `user_formal_material`：用户提供的正式企业文件。
- `company_official`：企业官网或官方信息平台。
- `official_wechat`：企业官方公众号。
- `annual_report`：企业公开年报或社会责任报告。
- `government`：政府官方网站。
- `industry_association`：行业协会官方网站。

## 证据状态

- `已核实`：来源和定位信息完整，可用于正式事实表述。
- `用户提供待核实`：来自用户材料，但缺少公开或正式定位信息。
- `来源冲突`：两个允许来源给出不一致信息，必须建立冲突记录。
- `缺少来源`：当前只有待确认说法，不得写成正式事实。

## 冲突记录

每项冲突记录：问题编号、相关证据编号、差异内容、影响范围、建议确认人和当前状态。不要静默选取较新或更有利的说法。

## 阶段门

第一阶段允许缺少空间尺寸，但必须标明降级。第二阶段必须设置 `storyline.confirmed=true` 并填写 `selected_id`，否则停止。

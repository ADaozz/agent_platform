# 中文期刊论文（单双栏可配置）

## 适用范围与优先级
高校／期刊官方指定模板和用户要求优先。本文件是可配置的通用设计，不能视为任一高校的合规证明。
GB/T 7713.1—2025 提供论文编写与结构依据；GB/T 7714—2025 提供参考文献依据。
具体字号、字体、页边距和题注位置是本方案的默认设计选择，不宣称由国标统一强制规定。
使用官方指定模板时保留模板样式与资源，不将本方案套写到模板上。

## 字体字号与命名样式
中文正文采用思源宋体类 Noto Serif CJK SC，西文采用 Liberation Serif，正文 10.5 pt。
标题采用 Noto Sans CJK SC：一级 16 pt、二级 14 pt、三级 12 pt；中文和西文分别声明。
如单位明确要求宋体／Times New Roman，提供正式 Design MD 配置并安装其授权字体；不得把字体替换隐瞒为原字体。
封面标题 22 pt，日期 12 pt；摘要标题 16 pt；图表题注、参考文献与表内文字 10.5 pt；页眉页脚 9 pt。
全部字号以结构化 Word 命名样式为准，直接字体／字号覆盖也接受检查。

## 结构与组件
- 封面使用 CoverTitle、CoverDate。封面构成单页组件，日期不得流到第二页；不靠统一缩字号修复。
- 中文／英文摘要使用 AbstractTitle、AbstractBody；关键词使用正文样式与清晰标签。
- 目录为原生 TOC 字段与 TOC1–3 样式，右对齐点引导线，必须有可解析页码及有效目标。
- 一级至三级标题不跳级，keepNext；正文启用孤行控制。
- 题注使用 Caption；图题置图下，表题置表上；按章节或连续编号，由计划明确且全文统一。
- 公式使用可编辑 Office Math，居中，编号右对齐；交叉引用使用 Word 字段。
- 引用与参考文献遵循选定的顺序编码制或著者—出版年制；采用 Reference 样式与悬挂缩进。
- 页眉 Header、页脚 Footer，使用原生 PAGE 字段；封面不编号，前置部分小写罗马数字，正文阿拉伯数字。
- 分节编号通过原生分节信息或指定模板表达；检查其格式、起始值及实际渲染结果。
- A4、上下左右 25.4mm。期刊方案默认双栏，可通过 init --columns 1 改为单栏；单位要求优先。
- 长表重复表头，禁止行跨页拆分；续表标注由章节计划明确，不能只凭表长推断单位要求。
- 图片保持宽高比，允许正常图文环绕；不允许正文、文本框与非透明图片遮挡。

## 来源元数据与参考页
来源、作用范围与核验等级记录于下方 sources。高校入口不是某项格式条款的证明；实际单位文件应附在任务中。
国家标准官方目录核验：GB/T 7713.1—2025 于 2026-02-01 实施，GB/T 7714—2025 于 2026-07-01 实施。目录核验不等于逐条合规认证。
参考页：[reference.svg](reference.svg)，仅展示通用排版参考；不作为某所学校的官方模板。

```docx-design
{
  "version": 2,
  "id": "cn-journal-paper",
  "page": {
    "width_twips": 11906,
    "height_twips": 16838,
    "margin_twips": 1440,
    "columns": 2,
    "column_space_twips": 420
  },
  "styles": {
    "Normal": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 21,
      "color": "000000",
      "bold": false,
      "alignment": "both",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "Heading1": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Sans CJK SC",
      "size_half_points": 32,
      "color": "000000",
      "bold": true,
      "alignment": "left",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true,
      "keep_next": true
    },
    "Heading2": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Sans CJK SC",
      "size_half_points": 28,
      "color": "000000",
      "bold": true,
      "alignment": "left",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true,
      "keep_next": true
    },
    "Heading3": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Sans CJK SC",
      "size_half_points": 24,
      "color": "000000",
      "bold": true,
      "alignment": "left",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true,
      "keep_next": true
    },
    "CoverTitle": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Sans CJK SC",
      "size_half_points": 44,
      "color": "000000",
      "bold": true,
      "alignment": "center",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true,
      "keep_next": true
    },
    "CoverDate": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 24,
      "color": "000000",
      "bold": false,
      "alignment": "center",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "AbstractTitle": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Sans CJK SC",
      "size_half_points": 32,
      "color": "000000",
      "bold": true,
      "alignment": "center",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true,
      "keep_next": true
    },
    "AbstractBody": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 21,
      "color": "000000",
      "bold": false,
      "alignment": "both",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "Caption": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 21,
      "color": "000000",
      "bold": false,
      "alignment": "center",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "Equation": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 24,
      "color": "000000",
      "bold": false,
      "alignment": "center",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "Reference": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 21,
      "color": "000000",
      "bold": false,
      "alignment": "left",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true,
      "hanging_indent_twips": 420
    },
    "TableText": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 21,
      "color": "000000",
      "bold": false,
      "alignment": "left",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "Header": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 18,
      "color": "000000",
      "bold": false,
      "alignment": "center",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "Footer": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 18,
      "color": "000000",
      "bold": false,
      "alignment": "center",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "TOC1": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 24,
      "color": "000000",
      "bold": false,
      "alignment": "left",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "TOC2": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 24,
      "color": "000000",
      "bold": false,
      "alignment": "left",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "TOC3": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 21,
      "color": "000000",
      "bold": false,
      "alignment": "left",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    }
  },
  "table": {
    "style_id": "DocumentTable",
    "header_fill": "F2F2F2",
    "border_color": "000000"
  },
  "components": {
    "cover": {
      "styles": [
        "CoverTitle",
        "CoverDate"
      ],
      "single_page": true,
      "max_space_after_twips": 480
    },
    "abstract": {
      "styles": [
        "AbstractTitle",
        "AbstractBody"
      ],
      "keywords": true,
      "languages": [
        "zh",
        "en"
      ]
    },
    "toc": {
      "styles": [
        "TOC1",
        "TOC2",
        "TOC3"
      ],
      "require_page_numbers": true,
      "require_targets": true
    },
    "body": {
      "style": "Normal",
      "columns": 2
    },
    "caption": {
      "style": "Caption",
      "figure_position": "below",
      "table_position": "above",
      "numbering": "chapter-or-continuous"
    },
    "equation": {
      "style": "Equation",
      "editable": "OMML",
      "number_position": "right"
    },
    "citations": {
      "style": "Reference",
      "scheme": "numeric-or-author-date",
      "standard": "GB/T 7714—2025"
    },
    "references": {
      "style": "Reference",
      "hanging_indent_twips": 420
    },
    "header": {
      "style": "Header"
    },
    "footer": {
      "style": "Footer",
      "page_field": true
    },
    "pagination": {
      "front_matter": "lowerRoman",
      "body": "decimal",
      "cover": "none",
      "repeat_table_headers": true,
      "split_rows": false,
      "preserve_image_aspect": true
    },
    "tables": {
      "style": "DocumentTable",
      "caption_position": "above",
      "repeat_header": true,
      "split_rows": false
    },
    "columns": {
      "supported": [
        1,
        2
      ],
      "default": 2,
      "gap_twips": 420
    }
  },
  "sources": [
    {
      "id": "GBT7713.1-2025",
      "title": "GB/T 7713.1—2025 信息与文献 编写规则 第1部分：学位论文",
      "url": "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=36C05B5738C54D42B4B262525320B52F",
      "scope": "论文结构与编写原则；不据此宣称通用方案的具体字号是强制国标",
      "verification": "official_catalog_verified_2026-11-11; normative_clauses_not_reproduced"
    },
    {
      "id": "GBT7714-2025",
      "title": "GB/T 7714—2025 信息与文献 参考文献著录规则",
      "url": "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=C6CE52E55AC09B9C79A20AEA77CEDD14",
      "scope": "引用与参考文献著录；不校验未提供原文的书目信息真实性",
      "verification": "official_catalog_verified_2026-11-11; normative_clauses_not_reproduced"
    },
    {
      "id": "institution-template",
      "title": "高校／期刊官方论文格式要求",
      "url": "https://grs.pku.edu.cn/",
      "scope": "示例官方发布入口；本通用方案不采纳任何单所学校的条款为统一国标",
      "verification": "entrypoint_only; attach actual institutional requirements when supplied"
    }
  ]
}
```

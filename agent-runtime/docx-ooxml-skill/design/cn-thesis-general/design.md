# 国内硕博学位论文通用方案

## 适用范围与优先级
高校／期刊官方指定模板和用户要求优先。本文件是可配置的通用设计，不能视为任一高校的合规证明。
GB/T 7713.1—2025 提供论文编写与结构依据；GB/T 7714—2025 提供参考文献依据。
具体字号、字体、页边距和题注位置是本方案的默认设计选择，不宣称由国标统一强制规定。
使用官方指定模板时保留模板样式与资源，不将本方案套写到模板上。

## 字体字号与命名样式
正文使用 Normal 样式，中文用宋体（SimSun），西文用 Liberation Serif，字号小四（12 pt），首行缩进 2 字符。
标题采用 Noto Sans CJK SC：一级 16 pt、二级 14 pt、三级 12 pt；中文和西文分别声明。
预览环境缺少宋体时允许用 Noto Serif CJK SC 渲染并记录替换，DOCX 仍声明宋体。学校指定不同字体时按要求配置。
封面标题 22 pt，日期 12 pt；摘要标题 16 pt；图表题注、参考文献与表内文字 10.5 pt；页眉 9 pt。
全部字号以结构化 Word 命名样式为准，直接字体／字号覆盖也接受检查。

## 结构与组件
- 封面使用 CoverTitle、CoverDate。封面构成单页组件，日期不得流到第二页；不靠统一缩字号修复。
- 中文／英文摘要使用 AbstractTitle、AbstractBody；关键词使用正文样式与清晰标签。
- 目录和参考文献各自另起一页，续页也由该部分独占。目录结束后，正文从下一页开始，随后按内容自然分页。
- “目录”标题用 TOCHeading，三号（16 pt）黑体，水平居中。目录默认三级，可按学校要求显示两级。
- 一级条目用小四号（12 pt）宋体风格，二级同字号，默认缩进约一字，三级用五号（10.5 pt），默认缩进约两字。缩进以学校模板或用户明确要求为准。默认 1.25 倍行距，可按学校模板改为单倍或 1.5 倍。
- 目录使用原生 TOC 和 PAGEREF 字段，点线引导，页码右对齐。随标题及其实际页码更新，全文完成后统一校验并刷新页码缓存。
- 一级章标题用 Heading 1 并设置段前分页。二级、三级标题用 Heading 2/3 并设置与下段同页。正文标题绑定一套 Word 多级列表，自动生成“第1章”“1.1”“1.1.1”。编辑时只输入标题文字，调整章节位置后可刷新目录。参考文献、附录和致谢仍可用标题样式，使用计划中的对应类型排除章号。标题不跳级，正文启用孤行控制。
- 表题用 TableCaption，置于表格上方，居中，与表格同页。默认五号（10.5 pt），中文使用 Noto Serif CJK SC（宋体风格）。学校指定字体时按学校要求配置。
- 表格默认用三线表，保留顶线、表头下线和底线。表注用 TableNote，紧接表格下方。
- 图题用 Caption，置于图片下方并居中。图表按章节或连续编号，由计划明确且全文统一。
- 公式使用可编辑 Office Math，居中，编号右对齐；交叉引用使用 Word 字段。
- 引用与参考文献遵循选定的顺序编码制或著者—出版年制；采用 Reference 样式与悬挂缩进。
- 封面独立成页，隐藏页码。中文摘要、英文摘要和目录各从下一页开始，页码使用大写罗马数字（I、II、III……），从中文摘要第一页起连续编号。
- 第 1 章从阿拉伯数字 1 起，后续章节、参考文献、附录和致谢延续同一套阿拉伯数字编号。参考文献、致谢设置段前分页。
- 页码使用原生 PAGE 字段，置于页脚水平居中，Times New Roman 五号（10.5 pt），仅显示数字。预览环境需安装 Times New Roman 才能按原字体渲染。
- 页码体系切换使用“下一页”分节符；同一编号体系内用段前分页另起一页。另起一页可以是偶数页。
- A4、上下左右 25.4mm，默认单栏。明确要求双栏时可通过 `init --columns 2` 设置。
- 长表重复表头，禁止行跨页拆分；续表标注由章节计划明确，不能只凭表长推断单位要求。
- 图片保持宽高比，允许正常图文环绕；不允许正文、文本框与非透明图片遮挡。

## 来源元数据与参考页
来源、作用范围与核验等级记录于下方 sources。高校入口不是某项格式条款的证明；实际单位文件应附在任务中。
国家标准官方目录核验：GB/T 7713.1—2025 于 2026-02-01 实施，GB/T 7714—2025 于 2026-07-01 实施。目录核验不等于逐条合规认证。
参考页：[reference.svg](reference.svg)，仅展示通用排版参考；不作为某所学校的官方模板。

```docx-design
{
  "version": 2,
  "id": "cn-thesis-general",
  "page": {
    "width_twips": 11906,
    "height_twips": 16838,
    "margin_twips": 1440,
    "columns": 1,
    "column_space_twips": 420
  },
  "styles": {
    "Normal": {
      "font": "Liberation Serif",
      "east_asia_font": "SimSun",
      "size_half_points": 24,
      "color": "000000",
      "bold": false,
      "alignment": "both",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "first_line_chars": 2,
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
      "keep_next": true,
      "page_break_before": true
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
      "size_half_points": 24,
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
    "TableCaption": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 21,
      "color": "000000",
      "bold": false,
      "alignment": "center",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true,
      "keep_next": true
    },
    "TableNote": {
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
      "font": "Times New Roman",
      "size_half_points": 21,
      "color": "000000",
      "bold": false,
      "alignment": "center",
      "line_twips": 360,
      "line_rule": "auto",
      "space_after_twips": 120,
      "widow_control": true
    },
    "TOCHeading": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Sans CJK SC",
      "size_half_points": 32,
      "color": "000000",
      "bold": true,
      "page_break_before": true,
      "keep_next": true,
      "line_twips": 300,
      "line_rule": "auto",
      "space_after_twips": 240,
      "alignment": "center"
    },
    "TOC1": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 24,
      "color": "000000",
      "bold": false,
      "alignment": "left",
      "line_twips": 300,
      "line_rule": "auto",
      "space_after_twips": 0,
      "widow_control": true
    },
    "TOC2": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 24,
      "color": "000000",
      "bold": false,
      "alignment": "left",
      "line_twips": 300,
      "line_rule": "auto",
      "space_after_twips": 0,
      "widow_control": true,
      "indent_twips": 240
    },
    "TOC3": {
      "font": "Liberation Serif",
      "east_asia_font": "Noto Serif CJK SC",
      "size_half_points": 21,
      "color": "000000",
      "bold": false,
      "alignment": "left",
      "line_twips": 300,
      "line_rule": "auto",
      "space_after_twips": 0,
      "widow_control": true,
      "indent_twips": 420
    }
  },
  "table": {
    "style_id": "DocumentTable",
    "header_fill": "FFFFFF",
    "border_color": "000000",
    "borders": "three_line"
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
      "keywords": true
    },
    "toc": {
      "styles": [
        "TOCHeading",
        "TOC1",
        "TOC2",
        "TOC3"
      ],
      "own_pages": true,
      "require_page_numbers": true,
      "require_targets": true
    },
    "body": {
      "style": "Normal",
      "heading_numbering": true,
      "preview_font_fallback": "Noto Serif CJK SC",
      "columns": 1
    },
    "caption": {
      "style": "Caption",
      "table_style": "TableCaption",
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
      "own_pages": true,
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
      "front_matter": "upperRoman",
      "body": "decimal",
      "body_start": 1,
      "cover": "none",
      "repeat_table_headers": true,
      "split_rows": false,
      "preserve_image_aspect": true
    },
    "tables": {
      "style": "DocumentTable",
      "caption_position": "above",
      "note_style": "TableNote",
      "note_position": "below",
      "repeat_header": true,
      "split_rows": false
    },
    "body_structure": [
      "cover",
      "abstract",
      "toc",
      "introduction",
      "methods",
      "results",
      "conclusion",
      "references",
      "appendix"
    ]
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

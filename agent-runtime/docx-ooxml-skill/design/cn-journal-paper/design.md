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

## 排版执行规范（必须遵守；按本 Design 执行而非临场自由排版）

以下规则约束 Agent 的内容生成、段落组织、插图和图表操作。正式投稿时，用户指定的期刊／机构官方模板或明确要求优先。此节不修改 `docx-design` 的机器可读字段；实际字号、字体、行距、页边距仍以文末 JSON 的原生 Word 样式为唯一数值来源。不得把这些通用默认值宣称为某期刊的强制标准。

### 排版基线与禁止事项
1. **先选语义样式，再填内容。** 普通正文使用 Normal，一级至三级标题使用 Heading1／Heading2／Heading3，摘要、公式、图题、表题、参考文献、表格正文分别使用 AbstractBody／Equation／Caption／Reference／TableText。不得为凑页数而把正文降字号、改变字体、缩行距、修改边距或隐式覆盖命名样式。
2. **字号冻结。** 本方案正文 10.5 pt，一级／二级／三级标题依次为 16／14／12 pt，题注、表内文字与参考文献 10.5 pt；严格使用 JSON 中的 `size_half_points`，不因字数或图片多少改变。允许斜体、加粗、上下标等语义性局部强调，但不得用 `runs.size`、`format_text.size` 等直接字号覆盖来重做整段或缩小超长内容。
3. **行距与段距冻结。** 正文采用 JSON 中 Normal 的 `line_twips=360`、`line_rule=auto`（对应约 1.5 倍行距）、`space_after_twips=120`（6 pt 段后）；其他样式遵从各自 JSON。不要使用逐段 `set_paragraph_format` 调整行距／段距来“挤下”图表。标题与后文保持同页，正文保留孤行控制。
4. **纸张与阅读顺序固定。** A4、四边各 25.4 mm。默认双栏、栏间约 7.41 mm，每栏实际可用宽度约 7.59 cm；单栏配置时正文可用宽度约 15.92 cm。段落正常顺排，不允许浮动对象遮挡文字，双栏文章遵守从左栏到右栏的阅读顺序。
5. **内容让位于规范。** 当元素装不下时，先缩短无关重复文字、精简图例或拆分表格，再让内容自然流到下一栏／下一页。禁止缩小全局字体、行距或页边距，禁止任意调整固定版心。不能在保持可读性的同时容纳时，应保留可下载草稿并明确报告问题。

### 图片尺寸、图文关系与质量
1. 论文示意图、实验结果图、照片统一采用**行内居中、等比例缩放**；常规图片双栏宽度建议 7.2 cm、上限约 7.59 cm；单栏宽度建议 14 cm、上限约 15.92 cm。尺寸由实际栏宽决定，不能直接沿用幻灯片尺寸或把 14 cm 图片硬塞进双栏的一栏。
2. 使用 `insert_image` 时显式传入符合本节的 `width_cm`，由引擎依原始宽高比确定高度。尽量使双栏普通图片高度不超过约 6 cm；若原图过于狭长，应先选择更合适的原图或按比例减小宽度，不得拉伸、挤压或裁掉科学数据。
3. 并列子图只在内容确实需要直接比较时使用 `insert_image_row`：双栏两图时每图约 3.3–3.4 cm 宽；三图以上若标签无法辨识，改为分开排版。子图标注 (a)(b) 与图题的位置和顺序必须一致。
4. 图片文字、坐标轴、图例和注释必须在最终页面可辨认；如果图中文字太密，应简化图中信息或将图拆为多张，不以继续缩小整图为解决方案。图片的 `alt` 与图题描述实际内容，不得凭空推断实验含义。
5. 图题统一紧邻图片**下方**，引用图片时使用文中交叉引用。图片与图题不得明显断裂，不允许图片边界越过栏宽或页边距。禁止使用无信息价值的装饰性图片填补留白。

### 原生图表尺寸与信息规范
1. 定量图表优先使用可编辑的 Word 原生图表（`insert_chart`）。默认双栏图表尺寸建议 `width_cm=7.2`、`height_cm=4.5`；单栏建议 `width_cm=14`、`height_cm=8`。这些是通用初始排版值，不属于论文标准；图表必须在所在栏内。若调整高度，应基于标签可读性、图种与真实数据，不能任意压扁图形。
2. 每个图表都要有明确的横纵轴含义、必要的单位、系列说明与数据来源。尽量使用直接标注或简短图例；对比图使用一致的量纲和可解释的比例尺，避免以截断坐标轴夸大变化。
3. 同一篇论文的同类图表保持一致的宽度、轴标签字号、图例顺序和视觉语言。原生图表在 Word 与 LibreOffice 中布局可能不同；检查渲染结果后，如出现坐标、图例重叠，优先简化标签／图例或改变图表结构，不降低正文排版规范。
4. 只有必要且有明确排版支持时才使用跨双栏大图；当前不能可靠跨栏时，不得偷偷把一张宽图溢出到相邻栏。应拆分为两个单栏图、改用单栏文档配置，或报告需要官方模板支持。

### 表格、公式与参考文献
1. 表格使用原生可编辑表格，表题放表上；宽度不得超过当前栏。默认使用设计中的 DocumentTable 与 TableText，表内字号不随单元格文字长度缩小。列数过多时优先拆表、重构指标或在官方模板允许时采用单栏版式。
2. 数学公式优先使用可编辑 Office Math，公式段落使用 Equation；编号右对齐，符号含义在正文说明。不得将整段公式截图来规避公式排版。复杂长公式优先在数学上合理的运算符位置分行，不缩至无法阅读。
3. 参考文献使用 Reference 命名样式，保留悬挂缩进；引用、图表编号与交叉引用保持真实对应，不能臆造文献数据。标题、图表、公式与参考文献均不使用装饰性强调。

### 每节与全文的检查顺序
1. 每节应用后，检查标题层级、段落字号和行距、图表是否超栏、图题是否贴近对应对象、表格是否跨页异常、是否发生图文碰撞。
2. 若检查发现格式问题，只对相关 Block ID 做最小修正；不允许先对整个文档执行全局字号／行距压缩。涉及设计规则的修正须维持本 Design 的全部未被用户覆盖的约束。
3. 完稿时执行现有 `check-document --final` 与页面视觉审查。真实渲染检查与视觉建议不能互相替代；若图片尺寸或图表内部布局无法可靠验证，必须标明未验证，不得宣称已经达到期刊官方排版合规。
4. Design 文字是 Agent 的约束和排版准则，**不是新的底层验证器**。仅修改本文件不等于新增自动拒绝尺寸违规的程序校验；因此所有“冻结”首先要求生成流程遵守，最终仍需以实际 DOCX／PDF 页面检查佐证。

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

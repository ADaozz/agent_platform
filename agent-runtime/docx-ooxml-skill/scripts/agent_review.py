"""Main-Agent visual review of LibreOffice-rendered DOCX pages.

The Agent opens the page PNGs and the numbered overview with ``read_file`` and
submits a structured answer. This module supplies the guidance, validates the
answer and derives the status from the reported issues. Pure Python, so the
standalone CLI can use it without the platform.
"""
import hashlib
import io
import json

GUIDANCE_VERSION = 'docx-agent-review-1'
PAGE_CHECKS = {
    'legibility': '文字是否清晰可读，字号与对比度是否合适',
    'spacing': '字间距、行距、段距是否正常',
    'tables': '表格是否完整、对齐、美观（无表格时 not_applicable）',
    'media_balance': '图片/图表与文字比例、图文排版是否合适',
    'heading_hierarchy': '标题与正文、题注之间的层级关系是否清楚',
    'equations': '公式是否完整呈现（无公式时 not_applicable）',
    'whitespace': '是否存在异常留白或拥挤',
    'completeness': '页面内容是否完整，无截断、遮挡或缺失',
}
DOCUMENT_CHECKS = {
    'consistency': '跨页风格、字体、颜色、题注格式是否一致',
    'structure': '封面、摘要、目录、正文、参考文献结构是否完整合理',
    'rhythm': '信息密度与留白节奏是否合理，是否有孤立页、异常跨页或连续低密度页',
    'design_fit': '是否符合所选设计规范或模板',
}
VERDICTS = ('ok', 'issue', 'not_applicable', 'uncertain')
SEVERITIES = ('critical', 'major', 'minor')
CONFIDENCES = ('high', 'medium', 'low')
STATUSES = ('passed', 'failed', 'uncertain', 'issues')

PAGE_GUIDANCE = """用 read_file 打开每一页的渲染截图（LibreOffice 正式分页），亲自看图后再填写审查结果；context_file 提供每页的设计规范、所属章节、页内 Block 与确定性检查结果。
1. 结论必须来自截图本身，没有打开截图不得提交该页结论。
2. 对每个检查项给出 verdict（ok / issue / not_applicable / uncertain）和截图中可见的具体证据，不写泛泛评价。
3. 每个问题写出观察到的现象和可局部执行的建议；block_id 只填 context_file 中该页列出的标识，无法确认留空。
4. 可选填写 category、severity（critical/major/minor）、confidence（high/medium/low），无法确认时省略，不得编造。
5. 无法判断时 status 用 uncertain，不得把未知当通过。不要建议删除必要内容或整体缩小字号。
6. 审查结果只是建议，不据此自动修改文档。"""

DOCUMENT_GUIDANCE = """所有页面都审查完后，用 read_file 打开整稿编号缩略图总览（每张缩略图左上角是页码），结合 context_file 中的章节页码映射和逐页审查结果，独立检查跨页问题：风格一致性、封面/摘要/目录/正文/参考文献结构、标题与题注一致性、密度与留白节奏、孤立页、异常跨页和连续低密度页。
逐页通过不等于整稿通过。每个问题列出实际页码（pages）和可局部执行的建议；不要求删除必要内容或统一缩小字号。无法确认时 status 用 uncertain。"""


class ReviewRejected(ValueError):
    """The submitted review does not follow the review structure."""


def _text(value, field, limit):
    if not isinstance(value, str) or not value.strip():
        raise ReviewRejected(f'{field} must be non-empty text')
    if len(value) > limit:
        raise ReviewRejected(f'{field} exceeds {limit} characters')
    return value.strip()


def _optional(issue, field, key, options):
    value = issue.get(key)
    if value is not None and value not in options:
        raise ReviewRejected(f'{field}.{key} must be one of {", ".join(options)} or omitted')
    return value


def _checks(value, names):
    if not isinstance(value, dict):
        raise ReviewRejected('checks must map every check to {verdict, evidence}')
    missing = [name for name in names if name not in value]
    if missing:
        raise ReviewRejected('checks missing: ' + ', '.join(missing))
    result = {}
    for name in names:
        item = value[name]
        if not isinstance(item, dict) or item.get('verdict') not in VERDICTS:
            raise ReviewRejected(f'checks.{name} must be {{verdict: {"/".join(VERDICTS)}, evidence}}')
        result[name] = dict(verdict=item['verdict'], evidence=_text(item.get('evidence'), f'checks.{name}.evidence', 800))
    return result


def _answer(answer, names, limit, summary_limit):
    if isinstance(answer, str):
        try:
            answer = json.loads(answer)
        except ValueError as exc:
            raise ReviewRejected('review is not JSON') from exc
    if not isinstance(answer, dict):
        raise ReviewRejected('review must be an object with status, summary, checks and issues')
    if answer.get('status') not in STATUSES:
        raise ReviewRejected('status must be one of ' + ', '.join(STATUSES))
    issues = answer.get('issues', [])
    if not isinstance(issues, list) or len(issues) > limit:
        raise ReviewRejected(f'issues must be a list of at most {limit} findings')
    return answer['status'], _text(answer.get('summary'), 'summary', summary_limit), _checks(answer.get('checks'), names), issues


def _issue(raw, field):
    if not isinstance(raw, dict):
        raise ReviewRejected(f'{field} must be an object')
    category = raw.get('category')
    if category is not None:
        category = _text(category, f'{field}.category', 80)
    return dict(category=category, severity=_optional(raw, field, 'severity', SEVERITIES),
                confidence=_optional(raw, field, 'confidence', CONFIDENCES),
                observation=_text(raw.get('observation'), f'{field}.observation', 1200),
                suggestion=_text(raw.get('suggestion'), f'{field}.suggestion', 1200))


def _status(status, issues, checks):
    if issues or status in ('failed', 'issues'):
        return 'issues'
    if status == 'uncertain' or any(item['verdict'] == 'uncertain' for item in checks.values()):
        return 'uncertain'
    return 'passed'


def evaluate_page(answer, block_ids):
    """Agent answer for one page -> validated review. Raises ReviewRejected."""
    status, summary, checks, raw_issues = _answer(answer, PAGE_CHECKS, 20, 1200)
    issues = []
    for index, raw in enumerate(raw_issues):
        field = f'issues[{index}]'
        item = _issue(raw, field)
        block_id = raw.get('block_id')
        if block_id is not None and not isinstance(block_id, str):
            raise ReviewRejected(f'{field}.block_id must be a string or null')
        item['block_id'] = block_id if block_id in block_ids else None
        issues.append(item)
    status = _status(status, issues, checks)
    return dict(status=status, summary=summary, checks=checks, issues=issues, passed=status == 'passed',
                suggestions=[issue['suggestion'] for issue in issues])


def evaluate_document(answer, total):
    status, summary, checks, raw_issues = _answer(answer, DOCUMENT_CHECKS, 30, 2000)
    issues = []
    for index, raw in enumerate(raw_issues):
        field = f'issues[{index}]'
        item = _issue(raw, field)
        pages = raw.get('pages')
        if not isinstance(pages, list) or not 1 <= len(pages) <= 200 or not all(type(p) is int and 1 <= p <= total for p in pages):
            raise ReviewRejected(f'{field}.pages must list actual page numbers between 1 and {total}')
        item['pages'] = sorted(set(pages))
        issues.append(item)
    status = _status(status, issues, checks)
    return dict(status=status, summary=summary, checks=checks, issues=issues, passed=status == 'passed',
                suggestions=[issue['suggestion'] for issue in issues])


def unavailable(reason):
    return dict(status='unavailable', error=dict(code='agent_cannot_inspect', message=_text(reason, 'unavailable', 200)),
                issues=[], checks={}, summary='', passed=False, suggestions=[])


def pixel_sha256(png):
    from PIL import Image
    with Image.open(io.BytesIO(png)) as image:
        return hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()


def contact_sheet(images, columns=4, width=320):
    """Numbered thumbnail overview of every rendered page; never samples."""
    from PIL import Image, ImageDraw, ImageFont
    thumbs = []
    for data in images:
        with Image.open(io.BytesIO(data)) as image:
            rgb = image.convert('RGB')
            thumbs.append(rgb.resize((width, round(rgb.height * width / rgb.width)), Image.LANCZOS))
    if not thumbs:
        raise ValueError('No rendered pages for the overview')
    gap, label = 16, 30
    cell_h = max(thumb.height for thumb in thumbs)
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * width + (columns + 1) * gap, rows * (cell_h + label) + (rows + 1) * gap), '#DDE2E8')
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('DejaVuSans-Bold.ttf', 20)
    except OSError:
        font = ImageFont.load_default()
    for index, thumb in enumerate(thumbs):
        row, column = divmod(index, columns)
        x = gap + column * (width + gap)
        y = gap + row * (cell_h + label + gap)
        draw.text((x, y), f'{index + 1:02d}', fill='#17324D', font=font)
        sheet.paste(thumb, (x, y + label))
    buffer = io.BytesIO()
    sheet.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()

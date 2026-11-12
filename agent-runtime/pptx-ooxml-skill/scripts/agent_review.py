"""Main-Agent visual review of formally rendered slides.

The Agent opens the rendered PNGs with ``read_file`` and submits a structured
answer. This module supplies the review guidance and context, validates the
answer and derives the status from confirmed issues rather than from the
reviewer's own verdict. Pure Python, so the standalone CLI can use it.
"""
import hashlib
import io
import json

GUIDANCE_VERSION = 'pptx-agent-review-1'
DIMENSIONS = {
    'composition': '页面构图是否平衡',
    'focal_point': '视觉焦点是否明确',
    'hierarchy': '信息层级是否合理',
    'legibility': '文字与背景是否清晰可读',
    'spacing': '留白和元素间距是否协调',
    'chart_quality': '图表是否专业、简约且有单位/标签/重点',
    'diagram_semantics': '流程/架构图连线是否有意义且与结构化关系一致',
    'media_balance': '图片、图标与文字比例是否合适',
    'decoration': '装饰是否多余',
    'profile_consistency': '是否与选定风格及用户实际要求一致',
    'templating': '是否模板化、过度重复或低质量拼装',
}
DECK_CATEGORIES = {
    'design_system': '整体是否属于同一设计体系',
    'transitions': '章节过渡是否自然',
    'repetition': '相邻页面构图是否过度重复',
    'card_overuse': '是否频繁使用相同的卡片布局',
    'consistency': '颜色、字体、图表是否一致',
    'density_rhythm': '页面信息密度是否有合理变化',
    'bookends': '封面与总结页是否呼应',
}
VERDICTS = ('ok', 'issue', 'not_applicable', 'uncertain')
SEVERITIES = ('critical', 'major', 'minor')
CONFIDENCES = ('high', 'medium', 'low')
MAX_TEXT = 800

SLIDE_GUIDANCE = """用 read_file 打开每一页的渲染截图（LibreOffice Impress 正式渲染），亲自看图后再填写审查结果；context_file 提供该页的设计依据、版式、页面用途、原生元素清单、图表数据、流程节点与连线和自动检查结果。
1. 观察必须来自截图本身。元素清单只用于把问题映射到元素 ID、核对图表数据与流程关系，不能代替看图；没有打开截图不得提交结论。
2. 对每个维度给出 verdict（ok / issue / not_applicable / uncertain）和具体证据。证据必须指向截图中可见的内容（文字、对象、位置、颜色），"看起来很好""设计专业"之类的泛泛评价不是证据。
3. 流程图与架构图：逐条比对截图中可见的连线和 edges 列表。可见但不在 edges 中的线、方向不明的箭头、悬空的短线、穿过文字的线都是问题。无法确认的关系 needs_verification=true 且 confidence=low。
4. element_ids 只能使用清单中存在的 ID；无法对应时留空，并用 region 标出区域（相对整张截图的归一化 [x, y, w, h]）。
5. 严重程度：critical = 内容不可读、错误或误导；major = 专业人士不会交付的明确缺陷；minor = 可选的打磨建议。
6. 留白多但焦点明确、层级清楚的极简页面不是缺陷。用户明确要求保留的版式属于已接受的设计决定，但可读性和数据正确性问题仍需报告。
7. 不打分，不建议重做整页，只给可局部执行的修改建议。
8. 风格依据：用户明确要求/调整优先，其次是本稿实际参数，再参考 design_md；未声明的配色、字号或边距不套内部默认 profile。
9. 审查结果只是建议，不据此自动修改 PPT。"""

DECK_GUIDANCE = """用 read_file 打开整套缩略图总览（每张缩略图左上角有页码），只检查跨页面的视觉设计问题：设计体系是否统一、章节过渡、相邻页构图重复、卡片布局滥用、颜色/字体/图表一致性、信息密度节奏、封面与总结页呼应。不重复逐页文字校验。
每个问题必须给出具体页码（slides，1 起算，最多 6 页），不允许笼统要求重做整个演示文稿；建议必须可局部执行。对每个维度给出 verdict 和指向具体页面的证据，不打分。"""


class ReviewRejected(ValueError):
    """The submitted review does not follow the review structure."""


def _text(value, field, limit=MAX_TEXT):
    if not isinstance(value, str) or not value.strip():
        raise ReviewRejected(f'{field} must be non-empty text')
    if len(value) > limit:
        raise ReviewRejected(f'{field} exceeds {limit} characters')
    return value.strip()


def _choice(value, field, options):
    if value not in options:
        raise ReviewRejected(f'{field} must be one of {", ".join(options)}')
    return value


def _checks(value, names):
    if not isinstance(value, dict):
        raise ReviewRejected('checks must map every dimension to {verdict, evidence}')
    missing = [name for name in names if name not in value]
    if missing:
        raise ReviewRejected('checks missing: ' + ', '.join(missing))
    result = {}
    for name in names:
        item = value[name]
        if not isinstance(item, dict):
            raise ReviewRejected(f'checks.{name} must be {{verdict, evidence}}')
        result[name] = dict(verdict=_choice(item.get('verdict'), f'checks.{name}.verdict', VERDICTS),
                            evidence=_text(item.get('evidence'), f'checks.{name}.evidence'))
    return result


def _issue_common(issue, field, categories):
    if not isinstance(issue, dict):
        raise ReviewRejected(f'{field} must be an object')
    needs = issue.get('needs_verification', False)
    if type(needs) is not bool:
        raise ReviewRejected(f'{field}.needs_verification must be true or false')
    return dict(category=_choice(issue.get('category'), f'{field}.category', tuple(categories)),
                severity=_choice(issue.get('severity'), f'{field}.severity', SEVERITIES),
                observation=_text(issue.get('observation'), f'{field}.observation'),
                reason=_text(issue.get('reason'), f'{field}.reason'),
                suggestion=_text(issue.get('suggestion'), f'{field}.suggestion'),
                confidence=_choice(issue.get('confidence'), f'{field}.confidence', CONFIDENCES),
                needs_verification=needs)


def _answer(answer, names, prefix):
    if isinstance(answer, str):
        try:
            answer = json.loads(answer)
        except ValueError as exc:
            raise ReviewRejected('review is not JSON') from exc
    if not isinstance(answer, dict):
        raise ReviewRejected('review must be an object with status, summary, checks and issues')
    issues = answer.get('issues', [])
    if not isinstance(issues, list) or len(issues) > 12:
        raise ReviewRejected('issues must be a list of at most 12 findings')
    seen = set()
    for index, issue in enumerate(issues):
        identity = issue.get('id') if isinstance(issue, dict) else None
        if not isinstance(identity, str) or not identity.startswith(prefix) or len(identity) != len(prefix) + 3 or not identity[len(prefix):].isdigit():
            raise ReviewRejected(f'issues[{index}].id must look like {prefix}001')
        if identity in seen:
            raise ReviewRejected(f'duplicate issue id {identity}')
        seen.add(identity)
    return dict(status=_choice(answer.get('status'), 'status', ('pass', 'fail', 'uncertain')),
                summary=_text(answer.get('summary'), 'summary'), checks=_checks(answer.get('checks'), names), issues=issues)


def decide(reviewer_status, issues, checks, flags):
    blocking = [issue for issue in issues if issue['severity'] in ('critical', 'major') and not issue.get('dismissed')]
    confirmed = [issue for issue in blocking if issue['confidence'] in ('high', 'medium') and not issue.get('needs_verification')]
    if confirmed:
        if reviewer_status == 'pass':
            flags.append(dict(type='status_contradiction', message='reviewer said pass but reported confirmed blocking issues'))
        return 'failed'
    if blocking or reviewer_status == 'uncertain' or any(item['verdict'] == 'uncertain' for item in checks.values()):
        return 'uncertain'
    if reviewer_status == 'fail':
        flags.append(dict(type='unsupported_failure', message='reviewer said fail without a confirmed critical or major issue'))
        return 'uncertain'
    return 'passed'


def evaluate_slide(answer, slide):
    """Agent answer -> validated, status-derived slide review. Raises ReviewRejected."""
    value = _answer(answer, DIMENSIONS, 'visual-')
    valid_ids = {element['id'] for element in slide.get('elements', [])}
    flags, issues = [], []
    for index, raw in enumerate(value['issues']):
        field = f'issues[{index}]'
        item = dict(id=raw['id'], **_issue_common(raw, field, DIMENSIONS))
        element_ids = raw.get('element_ids', [])
        if not isinstance(element_ids, list) or len(element_ids) > 8 or not all(isinstance(e, str) for e in element_ids):
            raise ReviewRejected(f'{field}.element_ids must be a list of at most 8 element IDs')
        region = raw.get('region')
        if not isinstance(region, list) or len(region) != 4 or not all(type(v) in (int, float) and 0 <= v <= 1 for v in region):
            raise ReviewRejected(f'{field}.region must be normalised [x, y, w, h] within 0..1')
        known = [identity for identity in element_ids if identity in valid_ids]
        unknown = [identity for identity in element_ids if identity not in valid_ids]
        item.update(element_ids=known, region=[float(v) for v in region])
        if unknown:
            item['unmapped_element_ids'] = unknown
            flags.append(dict(type='unknown_element_ids', issue=item['id'], ids=unknown))
        x, y, w, h = item['region']
        if w <= 0 or h <= 0 or x + w > 1.001 or y + h > 1.001:
            item['region'] = None
            item['region_invalid'] = True
            if not known:
                item['needs_verification'] = True
        item['fingerprint'] = issue_fingerprint(item)
        issues.append(item)
    status = decide(value['status'], issues, value['checks'], flags)
    return dict(status=status, reviewer_status=value['status'], summary=value['summary'], checks=value['checks'], issues=issues, flags=flags)


def evaluate_deck(answer, total):
    value = _answer(answer, DECK_CATEGORIES, 'deck-')
    flags, issues, rejected = [], [], []
    for index, raw in enumerate(value['issues']):
        field = f'issues[{index}]'
        item = dict(id=raw['id'], **_issue_common(raw, field, DECK_CATEGORIES))
        slides = raw.get('slides')
        if not isinstance(slides, list) or not 1 <= len(slides) <= 6 or not all(type(p) is int and p >= 1 for p in slides):
            raise ReviewRejected(f'{field}.slides must list 1-6 page numbers starting at 1')
        pages = sorted(set(slides))
        if any(page > total for page in pages):
            rejected.append(dict(item, slides=pages, rejected_reason='slide number outside the deck'))
            continue
        if total >= 5 and len(pages) > max(3, int(total * .6)):
            rejected.append(dict(item, slides=pages, rejected_reason='not page-specific; deck review must name concrete pages'))
            continue
        issues.append(dict(item, slides=pages))
    if rejected:
        flags.append(dict(type='rejected_issues', count=len(rejected)))
    status = decide(value['status'], issues, value['checks'], flags)
    return dict(status=status, reviewer_status=value['status'], summary=value['summary'], checks=value['checks'], issues=issues,
                rejected_issues=rejected, flags=flags)


def unavailable(reason):
    return dict(status='unavailable', error=dict(code='agent_cannot_inspect', message=_text(reason, 'unavailable', 200)),
                issues=[], checks={}, flags=[], summary='')


def issue_fingerprint(issue):
    if issue.get('element_ids'):
        anchor = ','.join(sorted(issue['element_ids']))
    elif issue.get('region'):
        x, y, w, h = issue['region']
        anchor = f'r{round((x + w / 2) * 4)}{round((y + h / 2) * 4)}'
    else:
        anchor = 'page'
    return f'{issue["category"]}:{anchor}'


def slide_title(slide):
    for element in slide.get('elements', []):
        if element.get('type') == 'text' and element.get('style_token') in ('slide_title', 'cover_title', 'section_title', 'statement'):
            return element.get('text', '')[:80]
    return next((element.get('text', '')[:80] for element in slide.get('elements', []) if element.get('type') == 'text' and element.get('text')), '')


def _round(value):
    return round(float(value), 3)


def element_context(element):
    item = dict(id=element['id'], type=element.get('type'), layer=element.get('layer'),
        geometry={key: _round(value) for key, value in (element.get('geometry') or {}).items()})
    if element.get('text'):
        item['text'] = element['text'][:240]
    style = element.get('style') or {}
    if style.get('font_size'):
        item['font'] = dict(size=style.get('font_size'), bold=style.get('bold'), color=style.get('color'))
    for key in ('shape', 'fill', 'anchor', 'component_instance', 'diagram_id', 'diagram_role', 'node_id', 'edge_id', 'source', 'target', 'relation', 'arrow', 'rotation'):
        if element.get(key) is not None:
            item[key] = element[key]
    if element.get('chart'):
        chart = element['chart']
        categories = chart.get('categories') or []
        item['chart'] = dict(type=chart.get('type'), categories=categories[:80], category_count=len(categories), unit=chart.get('unit'),
            totals=chart.get('totals'), bin_count=chart.get('bin_count'), bin_size=chart.get('bin_size'),
            series=[dict(name=s.get('name'), type=s.get('type'), secondary_axis=s.get('secondary_axis'),
                values=(s.get('values') or [])[:80], points=(s.get('points') or [])[:80],
                point_count=len(s.get('points') or s.get('values') or [])) for s in chart.get('series') or []],
            data_truncated=len(categories) > 80 or any(len(s.get('points') or s.get('values') or []) > 80 for s in chart.get('series') or []))
    if element.get('rows'):
        item['rows'] = [row[:8] for row in element['rows'][:10]]
    if element.get('native_equation'):
        source = element.get('latex') or ''
        item['equation'] = dict(format='OMML', latex=source[:2000], source_truncated=len(source) > 2000)
    if element.get('component'):
        item['component'] = dict(component_id=element['component'].get('component_id'), variant=element['component'].get('variant'))
    connector = element.get('connector')
    if connector:
        item['connector'] = dict(begin=connector.get('begin'), end=connector.get('end'),
            bound_start=(connector.get('start') or {}).get('element_id'), bound_end=(connector.get('finish') or {}).get('element_id'),
            arrow_start=connector.get('arrow_start'), arrow_end=connector.get('arrow_end'))
    return item


def diagram_context(elements):
    diagrams = {}
    for element in elements:
        identity = element.get('diagram_id')
        if not identity:
            continue
        entry = diagrams.setdefault(identity, dict(id=identity, nodes=[], edges=[]))
        if element.get('diagram_role') == 'node':
            entry['nodes'].append(dict(element_id=element['id'], node_id=element.get('node_id'), label=element.get('label'), rank=element.get('rank')))
        elif element.get('diagram_role') == 'edge':
            entry['edges'].append(dict(element_id=element['id'], source=element.get('source'), target=element.get('target'),
                relation=element.get('relation'), arrow=element.get('arrow'), label=element.get('label')))
    return list(diagrams.values())


def profile_context(profile):
    if not profile:
        return None
    return dict(id=profile.get('id'), name=profile.get('name'), description=profile.get('description'),
        colors={key: value for key, value in (profile.get('colors') or {}).items() if key != 'chart_series'},
        fonts=profile.get('fonts'), density=profile.get('density'), charts=profile.get('charts'), tables=profile.get('tables'),
        shape=profile.get('shape'))


def design_context(design):
    if not design:
        return None
    text = design.get('design_md') or ''
    return dict(source=design.get('source'), style_id=design.get('style_id'), folder_name=design.get('folder_name'),
        design_md=text[:20000], design_md_truncated=len(text) > 20000, parameters=design.get('parameters') or {},
        sha256=design.get('sha256'), precedence=design.get('precedence'),
        instruction='用户明确要求及调整优先，其次是本稿参数，再参考风格 MD。未声明的数值不套默认 profile。编辑已有 PPT 时保留原稿设计；不得仅因内部兜底 profile 而要求改成企业蓝白或统一 6% 边距。这里只输出建议，不执行修改。')


def slide_request(context):
    slide = context['slide']
    return dict(
        page=dict(index=context['index'] + 1, total=context['total'], slide_id=slide['slide_id'], layout=slide.get('layout'),
            layout_variant=slide.get('layout_variant'), purpose=context.get('intent') or '未提供', user_constraints=context.get('constraints') or []),
        design_profile=profile_context(context.get('profile')),
        selected_design=design_context(context.get('design')),
        elements=[element_context(element) for element in slide.get('elements', [])][:80],
        diagrams=diagram_context(slide.get('elements', [])),
        automatic_check_issues=[{key: issue.get(key) for key in ('type', 'severity', 'element_id', 'elements', 'message') if issue.get(key) is not None}
            for issue in context.get('technical_issues') or []][:40],
    )


def deck_request(context):
    return dict(total=len(context['slides']), design_profile=profile_context(context.get('profile')),
        selected_design=design_context(context.get('design')), slides=context['slides'])


def pixel_sha256(png):
    from PIL import Image
    with Image.open(io.BytesIO(png)) as image:
        return hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()


def contact_sheet(images, columns=4, width=480):
    """Numbered thumbnail overview of every rendered page."""
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

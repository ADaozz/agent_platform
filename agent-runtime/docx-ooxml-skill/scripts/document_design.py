"""Map explicit Design MD parameters into native Word styles, only for new files."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / 'design'
TOC_STYLE_NAMES = {'TOCHeading': 'TOC Heading', 'TOC1': 'toc 1', 'TOC2': 'toc 2', 'TOC3': 'toc 3'}
HEADING_LIST_NAME = 'Thesis headings'


def _add_heading_numbering(parts, styles, o):
    w = lambda name: o.q(o.W, name)
    part = 'word/numbering.xml'
    numbering = o.parse_xml(parts[part]) if part in parts else o.etree.Element(w('numbering'), nsmap={'w': o.W})
    abstract_id = str(1 + max((int(node.get(w('abstractNumId'))) for node in numbering.findall(w('abstractNum'))), default=-1))
    num_id = str(1 + max((int(node.get(w('numId'))) for node in numbering.findall(w('num'))), default=0))
    abstract = o.etree.Element(w('abstractNum'), {w('abstractNumId'): abstract_id})
    first_num = numbering.find(w('num'))
    numbering.insert(numbering.index(first_num) if first_num is not None else len(numbering), abstract)
    o.etree.SubElement(abstract, w('multiLevelType'), {w('val'): 'multilevel'})
    o.etree.SubElement(abstract, w('name'), {w('val'): HEADING_LIST_NAME})
    for index, pattern in enumerate(('第%1章', '%1.%2', '%1.%2.%3')):
        style_id = f'Heading{index + 1}'
        level = o.etree.SubElement(abstract, w('lvl'), {w('ilvl'): str(index)})
        for name, value in [('start', '1'), ('numFmt', 'decimal'), ('pStyle', style_id),
                            ('suff', 'space'), ('lvlText', pattern), ('lvlJc', 'left')]:
            o.etree.SubElement(level, w(name), {w('val'): value})
        style = styles.xpath('./w:style[@w:styleId=$id]/w:pPr', namespaces=o.NS, id=style_id)[0]
        control = o.etree.Element(w('numPr'))
        o.etree.SubElement(control, w('ilvl'), {w('val'): str(index)})
        o.etree.SubElement(control, w('numId'), {w('val'): num_id})
        spacing = style.find(w('spacing'))
        style.insert(style.index(spacing) if spacing is not None else 0, control)
    instance = o.etree.SubElement(numbering, w('num'), {w('numId'): num_id})
    o.etree.SubElement(instance, w('abstractNumId'), {w('val'): abstract_id})
    if part not in parts:
        rels = o.parse_xml(parts[o.DOC_RELS])
        used = {node.get('Id') for node in rels}
        rid = next(f'rId{i}' for i in range(1, len(used) + 2) if f'rId{i}' not in used)
        o.etree.SubElement(rels, o.q(o.RELS, 'Relationship'), Id=rid, Type=f'{o.R}/numbering', Target='numbering.xml')
        parts[o.DOC_RELS] = o.xml_bytes(rels)
        types = o.parse_xml(parts[o.CT_FILE])
        o.etree.SubElement(types, o.q(o.CT, 'Override'), PartName='/' + part,
                           ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml')
        parts[o.CT_FILE] = o.xml_bytes(types)
    parts[part] = o.xml_bytes(numbering)


def list_styles():
    return [dict(id=p.parent.name, design_md=str(p), reference=str(p.with_name('reference.svg')))
            for p in sorted(ROOT.glob('*/design.md'))]


def inspect_style(value):
    path = ROOT / value / 'design.md' if value in {p['id'] for p in list_styles()} else Path(value)
    text = path.read_text(encoding='utf-8')
    match = re.search(r'```docx-design\s*\n(.*?)\n```', text, re.S)
    if not match:
        raise ValueError('Design MD requires a docx-design JSON fenced block')
    config = json.loads(match[1])
    if not isinstance(config, dict) or (not {'id','page','styles','table'} <= set(config) or set(config)-{'id','page','styles','table','version','sources','components'}):
        raise ValueError('Unknown or missing design parameters')
    if not isinstance(config['id'],str) or not re.fullmatch(r'[\w.-]{1,80}',config['id']): raise ValueError('Invalid design ID')
    if not all(isinstance(config[k],dict) and config[k] for k in ('page','styles','table')): raise ValueError('Design parameters must be nonempty objects')
    return dict(config, design_md=text, source=str(path))


def apply(parts, config, o):
    page = config['page']
    if not {'width_twips','height_twips','margin_twips'} <= set(page) or set(page)-{'width_twips','height_twips','margin_twips','columns','column_space_twips'} or any(type(v) is not int for v in page.values()):
        raise ValueError('Invalid page parameters')
    w, h, m = (page[k] for k in ('width_twips', 'height_twips', 'margin_twips'))
    if not (5000 <= w <= 24000 and 5000 <= h <= 32000 and 180 <= m < min(w,h)/2):
        raise ValueError('Invalid page dimensions')
    document = o.parse_xml(parts[o.MAIN])
    for section in document.iter(o.q(o.W, 'sectPr')):
        for tag, values in [('pgSz', dict(w=w,h=h)), ('pgMar', dict(top=m,bottom=m,left=m,right=m))]:
            node = section.find(o.q(o.W,tag))
            if node is None: node = o.etree.SubElement(section,o.q(o.W,tag))
            for k,v in values.items(): node.set(o.q(o.W,k),str(v))
    columns=page.get('columns',1)
    if columns not in (1,2):raise ValueError('Only one or two columns are supported')
    for section in document.iter(o.q(o.W,'sectPr')):
        old=section.find(o.q(o.W,'cols'))
        if old is None:old=o.etree.SubElement(section,o.q(o.W,'cols'))
        old.set(o.q(o.W,'num'),str(columns));old.set(o.q(o.W,'space'),str(page.get('column_space_twips',420)))
    styles = o.parse_xml(parts['word/styles.xml'])
    allowed = {'font','size_half_points','color','line_twips','space_after_twips','space_before_twips','keep_next','east_asia_font','bold','alignment','line_rule','widow_control','hanging_indent_twips','indent_twips','first_line_chars','page_break_before'}
    for name, values in config['styles'].items():
        if not isinstance(values,dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]{0,79}',name) or set(values)-allowed:
            raise ValueError('Unsupported named style parameters')
        style = next((s for s in styles if s.get(o.q(o.W,'styleId'))==name),None)
        if style is None:
            style=o.etree.SubElement(styles,o.q(o.W,'style'),{o.q(o.W,'type'):'paragraph',o.q(o.W,'styleId'):name})
            display_name = TOC_STYLE_NAMES.get(name, name) if 'TOCHeading' in config['styles'] else name
            o.etree.SubElement(style,o.q(o.W,'name'),{o.q(o.W,'val'):display_name})
        for tag in ('rPr','pPr'):
            old=style.find(o.q(o.W,tag))
            if old is not None: style.remove(old)
        pp=o.etree.SubElement(style,o.q(o.W,'pPr')); rp=o.etree.SubElement(style,o.q(o.W,'rPr'))
        for k,v in values.items():
            if k=='east_asia_font':
                if not isinstance(v,str) or not 1<=len(v)<=100:raise ValueError('Invalid Chinese font')
                fonts=rp.find(o.q(o.W,'rFonts'))
                if fonts is None:fonts=o.etree.SubElement(rp,o.q(o.W,'rFonts'))
                fonts.set(o.q(o.W,'eastAsia'),v)
            elif k=='font':
                if not isinstance(v,str) or not 1 <= len(v) <= 100: raise ValueError('Invalid font')
                o.etree.SubElement(rp,o.q(o.W,'rFonts'),{o.q(o.W,a):v for a in ('ascii','hAnsi','eastAsia')})
            elif k=='color':
                if not isinstance(v,str) or not re.fullmatch('[0-9A-Fa-f]{6}',v): raise ValueError('Invalid colour')
                o.etree.SubElement(rp,o.q(o.W,'color'),{o.q(o.W,'val'):v})
            elif k in ('bold','widow_control'):
                if type(v) is not bool:raise ValueError('Invalid style boolean')
                o.etree.SubElement(rp if k=='bold' else pp,o.q(o.W,'b' if k=='bold' else 'widowControl'),{o.q(o.W,'val'):'1' if v else '0'})
            elif k=='alignment':
                if v not in ('left','right','center','both'):raise ValueError('Invalid alignment')
                o.etree.SubElement(pp,o.q(o.W,'jc'),{o.q(o.W,'val'):v})
            elif k=='line_rule':
                if v not in ('auto','exact','atLeast'):raise ValueError('Invalid line rule')
                spacing=pp.find(o.q(o.W,'spacing'))
                if spacing is None:spacing=o.etree.SubElement(pp,o.q(o.W,'spacing'))
                spacing.set(o.q(o.W,'lineRule'),v)
            elif k=='hanging_indent_twips':
                if type(v) is not int or not 0<=v<=2400:raise ValueError('Invalid hanging indent')
                o.etree.SubElement(pp,o.q(o.W,'ind'),{o.q(o.W,'left'):str(v),o.q(o.W,'hanging'):str(v)})
            elif k=='indent_twips':
                if type(v) is not int or not 0<=v<=2400:raise ValueError('Invalid left indent')
                o.etree.SubElement(pp,o.q(o.W,'ind'),{o.q(o.W,'left'):str(v)})
            elif k=='first_line_chars':
                if type(v) is not int or not 0 <= v <= 10:raise ValueError('Invalid first-line indent')
            elif k=='page_break_before':
                if type(v) is not bool:raise ValueError('Invalid page_break_before')
                o.etree.SubElement(pp,o.q(o.W,'pageBreakBefore'),{o.q(o.W,'val'):'1' if v else '0'})
            elif k=='keep_next':
                if type(v) is not bool: raise ValueError('Invalid keep_next')
                o.etree.SubElement(pp,o.q(o.W,'keepNext'),{o.q(o.W,'val'):'1' if v else '0'})
            else:
                if type(v) is not int or not 0 <= v <= 2400: raise ValueError('Invalid style dimension')
                if k=='size_half_points': o.etree.SubElement(rp,o.q(o.W,'sz'),{o.q(o.W,'val'):str(v)})
                else:
                    spacing=pp.find(o.q(o.W,'spacing'))
                    if spacing is None: spacing=o.etree.SubElement(pp,o.q(o.W,'spacing'))
                    spacing.set(o.q(o.W,'line' if k=='line_twips' else 'before' if k=='space_before_twips' else 'after'),str(v))
        if values.get('east_asia_font'):
            rp.find(o.q(o.W,'rFonts')).set(o.q(o.W,'eastAsia'),values['east_asia_font'])
        chars = values.get('first_line_chars')
        if chars is None and 'first_line_chars' in config['styles'].get('Normal', {}) and 'hanging_indent_twips' not in values:
            chars = 0
        if chars is not None:
            indent = pp.find(o.q(o.W, 'ind'))
            if indent is None:
                indent = o.etree.SubElement(pp, o.q(o.W, 'ind'))
            indent.set(o.q(o.W, 'firstLineChars'), str(chars * 100))
            indent.set(o.q(o.W, 'firstLine'), str(chars * values.get('size_half_points', 24) * 10))
        if name.startswith('Heading') and name[-1:] in '123456789':
            o.etree.SubElement(pp,o.q(o.W,'outlineLvl'),{o.q(o.W,'val'):str(int(name[-1])-1)})
    if config.get('components', {}).get('body', {}).get('heading_numbering'):
        _add_heading_numbering(parts, styles, o)
    # Style properties are read from JSON in any order. Write them in OOXML order.
    paragraph_order = {o.q(o.W, name): rank for rank, name in enumerate(
        ('keepNext', 'pageBreakBefore', 'widowControl', 'numPr', 'spacing', 'ind', 'jc', 'outlineLvl'))}
    for name in config['styles']:
        props = styles.xpath('./w:style[@w:styleId=$id]/w:pPr', namespaces=o.NS, id=name)[0]
        props[:] = sorted(props, key=lambda node: paragraph_order[node.tag])
    table=config['table']
    required = {'style_id', 'header_fill', 'border_color'}
    if not required <= table.keys() or table.keys() - required - {'borders'} or not isinstance(table['style_id'],str) or not re.fullmatch('[A-Za-z][A-Za-z0-9]{0,79}',table['style_id']):
        raise ValueError('Invalid table style')
    if table.get('borders', 'grid') not in ('grid', 'three_line'):
        raise ValueError('Design table borders must be grid or three_line')
    if any(not isinstance(table[k],str) or not re.fullmatch('[0-9A-Fa-f]{6}',table[k]) for k in ('header_fill','border_color')): raise ValueError('Invalid table colour')
    ts=o.etree.SubElement(styles,o.q(o.W,'style'),{o.q(o.W,'type'):'table',o.q(o.W,'styleId'):table['style_id']})
    o.etree.SubElement(ts,o.q(o.W,'name'),{o.q(o.W,'val'):table['style_id']})
    pr=o.etree.SubElement(ts,o.q(o.W,'tblPr')); borders=o.etree.SubElement(pr,o.q(o.W,'tblBorders'))
    three_line = table.get('borders') == 'three_line'
    for side in ('top','bottom','left','right','insideH','insideV'):
        attrs = {o.q(o.W, 'val'): 'nil'}
        if not three_line or side in ('top', 'bottom'):
            attrs = {o.q(o.W, 'val'): 'single', o.q(o.W, 'sz'): '12' if three_line else '4',
                     o.q(o.W, 'color'): table['border_color']}
        o.etree.SubElement(borders, o.q(o.W, side), attrs)
    conditional=o.etree.SubElement(ts,o.q(o.W,'tblStylePr'),{o.q(o.W,'type'):'firstRow'})
    cell=o.etree.SubElement(conditional,o.q(o.W,'tcPr'))
    o.etree.SubElement(cell,o.q(o.W,'shd'),{o.q(o.W,'fill'):table['header_fill']})
    parts[o.MAIN]=o.xml_bytes(document);parts['word/styles.xml']=o.xml_bytes(styles)
    return parts

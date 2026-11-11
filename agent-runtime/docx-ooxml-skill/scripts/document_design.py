"""Map explicit Design MD parameters into native Word styles, only for new files."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / 'design'


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
    if not isinstance(config, dict) or set(config) != {'id', 'page', 'styles', 'table'}:
        raise ValueError('Unknown or missing design parameters')
    if not isinstance(config['id'],str) or not re.fullmatch(r'[\w.-]{1,80}',config['id']): raise ValueError('Invalid design ID')
    if not all(isinstance(config[k],dict) and config[k] for k in ('page','styles','table')): raise ValueError('Design parameters must be nonempty objects')
    return dict(config, design_md=text, source=str(path))


def apply(parts, config, o):
    page = config['page']
    if set(page) != {'width_twips', 'height_twips', 'margin_twips'} or any(type(v) is not int for v in page.values()):
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
    styles = o.parse_xml(parts['word/styles.xml'])
    allowed = {'font','size_half_points','color','line_twips','space_after_twips','keep_next'}
    for name, values in config['styles'].items():
        if not isinstance(values,dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]{0,79}',name) or set(values)-allowed:
            raise ValueError('Unsupported named style parameters')
        style = next((s for s in styles if s.get(o.q(o.W,'styleId'))==name),None)
        if style is None:
            style=o.etree.SubElement(styles,o.q(o.W,'style'),{o.q(o.W,'type'):'paragraph',o.q(o.W,'styleId'):name})
            o.etree.SubElement(style,o.q(o.W,'name'),{o.q(o.W,'val'):name})
        for tag in ('rPr','pPr'):
            old=style.find(o.q(o.W,tag))
            if old is not None: style.remove(old)
        rp=o.etree.SubElement(style,o.q(o.W,'rPr')); pp=o.etree.SubElement(style,o.q(o.W,'pPr'))
        for k,v in values.items():
            if k=='font':
                if not isinstance(v,str) or not 1 <= len(v) <= 100: raise ValueError('Invalid font')
                o.etree.SubElement(rp,o.q(o.W,'rFonts'),{o.q(o.W,a):v for a in ('ascii','hAnsi','eastAsia')})
            elif k=='color':
                if not isinstance(v,str) or not re.fullmatch('[0-9A-Fa-f]{6}',v): raise ValueError('Invalid colour')
                o.etree.SubElement(rp,o.q(o.W,'color'),{o.q(o.W,'val'):v})
            elif k=='keep_next':
                if type(v) is not bool: raise ValueError('Invalid keep_next')
                o.etree.SubElement(pp,o.q(o.W,'keepNext'),{o.q(o.W,'val'):'1' if v else '0'})
            else:
                if type(v) is not int or not 0 <= v <= 2400: raise ValueError('Invalid style dimension')
                if k=='size_half_points': o.etree.SubElement(rp,o.q(o.W,'sz'),{o.q(o.W,'val'):str(v)})
                else:
                    spacing=pp.find(o.q(o.W,'spacing'))
                    if spacing is None: spacing=o.etree.SubElement(pp,o.q(o.W,'spacing'))
                    spacing.set(o.q(o.W,'line' if k=='line_twips' else 'after'),str(v))
        if name.startswith('Heading') and name[-1:] in '123456789':
            o.etree.SubElement(pp,o.q(o.W,'outlineLvl'),{o.q(o.W,'val'):str(int(name[-1])-1)})
    table=config['table']
    if set(table) != {'style_id','header_fill','border_color'} or not isinstance(table['style_id'],str) or not re.fullmatch('[A-Za-z][A-Za-z0-9]{0,79}',table['style_id']):
        raise ValueError('Invalid table style')
    if any(not isinstance(table[k],str) or not re.fullmatch('[0-9A-Fa-f]{6}',table[k]) for k in ('header_fill','border_color')): raise ValueError('Invalid table colour')
    ts=o.etree.SubElement(styles,o.q(o.W,'style'),{o.q(o.W,'type'):'table',o.q(o.W,'styleId'):table['style_id']})
    o.etree.SubElement(ts,o.q(o.W,'name'),{o.q(o.W,'val'):table['style_id']})
    pr=o.etree.SubElement(ts,o.q(o.W,'tblPr')); borders=o.etree.SubElement(pr,o.q(o.W,'tblBorders'))
    for side in ('top','bottom','left','right','insideH','insideV'):
        o.etree.SubElement(borders,o.q(o.W,side),{o.q(o.W,'val'):'single',o.q(o.W,'sz'):'4',o.q(o.W,'color'):table['border_color']})
    conditional=o.etree.SubElement(ts,o.q(o.W,'tblStylePr'),{o.q(o.W,'type'):'firstRow'})
    cell=o.etree.SubElement(conditional,o.q(o.W,'tcPr'))
    o.etree.SubElement(cell,o.q(o.W,'shd'),{o.q(o.W,'fill'):table['header_fill']})
    parts[o.MAIN]=o.xml_bytes(document);parts['word/styles.xml']=o.xml_bytes(styles)
    return parts

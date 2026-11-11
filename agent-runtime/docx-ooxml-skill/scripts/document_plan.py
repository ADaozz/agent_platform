"""Section-based authoring contract. No pagination or generation engine lives here."""
import json
import re

ID = re.compile(r'^[\w.-]{1,80}$')
MAX_OPERATIONS = 80
MAX_CHARACTERS = 120000
MAX_RESOURCE_BYTES = 20 * 1024 * 1024


def validate(plan):
    def ident(value):
        if not isinstance(value,str) or not ID.fullmatch(value) or value in ('.','..'): raise ValueError('Invalid plan identifier')
    if not isinstance(plan,dict) or len(json.dumps(plan,ensure_ascii=False)) > 200000:
        raise ValueError('Invalid or oversized document plan')
    if set(plan)-{'version','document_id','title','page_target','design','sections','references'} or not {'version','document_id','title','sections'} <= set(plan):
        raise ValueError('Unknown or missing plan fields')
    if type(plan['version']) is not int or plan['version'] != 1: raise ValueError('Unsupported plan version')
    ident(plan['document_id'])
    if not isinstance(plan['title'],str) or not 1<=len(plan['title'])<=500: raise ValueError('Invalid plan title')
    if 'page_target' in plan and (type(plan['page_target']) is not int or not 1<=plan['page_target']<=10000): raise ValueError('Invalid soft page target')
    if 'design' in plan and (not isinstance(plan['design'],str) or len(plan['design'])>500): raise ValueError('Invalid design reference')
    sections=plan['sections']
    if not isinstance(sections,list) or not 1<=len(sections)<=200: raise ValueError('Plan requires 1-200 sections')
    ids=set(); blocks=set(); assets=set()
    for section in sections:
        if not isinstance(section,dict) or set(section)-{'id','title','requirements','block_ids','equations','figures','tables','citations','styles'} or not {'id','title','requirements','block_ids'} <= set(section):
            raise ValueError('Unknown or missing section fields')
        ident(section['id'])
        if section['id'] in ids: raise ValueError('Duplicate section ID')
        ids.add(section['id'])
        for key in ('title','requirements'):
            if not isinstance(section[key],str) or not 1<=len(section[key])<=10000: raise ValueError('Invalid section '+key)
        for key in ('block_ids','equations','figures','tables','citations','styles'):
            values=section.get(key,[])
            if not isinstance(values,list) or len(values)>500: raise ValueError('Invalid section inventory')
            for value in values: ident(value)
            if len(values)!=len(set(values)): raise ValueError('Duplicate inventory ID')
        if not section['block_ids']: raise ValueError('Each section requires stable block IDs')
        if blocks.intersection(section['block_ids']): raise ValueError('Block IDs must belong to one section')
        blocks.update(section['block_ids'])
        for key in ('equations','figures','tables'):
            values=section.get(key,[])
            if assets.intersection(values): raise ValueError('Duplicate resource ID')
            assets.update(values)
            if not set(values)<=set(section['block_ids']): raise ValueError('Resource IDs must be planned blocks')
    references=plan.get('references',[])
    if not isinstance(references,list) or len(references)>1000: raise ValueError('Invalid reference inventory')
    refs=set()
    for reference in references:
        if not isinstance(reference,dict) or set(reference)!={'id','text'} or not isinstance(reference['text'],str) or not 1<=len(reference['text'])<=3000: raise ValueError('Invalid reference')
        ident(reference['id'])
        if reference['id'] in refs: raise ValueError('Duplicate reference')
        refs.add(reference['id'])
    if any(set(s.get('citations',[]))-refs for s in sections): raise ValueError('Unknown citation')
    return dict(ok=True,version=1,section_count=len(sections),block_count=len(blocks),page_target=plan.get('page_target'),pagination='flowing; page target is advisory')

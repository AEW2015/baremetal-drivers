#!/usr/bin/env python3
"""Maintain contextual diagram links/embeds in the existing example pages."""
import argparse,html,json,posixpath,re
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[2]
DOCS=ROOT/'docs'
BEGIN='<!-- example-architecture:start -->'
END='<!-- example-architecture:end -->'
PRACTICE=['practice/'+n for n in ('startup','corruption','exception','timer','mmu','uart','multicore')]
UPSTREAM=['upstream/'+n for n in ('crc','perf','combophy','noc','iossm','bridge','reset_mngr','reboot_mngr')]

def pages():
    catalog=json.loads((ROOT/'examples/agilex5-modular/catalog.json').read_text())
    ids={r['id'] for r in catalog['examples']}
    mapped={}
    custom={'ocram':'custom/ocram-hello','ddr':'custom/ddr-hello','ethernet':'custom/ethernet','qemu':'custom/qemu-hello'}
    for path in sorted((DOCS/'examples').glob('*.md')):
        if path.name=='README.md':continue # Public-header reference, not a lab page.
        mapped[str(path.relative_to(DOCS))]=PRACTICE if path.stem=='qemu-labs' else [custom.get(path.stem,'board/'+path.stem)]
    mapped.update({
        'examples.md':[],
        'qemu.md':['custom/qemu-hello'],
        'cross-platform.md':PRACTICE,
        'fabric-ip.md':['fabric/add','fabric/xor'],
        'partial-reconfiguration.md':['reference/pr'],
        'upstream-examples-validation.md':UPSTREAM,
        'runtime-fixes.md':UPSTREAM+['upstream/mailbox','diagnostic/smc-guard','custom/bridge-control','diagnostic/perf-zero-clock'],
        'simics.md':['upstream/'+n for n in ('hello','timer','gic','ddr')]+[r['id'] for r in catalog['examples'] if r['family']=='Legacy 25.1 Simics'],
    })
    for page,examples in mapped.items():
        if not (DOCS/page).is_file():raise ValueError('Missing example page: '+page)
        if set(examples)-ids:raise ValueError('Unknown example IDs: '+str(set(examples)-ids))
    return mapped

def section(page,examples):
    parent=posixpath.dirname(page) or '.'
    asset=posixpath.relpath('assets/architecture/design.html',parent)
    guide=posixpath.relpath('architecture.md',parent)
    selection='?example='+quote(examples[0],safe='') if examples else ''
    # Raw HTML URLs are relative to /page/index.html; Markdown URLs below are
    # resolved by MkDocs relative to the source .md file.
    prefix='../'*len(Path(page).with_suffix('').parts)
    iframe=prefix+'assets/architecture/design.html'+selection
    rendered_asset=prefix+'assets/architecture/design.html'
    links=' · '.join('<a href="'+html.escape(rendered_asset+'?example='+quote(id,safe=''),quote=True)+'" data-example-id="'+html.escape(id,quote=True)+'">'+html.escape(id)+'</a>' for id in examples)
    label='Open this example in the HPS / fabric diagram' if len(examples)==1 else 'Open the HPS / fabric example diagram'
    return '\n'.join([BEGIN,
        '['+label+']('+asset+selection+'){ .md-button }',
        '[Full architecture guide]('+guide+')','',
        '<details class="example-architecture">',
        '<summary>Show the clickable HPS / fabric diagram here</summary>',
        '<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>',
        '<p class="example-diagram-links">'+links+'</p>' if links else '<p>Select an example in the diagram to locate its hardware blocks.</p>',
        '<iframe class="example-diagram" src="'+html.escape(iframe,quote=True)+'" title="HPS and fabric diagram for '+html.escape(page,quote=True)+'" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>',
        '</details>',END])

def updated(page,text,examples):
    snippet=section(page,examples)
    pattern=re.compile(re.escape(BEGIN)+r'.*?'+re.escape(END),re.S)
    if BEGIN in text:
        if len(pattern.findall(text))!=1:raise ValueError('Invalid managed section: '+page)
        return pattern.sub(lambda _:snippet,text)
    before=re.search(r'^(?:=== |## )',text,re.M)
    position=before.start() if before else len(text.rstrip())
    return text[:position].rstrip()+'\n\n'+snippet+'\n\n'+text[position:].lstrip()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    mapped=pages()
    for page,examples in mapped.items():
        path=DOCS/page;text=path.read_text();expected=updated(page,text,examples)
        if a.check:
            if text!=expected:raise SystemExit('Stale example diagram links: '+page+'; run tools/architecture/link_example_pages.py')
        elif text!=expected:path.write_text(expected)
    print(('Verified' if a.check else 'Linked')+' contextual diagrams on '+str(len(mapped))+' example pages')
if __name__=='__main__':main()

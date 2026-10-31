#!/usr/bin/env python3
"""Validate the example inventory and generate the tutorial's platform matrix."""
import argparse,collections,json,os
from urllib.parse import quote
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
STATUSES={'pass','partial','fail','not-run','not-supported','compile-only','reference','blocked'}
PLATFORMS=('qemu','simics','hardware')

def load():
    catalog=json.loads((ROOT/'catalog.json').read_text())
    seen=set()
    for row in catalog['examples']:
        if row['id'] in seen:raise ValueError('Duplicate example ID: '+row['id'])
        seen.add(row['id'])
        if not (REPO/row['source']).exists():raise ValueError('Missing source: '+row['source'])
        if set(row['platforms'])!=set(PLATFORMS):raise ValueError('Three platform statuses required')
        for result in row['platforms'].values():
            if result['status'] not in STATUSES:raise ValueError('Invalid status')
            if result['status'] in ('pass','partial','fail') and not result.get('evidence'):
                raise ValueError('Execution result requires evidence: '+row['id'])
            if result.get('evidence') and not (ROOT/result['evidence']).exists():
                raise ValueError('Missing evidence: '+result['evidence'])
            case_names=result.get('cases',[]) or ([result['case']] if result.get('case') else [])
            if case_names and (not isinstance(case_names,list) or len(case_names)!=len(set(case_names))):
                raise ValueError('Evidence cases must be a distinct list: '+row['id'])
            for case_name in case_names:
                evidence=json.loads((ROOT/result['evidence']).read_text())
                cases=[t for t in evidence['tests'] if t['name']==case_name]
                if len(cases)!=1:raise ValueError('Missing/ambiguous evidence case: '+row['id'])
                observed=cases[0].get('status')
                if observed is None:observed='pass' if cases[0]['passed'] else 'fail'
                if observed!=result['status']:raise ValueError('Status contradicts evidence: '+row['id'])
    expected={p.parent.name for p in (REPO/'examples').glob('*/CMakeLists.txt')}
    actual={r['id'].split('/',1)[1] for r in catalog['examples'] if r['family']=='Current upstream'}
    if actual!=expected:raise ValueError('Upstream inventory differs: '+str(actual^expected))
    return catalog

def render(catalog):
    rows=catalog['examples']
    text=['# Example catalog and platform results','',
      'Generated from the [machine-readable catalog](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/catalog.json).', '',
      'Each row is one named exercise or implementation. Legacy, board-adapted and current implementations count separately. A bundled exercise counts once; individual assertions, negative variants, help commands and debugger walkthroughs are excluded.', '',
      'PASS records execution of the referenced artifacts, not a promise about every future rebuild. Partial results do not count as passes. “Not run” is not a claim that a platform supports the example. Software/RTL co-simulation is recorded separately from these three targets.', '',
      '| Platform | Recorded PASS | Partial | Failed |',
      '|---|---:|---:|---:|']
    for platform in PLATFORMS:
        counts=collections.Counter(r['platforms'][platform]['status'] for r in rows)
        text.append(f"| {platform} | {counts['pass']} | {counts['partial']} | {counts['fail']} |")
    text+=['',f'Inventory: **{len(rows)} rows**. Results include historical versions; see each row’s scope and evidence.','']
    for family in dict.fromkeys(r['family'] for r in rows):
        text+=['## '+family,'','| Example | QEMU | Simics | Hardware | Scope |','|---|---|---|---|---|']
        for row in rows:
            if row['family']!=family:continue
            values=[]
            for platform in PLATFORMS:
                result=row['platforms'][platform];label=result['status'].upper()
                if result.get('evidence'):label=f"[{label}](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/{result['evidence']})"
                values.append(label)
            title='['+row['title']+'](assets/architecture/design.html?example='+quote(row['id'],safe='')+')'
            text.append('| '+title+' | '+' | '.join(values)+' | '+row['scope'].replace('|','/')+' |')
        text.append('')
    return '\n'.join(text).rstrip()+'\n'

def checklist(catalog, target):
    """Use the same evidence-backed statuses in both GitHub entry points."""
    def link(path):
        return Path(os.path.relpath(path, target.parent)).as_posix()
    labels={'pass':'✅ Passed','partial':'⚠️ Partial','fail':'❌ Failed',
            'not-run':'⬜ Not tested','not-supported':'➖ Unsupported',
            'compile-only':'🔨 Build only','reference':'📖 Reference','blocked':'🚧 Blocked'}
    rows=catalog['examples']
    lines=['## Example platform checklist','',
      '**✅ = recorded execution passed.** ⬜ = not tested, not a promise of support. '
      '⚠️ = partial, ❌ = failed, ➖ = unsupported, 🔨 = build only, 📖 = reference, 🚧 = blocked.','',
      'Checkmarks apply to the linked evidence and the stated scope, including historical versions. '
      'Controller IDs, simulator models and physical transfers have different coverage.','',
      '| QEMU | SIMICS | Agilex 5 Modular hardware |',
      '|:---:|:---:|:---:|',
      '| '+' | '.join(f"**{sum(r['platforms'][p]['status']=='pass' for r in rows)} / {len(rows)} ✅**" for p in PLATFORMS)+' |','',
      f"Expand a group for every example. [Detailed scope and results]({link(REPO/'docs/example-catalog.md')}).",'']
    for family in dict.fromkeys(r['family'] for r in rows):
        group=[r for r in rows if r['family']==family]
        lines+=['<details>',f'<summary><strong>{family}</strong> · {len(group)} examples</summary>','',
                '| Example / source | QEMU | SIMICS | Hardware |','|---|:---:|:---:|:---:|']
        for row in group:
            values=[]
            for platform in PLATFORMS:
                result=row['platforms'][platform];label=labels[result['status']]
                if result.get('evidence'):label=f"[{label}]({link(ROOT/result['evidence'])})"
                values.append(label)
            lines.append(f"| [`{row['id']}`]({link(REPO/row['source'])}) | "+' | '.join(values)+' |')
        lines+=['','</details>','']
    lines += [f"**USB work in progress:** the [bare-metal USB lab]({link(ROOT/'usb-bringup/README.md')}) "
              'boots U-Boot on hardware, but USB controller readiness still fails. Hub enumeration, '
              'mouse input, flash reads and USB-Ethernet traffic are pending.','',
              'Maintainers: regenerate these checklists with '
              '`python3 examples/agilex5-modular/catalog.py`; CI checks for drift.']
    return '\n'.join(lines)+'\n'

def update_readme(catalog, target, check):
    start='<!-- example-platform-checklist:start -->'
    end='<!-- example-platform-checklist:end -->'
    content=target.read_text()
    block=start+'\n'+checklist(catalog,target)+end
    if start in content:
        before,rest=content.split(start,1)
        _,after=rest.split(end,1)
        updated=before+block+after
    else:
        marker='\n---\n' if target==REPO/'README.md' else '\n## Build\n'
        if marker not in content:raise ValueError('Missing README insertion marker: '+str(target))
        updated=content.replace(marker,'\n'+block+'\n'+marker,1)
    if check:
        if content!=updated:raise SystemExit('README checklist is stale: '+str(target))
    else:target.write_text(updated)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    catalog=load();output=render(catalog);target=REPO/'docs/example-catalog.md'
    if a.check:
        if not target.exists() or target.read_text()!=output:raise SystemExit('Catalog page is stale: run python3 catalog.py')
    else:target.write_text(output)
    for readme in (REPO/'README.md',ROOT/'README.md'):
        update_readme(catalog,readme,a.check)
    for platform in PLATFORMS:
        print(platform+': '+str(dict(collections.Counter(r['platforms'][platform]['status'] for r in catalog['examples']))))
if __name__=='__main__':main()

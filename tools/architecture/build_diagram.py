#!/usr/bin/env python3
"""Render the TRM-based Agilex architecture using pinned FPGA Project Analyzer.

This is an explicit educational adapter, not a Quartus netlist extractor. The
ADD/XOR RTL hierarchy is extracted by upstream fpalib, with Vivado disabled.
"""
import argparse,copy,hashlib,json,sys,tempfile
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
VENDOR=ROOT/'tools/vendor/fpga-project-analyzer'
LAB=ROOT/'examples/agilex5-modular'
OUT=ROOT/'docs/assets/architecture'
sys.path.insert(0,str(VENDOR))
from fpalib import build as analyzer,model as M,viewer

SITE='https://aew2015.github.io/baremetal-drivers/'
GITHUB='https://github.com/AEW2015/baremetal-drivers/'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def guide(row):
    id=row['id'];name=id.split('/',1)[1]
    if id.startswith('board/') and name in ('core','dma','gic','mmu','som','som-i2c','som-i3c','interfaces','mailbox','multicore','vendor-uart','vendor-ccu','vendor-clkmgr','vendor-smmu','vendor-ecc'):return SITE+'examples/'+name+'/'
    if id.startswith('config/'):return SITE+'config-audit/'
    if id.startswith('integration/simics-rtl-'):return SITE+'simics-rtl/'
    if id.startswith('model/'):return SITE+'model-audit/'
    if id.startswith('practice/'):return SITE+'cross-platform/'
    if id.startswith('legacy/'):return SITE+'simics/'
    if id.startswith('fabric/'):return SITE+'fabric-ip/'
    if id=='reference/pr':return SITE+'partial-reconfiguration/'
    if id=='custom/ethernet':return SITE+'examples/ethernet/'
    if id=='custom/ocram-hello':return SITE+'examples/ocram/'
    if id=='custom/ddr-hello':return SITE+'examples/ddr/'
    if id=='custom/qemu-hello':return SITE+'examples/qemu/'
    if id.startswith('upstream/') and name in ('perf','mailbox','bridge','reboot_mngr','iossm'):return SITE+'runtime-fixes/'
    if id.startswith('upstream/'):return SITE+'upstream-examples-validation/'
    return SITE+'example-catalog/'

def build():
    spec=json.loads((HERE/'agilex5.json').read_text())
    trm_layout=json.loads((HERE/'trm-layout.json').read_text())
    catalog=json.loads((LAB/'catalog.json').read_text())
    ids={r['id'] for r in catalog['examples']}
    if ids!=set(spec['example_blocks']):raise ValueError('Catalog mappings differ: '+str(ids^set(spec['example_blocks'])))
    d=M.new_design('Agilex 5 Modular example architecture');d['top']='arch:root'
    d['defs'][d['top']]=M.new_def('Agilex 5 Modular ES','hier')
    info={n['path']:n for n in spec['nodes']}
    if len(info)!=len(spec['nodes']):raise ValueError('Duplicate architecture paths')
    for ref in spec['documents'].values():
        url=urlsplit(ref['url'])
        if ref['kind']=='trm' and (url.netloc!='docs.altera.com' or '/814346/26.1.1/' not in url.path or parse_qs(url.query).get('contentId')!=[ref['content_id']]):
            raise ValueError('Invalid direct TRM topic: '+ref['title'])
    roots={path for path in info if path.count('/')==1}
    if not roots <= {shape['path'] for shape in trm_layout['shapes']}:
        raise ValueError('Every root subsystem needs a visible overview target for Up navigation')
    for shape in trm_layout['shapes']:
        if shape['path'] not in info:raise ValueError('Unknown TRM diagram target: '+shape['path'])
    for node in spec['nodes']:
        path=node['path'];parent,name=path.rsplit('/',1);parent=parent or '/'
        if parent!='/' and parent not in info:raise ValueError('Missing parent: '+parent)
        key='arch:'+path
        params={'Scope':node['scope']}
        if node.get('address'):params['Address context']=node['address']
        d['defs'][key]=M.new_def(node['title'],'ip',params=params)
        if node.get('source'):d['defs'][key]['src']={'file':node['source']}
        for ref in node.get('documents',[]):
            if ref not in spec['documents']:raise ValueError('Unknown TRM reference: '+ref)
        if path.startswith('/HPS') and not node.get('documents'):raise ValueError('Missing direct TRM reference: '+path)
    for node in spec['nodes']:
        parent,name=node['path'].rsplit('/',1)
        pd=d['defs']['arch:'+parent] if parent else d['defs'][d['top']]
        pd['insts'].append({'name':name,'def':'arch:'+node['path']})
        if pd['insts']:pd['kind']='hier'
    def get(path):return d['defs'][d['top'] if path=='/' else 'arch:'+path]
    def pin(definition,name,direction):
        existing=next((p for p in definition['pins'] if p['name']==name),None)
        if existing and existing['dir']!=direction:raise ValueError('Direction conflict: '+name)
        if not existing:definition['pins'].append(M.pin(name,direction,'bus',bus='functional path'))
    for edge in spec['connections']:
        level=edge['level'];pd=get(level)
        if len(edge['ends'])<2:raise ValueError('Net needs endpoints')
        for i,(inst,port) in enumerate(edge['ends']):
            endpoint=get((level.rstrip('/')+'/'+inst) if inst else level)
            # Boundary inputs are sources inside that hierarchy.
            direction=('in' if i==0 else 'out') if not inst else ('out' if i==0 else 'in')
            pin(endpoint,port,direction)
        pd['nets'].append({'name':edge['name'],'kind':'bus','ends':edge['ends']})
    # Parse our real RTL with the requested tool; do not apply Vivado pin/DRC
    # findings to a Quartus component, or claim this is Quartus elaboration.
    with tempfile.TemporaryDirectory() as temp:
        rtl=analyzer.build(str(LAB/'fabric'),temp,top='lab_ip',use_vivado='off',srcs=['rtl'])
    rtl=copy.deepcopy(rtl)
    for definition in rtl['defs'].values():
        if definition.get('src'):
            definition['src']['file']='examples/agilex5-modular/fabric/'+definition['src']['file']
    d['defs'].update(rtl['defs'])
    lab_path='/Fabric/Lab_proposed/lab_ip'
    get(lab_path)['impl']=rtl['top']
    # Register ABI is authored from lab_driver.h and the case decode in lab_ip.sv.
    registers=[('0x00','ID','RO','LAB1 identification'),('0x04','ABI','RO','ABI version 1.0'),('0x08','PERSONA','RO','ADD1 / XOR1; zero while quiesced'),('0x0c','CONTROL','RW','START bit 0; QUIESCE bit 1'),('0x10','STATUS','RW1C / RO','DONE bit 0; QUIESCE bit 1; REJECTED bit 2'),('0x14','A','RW','Operand A, byte enables supported'),('0x18','B','RW','Operand B, byte enables supported'),('0x1c','RESULT','RO','Captured result'),('0x20','SEQUENCE','RO','Accepted-operation count')]
    get(lab_path)['regs']=[{'off':o,'name':n,'acc':a,'desc':text,'size':4} for o,n,a,text in registers]
    examples=[]
    for row in catalog['examples']:
        item=copy.deepcopy(row);item['blocks']=spec['example_blocks'][row['id']]
        for path in item['blocks']:
            if path not in info:raise ValueError('Unknown example block: '+path)
        item['guide_url']=guide(row);item['source_url']=GITHUB+'tree/main/'+row['source']
        for result in item['platforms'].values():
            if result.get('evidence'):result['evidence_url']=GITHUB+'tree/main/examples/agilex5-modular/'+result['evidence']
        examples.append(item)
    d['meta']={'name':'Agilex 5 examples','part':'Modular ES · A5ED065 R0','tool':'TRM adapter',
        'sources':[{'kind':'TRM + bench profile','path':'tools/architecture/agilex5.json'},{'kind':'RTL parsed by FPGA Project Analyzer','path':'examples/agilex5-modular/fabric/rtl'}],
        'source_url_base':GITHUB+'blob/main/'}
    d['integration']={'scope':spec['scope'],'blocks':info,'examples':examples,'sources':spec['sources'],
        'documents':spec['documents'],'aliases':spec['aliases'],'trm_layout':trm_layout,'reference_index':spec['reference_index'],
        'tool':json.loads((VENDOR/'UPSTREAM.json').read_text())['commit'],'catalog_sha256':digest(LAB/'catalog.json')}
    d['findings']=[];d['annotations']=[]
    notes={'notes':{n['path']:' '.join(n['role'].split()[:7])+('…' if len(n['role'].split())>7 else '') for n in spec['nodes']},'flows':spec['flows']}
    errors=viewer.check_overlay(d,notes)
    if errors:raise ValueError(errors)
    return d,notes

def render(d,notes):
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'design.html';viewer.render(d,str(path),notes);html=path.read_text()
    def replace(old,new):
        nonlocal html
        if html.count(old)!=1:raise ValueError('Pinned viewer hook changed: '+old[:70])
        html=html.replace(old,new,1)
    replace('</head>','<style>'+ (HERE/'explorer.css').read_text()+'</style>\n</head>')
    replace('<main id="main">',(HERE/'explorer-bar.html').read_text()+'\n<main id="main">')
    replace('  P.innerHTML = h; P.hidden = false;','  if (s.type === "inst") h += architectureDetails(s.full);\n  P.innerHTML = h; P.hidden = false;\n  wireArchitectureButtons(P);')
    replace('function srcLink(src) {','function srcLink(src) {\n  if (src && src.file && D.meta.source_url_base) return `<a target="_blank" rel="noopener" href="${esc(D.meta.source_url_base + src.file + (src.line ? "#L" + src.line : ""))}">${esc(src.file)}${src.line ? ":" + src.line : ""}</a>`;')
    replace('window.__fpa = {go, select, state: S};',(HERE/'explorer.js').read_text()+'\n'+(HERE/'trm-overview.js').read_text()+'\nwindow.__fpa = {go, select, state: S, openBlock, chooseExample};')
    replace('go(start);','initializeExplorer();\ngo(start);\nif (q.get("example")) chooseExample(q.get("example"));')
    replace('  window.__fpa_ready = true;','  window.__fpa_ready = true;\n  decorateArchitecture();\n  updateNavigationControls();')
    replace('  if (!defAt(parts)) parts = [];','  parts = normalizeArchitecturePath(parts);\n  if (!defAt(parts)) parts = [];\n  rememberNavigation(parts);')
    old_reveal='''function reveal(p) {
  const parts = p.split("/").filter(Boolean);
  let k = parts.length;
  while (k > 0 && !defAt(parts.slice(0, k))) k--;
  const target = parts.slice(0, k);
  go(target.slice(0, -1), true);
  setTimeout(() => { const nm = target[target.length - 1]; const m = metaFor(nm); if (m) select(pick(m, nm)); }, 60);
}'''
    replace(old_reveal,'''function reveal(p) {
  const parts = normalizeArchitecturePath(p.split("/").filter(Boolean));
  while (parts.length && !defAt(parts)) parts.pop();
  if (parts.length) openBlock("/" + parts.join("/")); else go([]);
}''')
    replace('async function render(refit) {','async function render(refit) {\n  if (!S.path.length) { renderTRMOverview(); return; }')
    replace('  panel();\n  if (s && s.type === "inst") keepVisible','  panel();\n  updateNavigationControls();\n  if (s && s.type === "inst") keepVisible')
    replace('if (drillable(cd)) h += `<button class="open" onclick="window.__fpa.go(${esc(JSON.stringify(S.path.concat(inst.name)))})">Open ▸</button> `;',
            'if (drillable(cd)) h += `<button class="open" data-open-block="${esc(full)}">Open ▸</button> `;')
    # Initial deep links and fast navigation can start overlapping ELK layouts.
    # Discard an older result rather than drawing it with the newer global G.
    replace('  G = build(S.path);','  const requestedGraph = build(S.path);\n  G = requestedGraph;')
    replace('  LAID = await layout(G);','  const requestedLayout = await layout(requestedGraph);\n  if (G !== requestedGraph) return;\n  LAID = requestedLayout;')
    replace('m.tool ? "Vivado " + m.tool : ""','m.tool || ""')
    licenses=(VENDOR/'LICENSE').read_text()+'\n\n'+(VENDOR/'fpalib/assets/vendor/ELK-LICENSE.md').read_text()
    replace('</body>','<script type="text/plain" id="third-party-licenses">'+licenses.replace('<','&lt;')+'</script>\n</body>')
    return html

def outputs():
    d,notes=build();html=render(d,notes)
    design=viewer.merge_overlay(d,notes)
    result={'design.html':html,'design.json':json.dumps(design,indent=2)+'\n',
        'MIT-LICENSE.txt':(VENDOR/'LICENSE').read_text(),'ELK-LICENSE.txt':(VENDOR/'fpalib/assets/vendor/ELK-LICENSE.md').read_text(),
        'THIRD_PARTY.txt':'Agilex architecture explorer\n\nRenderer and RTL parser: FPGA Project Analyzer, MIT, copyright 2026 Abdullah AlNafisah.\nhttps://github.com/al-nafisah/fpga-project-analyzer\nPinned commit: '+d['integration']['tool']+'\n\nLayout: elkjs 0.10.0 (Eclipse Layout Kernel), EPL-2.0.\nhttps://github.com/kieler/elkjs\n\nSee MIT-LICENSE.txt and ELK-LICENSE.txt. Full license texts are also embedded in design.html.\n\nThe renderer is reused through its public Python model API. HPS architecture and example associations are manually curated from the Altera TRM and repository sources; they are not a Quartus netlist extraction. Only the ADD/XOR RTL hierarchy is parsed. No Vivado constraints or DRC findings are asserted for this Quartus component.\n'}
    sources=[HERE/'agilex5.json',HERE/'trm-layout.json',HERE/'trm-overview.js',HERE/'build_diagram.py',HERE/'explorer.js',HERE/'explorer.css',HERE/'explorer-bar.html',LAB/'catalog.json',LAB/'fabric/rtl/lab_ip.sv',LAB/'fabric/rtl/lab_persona.sv',LAB/'fabric/lab_driver.h']
    metadata={'analyzer_commit':d['integration']['tool'],'nodes':len(d['integration']['blocks']),'catalog_entries':len(d['integration']['examples']),
        'scope':d['integration']['scope'],'sources_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'outputs_sha256':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in result.items()}}
    result['build.json']=json.dumps(metadata,indent=2)+'\n'
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    upstream=json.loads((VENDOR/'UPSTREAM.json').read_text())
    for path,expected in upstream['files_sha256'].items():
        if digest(VENDOR/path)!=expected:raise ValueError('Vendored analyzer changed: '+path)
    files=outputs();OUT.mkdir(parents=True,exist_ok=True)
    for name,text in files.items():
        path=OUT/name
        if a.check:
            if not path.is_file() or path.read_text()!=text:raise SystemExit('Stale diagram: '+name+'; run python3 tools/architecture/build_diagram.py')
        else:path.write_text(text)
    metadata=json.loads(files['build.json'])
    print(('Verified' if a.check else 'Rendered')+f" architecture: {metadata['nodes']} blocks, {metadata['catalog_entries']} mapped examples, parsed ADD/XOR RTL")
if __name__=='__main__':main()

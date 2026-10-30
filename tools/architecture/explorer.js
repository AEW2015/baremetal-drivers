/* Agilex adapter UI. Upstream renderer remains unmodified in tools/vendor. */
const ARCH = D.integration;
let chosenExample = "", chosenPlatform = "all";
let navigationTrail = [], settledView = null, returningToView = false;
const platformTitle = {qemu:"QEMU",simics:"Simics",hardware:"Hardware"};
function examplesAt(path) {
  return ARCH.examples.filter(e => e.blocks.some(b => b === path || b.startsWith(path + "/")));
}
function coverageAt(path) {
  // Parsed RTL inherits its containing lab's association. Architecture blocks
  // never inherit a parent's associations: HPS DDR cannot qualify fabric DDR.
  while(path && !ARCH.blocks[path])path=path.slice(0,path.lastIndexOf('/'));
  return examplesAt(path);
}
function safeLink(url, label, cls="") {
  if (!/^https:\/\//.test(url || "")) return esc(label);
  return `<a class="${esc(cls)}" target="_blank" rel="noopener" href="${esc(url)}">${esc(label)}</a>`;
}
function exampleCard(e) {
  const platforms = chosenPlatform === "all" ? ["qemu","simics","hardware"] : [chosenPlatform];
  const results = platforms.map(p => {
    const r=e.platforms[p],label=platformTitle[p]+": "+r.status.toUpperCase();
    return r.evidence_url ? safeLink(r.evidence_url,label,"result-badge result-"+r.status) : `<span class="result-badge result-${esc(r.status)}">${esc(label)}</span>`;
  }).join("");
  return `<article class="example-card" data-example-id="${esc(e.id)}"><div class="example-family">${esc(e.family)}</div><div class="example-title">${esc(e.id)} · ${esc(e.title)}</div>${results}<div class="example-scope">${esc(e.scope)}</div><div class="example-links">${safeLink(e.guide_url,"Tutorial / expected output ↗")}${safeLink(e.source_url,"Source ↗")}</div><div class="block-links">${e.blocks.map(b=>`<button type="button" data-arch-block="${esc(b)}">${esc(b.split("/").pop())}</button>`).join("")}</div></article>`;
}
function architectureDetails(path) {
  let ancestor=path;
  while (ancestor && !ARCH.blocks[ancestor]) ancestor=ancestor.slice(0,ancestor.lastIndexOf("/"));
  const info=ARCH.blocks[ancestor];
  const associated=coverageAt(path);
  let examples=associated;
  if (chosenExample) examples=examples.filter(e=>e.id===chosenExample);
  const docs = documentsAt(path);
  if (info && info.address) docs.push(ARCH.sources.address_map);
  let h=`<section class="architecture-detail"><h3>Example explorer</h3>`;
  h+=associated.length ? `<p class="coverage-summary">${associated.length} associated example${associated.length===1?'':'s'} in this block or its children</p>` : `<p class="coverage-empty"><b>◇ No example yet</b><br>No catalog example is mapped to this block or its children.</p>`;
  if(info) h+=`<div class="context"><b>${esc(info.scope)}</b><br>${esc(info.role)}${info.address ? "<br>"+esc(info.address):""}</div>`;
  if(path.startsWith("/Fabric/Lab_proposed")) h+=`<p>Only this core's hierarchy is parsed from repository RTL. Its proposed LWHPS2FPGA deployment has not been fitted or run on the board, and Simics is not running this RTL.</p>`;
  h+=`<h3>Direct reference pages</h3><p class="direct-trm-links">${docs.map(d=>safeLink(d.url,d.title+" ↗")).join("<br>")}</p>`;
  h+=`<div class="block-links"><button type="button" data-show-hierarchy="${esc(path)}">Show in hierarchy</button></div>`;
  h+=`<p class="navigation-explanation">Click selects a block. Open enters a subsystem. Up leaves the diagram level shown in the toolbar.</p>`;
  h+=`<h3>${examples.length} related example${examples.length===1?"":"s"}</h3>`;
  h+=examples.map(exampleCard).join("") || (associated.length ? "<p>No example matches the current filter. Choose All examples to browse this block.</p>" : "<p>This block remains available for architecture and reference browsing.</p>");
  h+=`<p class="architecture-credit">Rendered with ${safeLink("https://github.com/al-nafisah/fpga-project-analyzer","FPGA Project Analyzer")} (MIT), layout by ELK (EPL-2.0). ${safeLink("https://aew2015.github.io/baremetal-drivers/assets/architecture/THIRD_PARTY.txt","Licenses and provenance ↗")}</p></section>`;
  return h;
}
function wireArchitectureButtons(parent) {
  parent.querySelectorAll("[data-arch-block]").forEach(b=>b.onclick=()=>openBlock(b.dataset.archBlock));
  parent.querySelectorAll("[data-open-block]").forEach(b=>b.onclick=()=>go(b.dataset.openBlock.split('/').filter(Boolean)));
  parent.querySelectorAll("[data-open-level]").forEach(b=>b.onclick=()=>go(b.dataset.openLevel.split('/').filter(Boolean)));
  parent.querySelectorAll("[data-show-hierarchy]").forEach(b=>b.onclick=()=>openBlock(b.dataset.showHierarchy));
}
async function openBlock(path) {
  const parts=normalizeArchitecturePath(path.split("/").filter(Boolean));
  if(!defAt(parts)) throw new Error("Unknown block: "+path);
  go(parts.slice(0,-1));
  const expected=parts.slice(0,-1).join("/");
  for(let i=0;i<200;i++) {
    await new Promise(resolve=>setTimeout(resolve,10));
    if(S.path.join("/")!==expected)return; // A later user navigation won.
    if(window.__fpa_ready && S.path.join("/")===expected) {
      const m=Object.values(G.meta).find(m=>m.type==='inst' && m.full==='/'+parts.join('/')) || metaFor(parts[parts.length-1]);
      if(m) {select(pick(m,parts[parts.length-1]));fit();decorateArchitecture();}
      return;
    }
  }
  throw new Error("Diagram layout did not complete");
}
async function chooseExample(id) {
  const e=ARCH.examples.find(e=>e.id===id);
  if(id && !e) return;
  chosenExample=id;$("example-picker").value=id;
  const url=new URL(location.href);url.searchParams.delete("sel");
  if(id)url.searchParams.set("example",id);else url.searchParams.delete("example");
  history.replaceState(null,"",url);
  if(e) await openBlock(e.blocks[0]);else {panel();decorateArchitecture();}
}
function decorateArchitecture() {
  const e=ARCH.examples.find(e=>e.id===chosenExample);
  Object.entries(G.meta).forEach(([id,m])=>{
    if(m.type!=="inst")return;
    const node=[...vp.querySelectorAll(".node")].find(n=>n.dataset.id===id);
    if(!node)return;
    node.setAttribute("role","button");node.setAttribute("tabindex","0");
    node.setAttribute("aria-label",m.full+" — click for examples; double-click to open");
    const covered=coverageAt(m.full).length>0;
    node.classList.toggle('no-example',!covered);
    node.dataset.exampleCoverage=covered?'associated':'none';
    if(!covered && !node.querySelector('.no-example-marker')){
      const box=node.querySelector('.box').getBBox();
      const marker=el('text',{x:box.x+box.width-4,y:box.y+12,'text-anchor':'end',class:'no-example-marker','aria-hidden':'true'},node);
      marker.textContent='◇';
      el('title',{},marker).textContent='No example yet';
    }
    node.classList.toggle("example-hit",!!e && e.blocks.some(b=>b===m.full || b.startsWith(m.full+"/") || m.full.startsWith(b+"/")));
    node.onkeydown=event=>{
      if(event.key==="Enter"){event.preventDefault();event.stopPropagation();select(pick(m,m.inst.name));}
      if(event.key===" "){event.preventDefault();event.stopPropagation();if(drillable(m.def))go(m.full.split('/').filter(Boolean));}
    };
  });
  $("example-count").textContent=(chosenExample ? "Selected: "+chosenExample : ARCH.examples.length+" catalog entries")+" · "+Object.keys(ARCH.blocks).length+" blocks";
}
function fillExamplePicker(query="") {
  const text=query.toLowerCase(),matches=ARCH.examples.filter(e=>(e.id+" "+e.title+" "+e.family+" "+e.blocks.join(" ")).toLowerCase().includes(text));
  $("example-picker").innerHTML=`<option value="">All examples (${matches.length})</option>`+matches.map(e=>`<option value="${esc(e.id)}">${esc(e.id+" · "+e.title)}</option>`).join("");
  if(matches.some(e=>e.id===chosenExample))$("example-picker").value=chosenExample;
  $("example-count").textContent=matches.length+" of "+ARCH.examples.length+" examples";
}
function initializeExplorer() {
  fillExamplePicker();
  $("example-picker").onchange=event=>chooseExample(event.target.value);
  $("example-search").oninput=event=>fillExamplePicker(event.target.value);
  $("platform-picker").onchange=event=>{chosenPlatform=event.target.value;panel();};
  $("architecture-overview").onclick=goSystem;
  $("architecture-up").onclick=goUp;
  $("architecture-back").onclick=goBack;
  settledView={path:[],example:"",selected:null};
  new ResizeObserver(()=>{$("main").style.top=$("architecture-bar").getBoundingClientRect().bottom+"px";fit();}).observe($("architecture-bar"));
  addEventListener('keydown',event=>{
    if(event.target.closest('input,select,textarea'))return;
    if(event.altKey && event.key==='ArrowLeft'){event.preventDefault();goBack();}
    if(event.altKey && event.key==='ArrowUp'){event.preventDefault();goUp();}
  });
}

function normalizeArchitecturePath(parts) {
  let path='/'+parts.join('/');
  for(const [oldPath,newPath] of Object.entries(ARCH.aliases).sort((a,b)=>b[0].length-a[0].length)){
    if(path===oldPath || path.startsWith(oldPath+'/')){path=newPath+path.slice(oldPath.length);break;}
  }
  return path.split('/').filter(Boolean);
}
function documentsAt(path) {
  if(path==='/Fabric/Simics_RTL')return [ARCH.sources.simics_rtl];
  let ancestor=path;
  while(ancestor && !ARCH.blocks[ancestor])ancestor=ancestor.slice(0,ancestor.lastIndexOf('/'));
  const info=ARCH.blocks[ancestor];
  if(info && info.documents)return info.documents.map(key=>ARCH.documents[key]);
  if(path.startsWith('/SOM_IO'))return [ARCH.sources.som];
  if(path.startsWith('/Fabric/Simics_reference'))return [ARCH.sources.simics];
  return [ARCH.documents.hps];
}
function currentView() {
  return {path:S.path.slice(),example:chosenExample,selected:S.sel && S.sel.type==='inst' ? S.sel.full : null};
}
function rememberNavigation(next) {
  if(returningToView || !settledView || next.join('/')===S.path.join('/'))return;
  const snapshot=JSON.parse(JSON.stringify(settledView));
  if(JSON.stringify(navigationTrail[navigationTrail.length-1])!==JSON.stringify(snapshot))navigationTrail.push(snapshot);
}
function updateNavigationControls() {
  settledView=currentView();
  $("architecture-back").disabled=returningToView || !navigationTrail.length;
  $("architecture-up").disabled=returningToView || !S.path.length;
  $("architecture-up").title=S.path.length ? 'Open /'+S.path.slice(0,-1).join('/') : 'Already at the system overview';
  $("architecture-up").textContent=S.path.length ? '↑ Up one level → '+(S.path.length>1?S.path[S.path.length-2]:'System') : '↑ Up one level (top)';
  const path=S.sel && S.sel.type==='inst' ? S.sel.full : '/'+S.path.join('/');
  const doc=documentsAt(path)[0];
  $("trm-context-link").href=doc.url;$("trm-context-link").textContent=(doc.kind==='trm'?'TRM ':'')+doc.title+' ↗';
  $("trm-context-link").title=doc.title;
  $("diagram-level").textContent='Viewing: '+(S.path.length ? '/'+S.path.join('/') : 'System overview (top level)');
  $("flows").disabled=!S.path.length;
}
async function goUp() {
  if(!S.path.length)return;
  // Keep the subsystem we just left selected in its parent diagram.
  await openBlock('/'+S.path.join('/'));
}
async function goBack() {
  if(returningToView)return;
  const previous=navigationTrail.pop();if(!previous)return;
  returningToView=true;
  try{
    chosenExample=previous.example;$("example-search").value="";fillExamplePicker();$("example-picker").value=chosenExample;
    const url=new URL(location.href);if(chosenExample)url.searchParams.set('example',chosenExample);else url.searchParams.delete('example');history.replaceState(null,'',url);
    go(previous.path);
    for(let i=0;i<200 && !window.__fpa_ready;i++)await new Promise(resolve=>setTimeout(resolve,10));
    if(previous.selected){const m=Object.values(G.meta).find(m=>m.full===previous.selected);if(m)select(pick(m,m.inst.name));}
    fit();decorateArchitecture();
  }finally{returningToView=false;updateNavigationControls();}
}
function goSystem() {
  chosenExample="";$("example-search").value="";fillExamplePicker();
  const url=new URL(location.href);url.searchParams.delete('example');url.searchParams.delete('sel');history.replaceState(null,'',url);
  go([]);
}

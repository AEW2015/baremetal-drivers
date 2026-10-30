/* Agilex adapter UI. Upstream renderer remains unmodified in tools/vendor. */
const ARCH = D.integration;
let chosenExample = "", chosenPlatform = "all";
const platformTitle = {qemu:"QEMU",simics:"Simics",hardware:"Hardware"};
function examplesAt(path) {
  return ARCH.examples.filter(e => e.blocks.some(b => b === path || b.startsWith(path + "/")));
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
  let examples=examplesAt(ancestor || path);
  if (chosenExample) examples=examples.filter(e=>e.id===chosenExample);
  const docs = [ancestor.startsWith("/SOM_IO") ? ARCH.sources.som : ancestor.startsWith("/Fabric/Simics_reference") ? ARCH.sources.simics : ARCH.sources.trm];
  if (info && info.address) docs.push(ARCH.sources.address_map);
  let h=`<section class="architecture-detail"><h3>Example explorer</h3>`;
  if(info) h+=`<div class="context"><b>${esc(info.scope)}</b><br>${esc(info.role)}${info.address ? "<br>"+esc(info.address):""}</div>`;
  if(path.startsWith("/Fabric/Lab_proposed")) h+=`<p>Only this core's hierarchy is parsed from repository RTL. Its proposed LWHPS2FPGA deployment has not been fitted or run on the board, and Simics is not running this RTL.</p>`;
  h+=`<p>${docs.map(d=>safeLink(d.url,d.title+" ↗")).join("<br>")}</p>`;
  h+=`<h3>${examples.length} related example${examples.length===1?"":"s"}</h3>`;
  h+=examples.map(exampleCard).join("") || "<p>No example matches the current selection. Choose All examples to browse this block.</p>";
  h+=`<p class="architecture-credit">Rendered with ${safeLink("https://github.com/al-nafisah/fpga-project-analyzer","FPGA Project Analyzer")} (MIT), layout by ELK (EPL-2.0). ${safeLink("https://aew2015.github.io/baremetal-drivers/assets/architecture/THIRD_PARTY.txt","Licenses and provenance ↗")}</p></section>`;
  return h;
}
function wireArchitectureButtons(parent) {
  parent.querySelectorAll("[data-arch-block]").forEach(b=>b.onclick=()=>openBlock(b.dataset.archBlock));
}
async function openBlock(path) {
  const parts=path.split("/").filter(Boolean);
  if(!defAt(parts)) throw new Error("Unknown block: "+path);
  go(parts.slice(0,-1));
  const expected=parts.slice(0,-1).join("/");
  for(let i=0;i<200;i++) {
    await new Promise(resolve=>setTimeout(resolve,10));
    if(S.path.join("/")!==expected)return; // A later user navigation won.
    if(window.__fpa_ready && S.path.join("/")===expected) {
      const m=metaFor(parts[parts.length-1]);
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
  const url=new URL(location.href);
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
    node.classList.toggle("example-hit",!!e && e.blocks.some(b=>b===m.full || b.startsWith(m.full+"/") || m.full.startsWith(b+"/")));
    node.onkeydown=event=>{
      if(event.key==="Enter"){event.preventDefault();event.stopPropagation();select(pick(m,m.inst.name));}
      if(event.key===" "){event.preventDefault();event.stopPropagation();if(drillable(m.def))go(S.path.concat(m.inst.name));}
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
  $("architecture-overview").onclick=()=>{chosenExample="";$("example-search").value="";fillExamplePicker();chooseExample("");go([]);};
}

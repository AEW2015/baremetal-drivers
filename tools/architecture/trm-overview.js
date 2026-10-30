/* Independent redraw following TRM Figure 1; no vendor figure SVG is embedded. */
function renderTRMOverview() {
  window.__fpa_ready=false;
  const layout=ARCH.trm_layout;
  G={lk:"",body:defs[D.top],nodes:[],edges:[],meta:{},tidy:true};
  LAID={width:layout.width,height:layout.height,edges:[]};
  vp.innerHTML="";vp.classList.remove('fade');
  el('rect',{x:0,y:0,width:layout.width,height:layout.height,rx:6,class:'trm-background'},vp);
  const arrows=el('defs',{},vp);
  for(const [name,color] of [['black','var(--trm-wire)'],['bus','var(--trm-bus)']]){
    const marker=el('marker',{id:'trm-arrow-'+name,viewBox:'0 0 10 10',refX:8,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'},arrows);
    el('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:color},marker);
  }
  function target(shape,index) {
    const parts=shape.path.split('/').filter(Boolean),definition=defAt(parts),inst=instAt(parts);
    const id='trm:'+index;
    const m={type:'inst',id,full:shape.path,fulls:[shape.path],inst,def:definition,stack:null,label:shape.label};
    G.meta[id]=m;G.nodes.push({id});
    const group=el('g',{class:'node trm-node trm-'+shape.tone,'data-id':id,role:'button',tabindex:0},vp);
    el('title',{},group).textContent=shape.label.replace(/\n/g,' ')+' — '+documentsAt(shape.path)[0].title;
    el('rect',{x:shape.x,y:shape.y,width:shape.w,height:shape.h,rx:shape.kind==='frame'?3:1,class:'box'},group);
    const area=shape.text_box || [shape.x,shape.y,shape.w,shape.kind==='frame'?32:shape.h];
    const lines=shape.label.split('\n'),font=shape.font || (shape.kind==='frame'?20:18),lineHeight=font*1.14;
    const y=area[1]+area[3]/2-(lines.length-1)*lineHeight/2+font*.34;
    lines.forEach((line,i)=>{el('text',{x:area[0]+area[2]/2,y:y+i*lineHeight,'text-anchor':'middle','font-size':font,class:'trm-label'},group).textContent=line;});
    group.addEventListener('click',event=>{event.stopPropagation();select(m);});
    group.addEventListener('dblclick',event=>{event.stopPropagation();if(drillable(definition))go(parts);});
  }
  // Container frames go first. Internal nodes remain separate click targets.
  layout.shapes.forEach((shape,index)=>{if(shape.kind==='frame')target(shape,index);});
  const wires=el('g',{class:'trm-wires','pointer-events':'none'},vp);
  for(const wire of layout.wires){
    const d=wire.points.map((point,index)=>(index?'L':'M')+' '+point.join(' ')).join(' ');
    const attrs={d,fill:'none',class:'trm-wire trm-wire-'+wire.tone,'marker-end':'url(#trm-arrow-'+wire.tone+')'};
    if(wire.both)attrs['marker-start']='url(#trm-arrow-'+wire.tone+')';
    el('path',attrs,wires);
    if(wire.label && wire.label_at)el('text',{x:wire.label_at[0],y:wire.label_at[1],'text-anchor':'middle',class:'trm-wire-label'},wires).textContent=wire.label;
  }
  layout.shapes.forEach((shape,index)=>{if(shape.kind!=='frame')target(shape,index);});
  el('text',{x:layout.width-24,y:layout.height-10,'text-anchor':'end',class:'trm-caption'},vp).textContent='TRM-based redraw · demonstration contexts below · not a fitted netlist';
  crumbs();$("empty").hidden=true;$("legend").hidden=true;
  panel();fit();window.__fpa_ready=true;decorateArchitecture();updateNavigationControls();
}

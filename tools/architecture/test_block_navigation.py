"""Exhaustive pointer-based block navigation checks, called by test_browser.py."""

def check_blocks(page, model):
    records=[]

    def ready(path):
        page.wait_for_function('(path)=>window.__fpa_ready && !document.querySelector("#vp").classList.contains("fade") && window.__fpa.state.path.join("/")===path',arg=path.strip('/'))

    def pointer_click(node):
        # Pick an exposed point belonging to this exact node. Container frames
        # overlap their children, so their center is not a valid click target.
        point=node.evaluate('''node=>{
          const b=node.querySelector('.box').getBoundingClientRect();
          for(const fy of [.05,.15,.3,.5,.7,.85,.95])for(const fx of [.05,.15,.3,.5,.7,.85,.95]){
            const x=b.x+b.width*fx,y=b.y+b.height*fy;
            if(document.elementFromPoint(x,y)?.closest('.node')===node)return {x,y};
          }
          return null;
        }''')
        assert point is not None,'No exposed pointer target: '+node.get_attribute('aria-label')
        page.mouse.click(point['x'],point['y'])

    def clear_panel():
        if page.locator('#panel').is_visible():
            page.get_by_role('button',name='Close',exact=True).click()

    # Click every drawn overview target, including repeated core/PHY shapes.
    for index,shape in enumerate(model['trm_layout']['shapes']):
        page.locator('#architecture-overview').click();ready('/')
        node=page.locator(f'.trm-node[data-id="trm:{index}"]')
        pointer_click(node)
        page.wait_for_function('(path)=>window.__fpa.state.sel?.full===path',arg=shape['path'])
        assert page.locator('#architecture-up').is_disabled()
        assert 'top level' in page.locator('#diagram-level').inner_text()
        page.get_by_role('button',name='Show in hierarchy',exact=True).click()
        parent=shape['path'].rsplit('/',1)[0] or '/'
        ready(parent)
        page.wait_for_function('(path)=>window.__fpa.state.sel?.full===path',arg=shape['path'])
        if parent!='/':
            page.locator('#architecture-up').click()
            ready(parent.rsplit('/',1)[0] or '/')
            page.wait_for_function('(path)=>window.__fpa.state.sel?.full===path',arg=parent)
        else:
            assert page.locator('#architecture-up').is_disabled()
        records.append({'overview_target':index,'path':shape['path'],'result':'pass'})

    # Every architectural block, plus parsed RTL children, is exercised in its
    # actual parent diagram. This checks native ELK views as well as the redraw.
    paths=set(model['blocks'])
    paths.update(['/Fabric/Lab_proposed/lab_ip/u_persona','/Fabric/Lab_proposed/lab_ip/a_reg'])
    for path in sorted(paths):
        page.evaluate('(path)=>window.__fpa.openBlock(path)',path)
        parent=path.rsplit('/',1)[0] or '/';ready(parent)
        clear_panel()
        node=page.get_by_role('button',name=path+' — click for examples; double-click to open',exact=True).first
        pointer_click(node)
        page.wait_for_function('(path)=>window.__fpa.state.sel?.full===path',arg=path)
        ancestor=path
        while ancestor not in model['blocks']:ancestor=ancestor.rsplit('/',1)[0]
        covered=any(any(b==ancestor or b.startswith(ancestor+'/') for b in e['blocks']) for e in model['examples'])
        assert node.get_attribute('data-example-coverage')==('associated' if covered else 'none'),path
        assert node.locator('.no-example-marker').count()==(0 if covered else 1),path
        if not covered:
            assert 'No example yet' in page.locator('#panel').inner_text(),path
        opens=page.get_by_role('button',name='Open ▸',exact=True)
        if opens.count():
            opens.click();ready(path)
            page.locator('#architecture-up').click();ready(parent)
            page.wait_for_function('(path)=>window.__fpa.state.sel?.full===path',arg=path)
        elif parent!='/':
            page.locator('#architecture-up').click();ready(parent.rsplit('/',1)[0] or '/')
            page.wait_for_function('(path)=>window.__fpa.state.sel?.full===path',arg=parent)
        else:
            assert page.locator('#architecture-up').is_disabled()
        records.append({'hierarchy_block':path,'associated_examples':covered,'result':'pass'})
    page.locator('#architecture-overview').click();ready('/')
    return records

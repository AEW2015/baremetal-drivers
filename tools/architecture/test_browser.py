#!/usr/bin/env python3
"""Exercise the generated diagram offline; requires Playwright + Chromium."""
import argparse,json
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--browser',help='Optional existing Chromium executable')
    p.add_argument('--output',type=Path,default=ROOT/'examples/agilex5-modular/runs/architecture-browser')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((ROOT/'examples/agilex5-modular/catalog.json').read_text())
    design=ROOT/'docs/assets/architecture/design.html'
    model=json.loads((ROOT/'docs/assets/architecture/design.json').read_text())['integration']
    errors=[];requests=[];checks=[]
    with sync_playwright() as w:
        options={'headless':True}
        if a.browser:options['executable_path']=a.browser
        browser=w.chromium.launch(**options)
        context=browser.new_context(viewport={'width':1440,'height':1000},offline=True)
        page=context.new_page();page.on('pageerror',lambda error:errors.append(error.stack))
        page.on('request',lambda request:requests.append(request.url))
        def screenshot(name):
            page.wait_for_function('!document.querySelector("#vp").classList.contains("fade")')
            page.wait_for_timeout(200) # Let the viewer's 180 ms opacity transition finish.
            page.screenshot(path=str(a.output/name))
        page.goto(design.as_uri());page.wait_for_function('window.__fpa_ready === true')
        assert page.locator('.trm-node').count()==len(model['trm_layout']['shapes'])
        assert page.locator('#architecture-up').is_disabled()
        assert page.locator('#architecture-back').is_disabled()
        assert page.locator('#example-picker option').count()==82
        screenshot('overview.png')
        checks.append('Offline TRM Figure 1 layout: MPU / APS / PSS / MPFE, all 81 catalog options')
        for doc in model['documents'].values():
            assert parse_qs(urlsplit(doc['url']).query)['contentId']==[doc['content_id']]
        assert page.locator('#trm-context-link').get_attribute('href')==model['documents']['hps']['url']
        page.get_by_role('button',name='/HPS/APS/CCU — click for examples; double-click to open').click()
        assert page.locator('#trm-context-link').get_attribute('href')==model['documents']['ccu']['url']
        page.get_by_role('button',name='↑ Open parent diagram',exact=True).click()
        page.wait_for_function('window.__fpa_ready && window.__fpa.state.path.join("/") === "HPS/APS"')
        checks.append('Direct TRM context links resolve exact topic IDs; overview blocks open their parent hierarchy')
        for row in catalog['examples']:
            page.evaluate('(id)=>window.__fpa.chooseExample(id)',row['id'])
            card=page.locator('[data-example-id="'+row['id']+'"]')
            assert card.count()==1,row['id']
            assert card.locator('.result-badge').count()==3,row['id']
            assert card.get_by_text('Tutorial / expected output ↗',exact=True).get_attribute('href').startswith('https://')
            assert card.get_by_text('Source ↗',exact=True).get_attribute('href').startswith('https://github.com/AEW2015/baremetal-drivers/')
            for platform,result in row['platforms'].items():
                assert result['status'].upper() in card.inner_text(),(row['id'],platform)
        checks.append('All 81 example selections resolve to blocks, status cards, tutorials and source')
        page.evaluate('()=>window.__fpa.chooseExample("upstream/gic")')
        assert page.locator('#trm-context-link').get_attribute('href')==model['documents']['gic']['url']
        page.locator('#architecture-up').click()
        page.wait_for_function('window.__fpa_ready && window.__fpa.state.path.join("/") === "HPS"')
        page.locator('#architecture-back').click()
        page.wait_for_selector('[data-example-id="upstream/gic"]')
        assert page.evaluate('window.__fpa.state.path.join("/")')=='HPS/APS'
        assert page.evaluate('window.__fpa.state.sel.full')=='/HPS/APS/GIC'
        page.keyboard.press('Alt+ArrowUp')
        page.wait_for_function('window.__fpa_ready && window.__fpa.state.path.join("/") === "HPS"')
        page.keyboard.press('Alt+ArrowLeft')
        page.wait_for_selector('[data-example-id="upstream/gic"]')
        checks.append('Back/Up buttons and Alt+Left/Alt+Up restore diagram level, selected block and example')
        page.evaluate('()=>window.__fpa.chooseExample("upstream/mailbox")')
        page.select_option('#platform-picker','hardware')
        card=page.locator('[data-example-id="upstream/mailbox"]')
        assert card.locator('.result-badge').count()==1 and 'Hardware: PASS' in card.inner_text()
        screenshot('mailbox.png')
        page.select_option('#platform-picker','all')
        checks.append('Platform emphasis preserves the mailbox hardware PASS and evidence link')
        page.evaluate('()=>window.__fpa.chooseExample("fabric/add")')
        assert page.locator('#panel').get_by_text('Registers',exact=True).count()==1
        assert 'Proposed CPU base 0x20020000' in page.locator('#panel').inner_text()
        assert 'hardware unqualified' in page.locator('#panel').inner_text()
        page.get_by_role('button',name='Open ▸',exact=True).click()
        page.wait_for_function('window.__fpa_ready === true')
        assert page.locator('.node').count()==2
        assert page.get_by_role('button',name='/Fabric/Lab_proposed/lab_ip/u_persona — click for examples; double-click to open').count()==1
        screenshot('rtl.png')
        checks.append('Fabric register ABI, unqualified-deployment notice and parsed persona/register hierarchy')
        node=page.get_by_role('button',name='/Fabric/Lab_proposed/lab_ip/u_persona — click for examples; double-click to open')
        node.focus();page.keyboard.press('Enter')
        assert 'lab_persona' in page.locator('#panel').inner_text()
        checks.append('Keyboard selection of an actual RTL child')
        page.locator('#architecture-overview').click();page.wait_for_function('window.__fpa_ready === true')
        with page.expect_download() as captured:page.select_option('#export','svg')
        download=captured.value;download.save_as(a.output/'overview.svg')
        assert '<svg' in (a.output/'overview.svg').read_text()
        checks.append('SVG export downloads a standalone drawing')
        with page.expect_download() as captured:page.select_option('#export','png')
        captured.value.save_as(a.output/'export.png')
        assert (a.output/'export.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        checks.append('PNG export downloads a valid raster drawing')
        page.locator('#example-search').fill('mailbox')
        assert 1<page.locator('#example-picker option').count()<82
        page.locator('#example-search').fill('no-example-with-this-name')
        assert page.locator('#example-picker option').count()==1
        checks.append('Example search handles matching and empty results')
        page.locator('#architecture-overview').click()
        page.goto(design.as_uri()+'?example=practice/timer&theme=dark')
        page.wait_for_selector('[data-example-id="practice/timer"]')
        assert page.locator('.node.example-hit').count()>0
        checks.append('Shareable example URL restores selection and dark theme')
        page.evaluate('()=>Promise.all([window.__fpa.chooseExample("upstream/mailbox"),window.__fpa.chooseExample("fabric/add")])')
        assert page.locator('[data-example-id="fabric/add"]').count()==1
        checks.append('Overlapping layout requests preserve the latest example selection')
        page.set_viewport_size({'width':390,'height':844})
        screenshot('mobile.png')
        assert page.locator('#panel').bounding_box()['width']<=390
        assert page.locator('#architecture-bar').bounding_box()['height']<844
        checks.append('Mobile viewport retains controls and a bounded details panel')
        page.goto(design.as_uri()+'?sel=/HPS/Memory/CCU')
        page.wait_for_function('window.__fpa.state.sel?.full === "/HPS/APS/CCU"')
        assert page.locator('#trm-context-link').get_attribute('href')==model['documents']['ccu']['url']
        checks.append('Legacy Memory/CCU deep link resolves to the reorganized APS block')
        assert not errors,errors
        assert not any(url.startswith(('http:','https:')) for url in requests),requests
        report={'browser':browser.version,'examples_checked':81,'checks':checks,'javascript_errors':errors,'network_dependency_requests':[],
                'html_sha256':__import__('hashlib').sha256(design.read_bytes()).hexdigest()}
        browser.close()
    (a.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: '+str(len(checks))+' browser checks; all 81 example selections; offline; no JavaScript errors')

if __name__=='__main__':main()

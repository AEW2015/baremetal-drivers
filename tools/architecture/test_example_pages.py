#!/usr/bin/env python3
"""Check built page links, and optionally exercise embedded diagrams in Chromium."""
import argparse,functools,json,threading
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urljoin,urlsplit,unquote
from link_example_pages import ROOT,pages

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.frames=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and attrs.get('href'):self.links.append(attrs['href'])
        if tag=='iframe' and 'example-diagram' in attrs.get('class','').split():self.frames.append(attrs)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site',type=Path,default=ROOT/'site')
    p.add_argument('--browser-checks',action='store_true')
    p.add_argument('--output',type=Path,default=ROOT/'examples/agilex5-modular/runs/example-page-diagrams')
    a=p.parse_args();site=a.site.resolve();mapped=pages();expected=(site/'assets/architecture/design.html').resolve()
    if not expected.is_file():raise RuntimeError('Build the architecture assets and MkDocs first')
    for name,ids in mapped.items():
        file=site/Path(name).with_suffix('')/'index.html'
        data=Links();data.feed(file.read_text())
        assert len(data.frames)==1,name
        frame=data.frames[0];src=urlsplit(urljoin(file.as_uri(),frame['src']))
        assert Path(unquote(src.path)).resolve()==expected,(name,frame['src'])
        assert parse_qs(src.query).get('example',[])==(ids[:1] if ids else []),name
        assert frame.get('loading')=='lazy',name
        linked=set()
        for href in data.links:
            url=urlsplit(urljoin(file.as_uri(),href))
            if url.scheme=='file' and Path(unquote(url.path)).resolve()==expected:
                linked.update(parse_qs(url.query).get('example',[]))
        assert set(ids)<=linked,(name,set(ids)-linked)
    data=Links();data.feed((site/'example-catalog/index.html').read_text())
    linked={id for href in data.links for id in parse_qs(urlsplit(href).query).get('example',[])}
    catalog=json.loads((ROOT/'examples/agilex5-modular/catalog.json').read_text())
    assert linked=={r['id'] for r in catalog['examples']}
    report={'pages_checked':len(mapped),'catalog_links_checked':len(linked),'browser_checks':[]}
    if a.browser_checks:
        from playwright.sync_api import sync_playwright
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(site)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        try:
            with sync_playwright() as w:
                browser=w.chromium.launch(headless=True)
                context=browser.new_context(viewport={'width':1440,'height':1000})
                context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base+'/') else route.abort())
                page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(error.stack))
                for name in ('examples/dma.md','examples/qemu-labs.md','runtime-fixes.md','fabric-ip.md','config-audit.md','simics-rtl.md','model-audit.md','memory-fabric-labs.md'):
                    page.goto(base+'/'+str(Path(name).with_suffix(''))+'/')
                    assert page.locator('details.example-architecture').get_attribute('open') is None
                    page.locator('details.example-architecture > summary').click()
                    page.locator('iframe.example-diagram').scroll_into_view_if_needed()
                    diagram=page.frame_locator('iframe.example-diagram')
                    id=mapped[name][0]
                    diagram.locator('[data-example-id="'+id+'"]').wait_for(timeout=30000)
                    assert diagram.locator('#example-picker').input_value()==id
                    report['browser_checks'].append({'page':name,'selected_example':id,'status':'pass'})
                assert not errors,errors
                report['javascript_errors']=errors;report['browser']=browser.version
                browser.close()
        finally:server.shutdown();server.server_close();thread.join(timeout=5)
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: '+str(len(mapped))+' embedded example pages; '+str(len(linked))+' catalog diagram links; '+str(len(report['browser_checks']))+' browser checks')

if __name__=='__main__':main()

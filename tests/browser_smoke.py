"""Exercise the shipped application against its built distribution in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os, json
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
with ThreadingHTTPServer(("127.0.0.1",0), partial(SimpleHTTPRequestHandler,directory=root / "dist")) as server:
    Thread(target=server.serve_forever,daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))
        page = browser.new_page(viewport={"width":390,"height":844})
        errors = []
        page.on('pageerror',lambda error: errors.append(str(error)))
        page.goto(base + '/provinces.html?province=ns&q=3057952')
        page.locator('#matches').get_by_text('ABC HOUSING CO-OPERATIVE LIMITED').wait_for()
        assert 'Dartmouth' in page.locator('#matches').inner_text()
        page.select_option('#province', 'bc')
        assert 'telegraph' in page.locator('#example').inner_text()
        assert page.locator('#history').input_value() == 'true'
        assert page.get_by_text('Canada’s Business Registries ↗').get_attribute('href').startswith('https://ised-isde')
        version = [0]
        def federal(route):
            director = 'Updated Director' if version[0] else 'Example Director <img>'
            data = {'id':'1234567','legalName':'Example Company <img>','status':'active','statusDetail':'intent_to_dissolve','legislation':'cbca','locality':'Halifax, NS','directors':[{'name':director,'changeType':''}],'annualReturns':[{'year':2025,'status':'filed'}],'controlStatements':[{'names':['Published Person'],'date':'2025-01-01','status':'closed','personType':'knownPerson'}],'filings':[{'type':'incorporation','effectiveDate':'2020-01-01','receivedDate':'2020-01-02','legalName':''}]}
            route.fulfill(content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'fetched_at':'2026-11-25T12:0'+str(version[0])+':00Z','data':data}))
        page.route('**/api/corporateghosts/corporation?*',federal)
        page.goto(base+'/')
        page.locator('#live-id').fill('1234567')
        page.locator('#lookup').click()
        page.locator('#live-name').get_by_text('Example Company <img>',exact=True).wait_for()
        assert 'intent to dissolve' in page.locator('#live-fields').inner_text()
        assert page.locator('img').count()==0
        page.locator('#save-capture').click()
        page.reload()
        assert '1 saved captures' in page.locator('#saved-count').inner_text()
        version[0] = 1
        page.locator('#live-id').fill('1234567')
        page.locator('#lookup').click()
        page.locator('#live-comparison').get_by_text('Selected: Updated Director',exact=True).wait_for()
        assert 'closed' in page.locator('#live-control').text_content()
        page.locator('#current-record > details > summary').click()
        page.locator('#clear-saved').click()
        assert '0 saved captures' in page.locator('#saved-count').inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not errors, errors
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        browser.close()
    server.shutdown()

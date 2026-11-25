"""Exercise the shipped application against its built distribution in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os, json
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright, expect

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
        assert page.locator('#history').input_value() == 'false'
        assert page.get_by_text('Canada’s Business Registries ↗').get_attribute('href').startswith('https://ised-isde')
        version = [0]
        requested_ids = []
        snapshot = json.loads((root/'dist/data/manifest.json').read_text())
        snapshot['business_numbers'] = {'version':1,'prefix_length':3,'shards':{'123':'business-numbers-123-abcdef0123456789.json.gz'}}
        page.route('**/data/manifest.json*', lambda route: route.fulfill(content_type='application/json',body=json.dumps(snapshot)))
        page.route('**/data/business-numbers-123-abcdef0123456789.json.gz', lambda route: route.fulfill(content_type='application/json',body=json.dumps({'123456789':['1234567']})))
        def federal(route):
            requested_ids.append(route.request.url.split('id=')[-1])
            director = 'Updated Director' if version[0] else 'Example Director <img>'
            data = {'id':'1234567','legalName':'Example Company <img>','status':'active','statusDetail':'intent_to_dissolve','legislation':'cbca','locality':'Halifax, NS','directors':[{'name':director,'changeType':''}],'annualReturns':[{'year':2025,'status':'filed'}],'controlStatements':[{'names':['Published Person'],'date':'2025-01-01','status':'closed','personType':'knownPerson'}],'filings':[{'type':'incorporation','effectiveDate':'2020-01-01','receivedDate':'2020-01-02','legalName':''}]}
            route.fulfill(content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'fetched_at':'2026-11-25T12:0'+str(version[0])+':00Z','data':data}))
        page.route('**/api/corporateghosts/corporation?*',federal)
        page.goto(base+'/')
        page.locator('#live-id').fill('1234567')
        page.locator('#lookup').click()
        page.locator('#live-name').get_by_text('Example Company <img>',exact=True).wait_for()
        assert 'intent to dissolve' in page.locator('#live-fields').inner_text()
        assert '2020-01-01' in page.locator('#live-fields').inner_text()
        assert page.locator('img').count()==0
        page.locator('#save-capture').click()
        expect(page.locator('#live-status')).to_contain_text('Capture saved on this device')
        assert page.evaluate("JSON.parse(localStorage.getItem('coolcode:corporateghosts:captures')).length") == 1
        page.reload()
        expect(page.locator('#saved-count')).to_contain_text('1 saved captures')
        version[0] = 1
        page.locator('#live-id').fill('1234567')
        page.locator('#lookup').click()
        page.locator('#live-comparison').get_by_text('Selected: Updated Director',exact=True).wait_for()
        assert 'closed' in page.locator('#live-control').text_content()
        page.locator('#live-kind').select_option('auto')
        page.locator('#live-id').fill('123 456 789 RC0001')
        page.locator('#lookup').click()
        expect(page.locator('#live-status')).to_contain_text('CRA business number matched federal corporation 1234567')
        expect(page.locator('#lookup')).to_be_enabled()
        assert requested_ids[-1] == '1234567'
        assert '123456789' not in requested_ids
        # An absent federal BN must never be sent as a corporation number.
        before_calls = len(requested_ids)
        page.locator('#live-id').fill('987654321')
        page.locator('#lookup').click()
        expect(page.locator('#live-status')).to_contain_text('No federal match')
        assert len(requested_ids) == before_calls
        bc_link=page.locator('#live-matches a').first
        assert 'historical=false' in bc_link.get_attribute('href')
        assert 'q=987654321' in bc_link.get_attribute('href')
        # A provincial search starts with current registrations and exposes the BN.
        page.route('https://orgbook.gov.bc.ca/api/v4/search/topic?*',lambda route:route.fulfill(content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'total':1,'page_size':10,'results':[{'source_id':'BC0000001','inactive':False,'names':[{'type':'entity_name','text':'Example BC Company'},{'type':'business_number','text':'987654321'}],'attributes':[]}]})))
        with page.expect_navigation(): bc_link.click()
        expect(page.locator('#result-status')).to_contain_text('1 matching records')
        assert page.locator('#history').input_value() == 'false'
        assert 'CRA business number 987654321' in page.locator('#matches').inner_text()
        assert page.locator('#matches a').get_attribute('href') == 'https://orgbook.gov.bc.ca/entity/BC0000001'
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.goto(base+'/')
        page.locator('#current-record > details > summary').click()
        page.locator('#clear-saved').click()
        expect(page.locator('#saved-count')).to_contain_text('0 saved captures')
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not errors, errors
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        browser.close()
    server.shutdown()

"""Exercise the shipped application against its built distribution in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
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
        assert not errors, errors
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        browser.close()
    server.shutdown()

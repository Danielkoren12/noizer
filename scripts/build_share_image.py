"""Render the existing site wordmark as a social preview, without AI or downloads.

Uses the Chromium and Playwright already used by the project's browser checks.
"""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
from build_preview import inline_asset


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'assets' / 'noizer-share.png'


def build():
    source = (ROOT / 'index.html').read_text()
    wordmark = re.search(r'<span class="wordmark"[^>]*>[^<]*</span>', source).group(0)
    css = (ROOT / 'styles.css').read_text()
    css = re.sub(r"url\('([^']+)'\)", inline_asset, css)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1200, 'height': 630},
                                device_scale_factor=1, reduced_motion='reduce')
        page.route('**/*', lambda route: route.abort())
        page.set_content(f'<style>{css}</style><main class="share-card">{wordmark}</main>')
        page.add_style_tag(content='''
            html, body { margin: 0; width: 1200px; height: 630px; overflow: hidden; }
            .share-card { width: 1200px; height: 630px; display: grid;
                          place-items: center; background: #fff; }
            .share-card .wordmark { width: 640px; font-size: 140px; line-height: 1.3; }
            .share-card .wordmark:after { height: 16px; margin-top: 5px; }
        ''')
        page.evaluate('document.fonts.ready')
        assert page.evaluate('document.fonts.check("140px Marker")')
        page.screenshot(path=str(OUTPUT))
        browser.close()
    print('Built assets/noizer-share.png: existing site wordmark on white, 1200x630.')


if __name__ == '__main__':
    build()

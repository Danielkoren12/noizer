"""Build a portable preview from the maintained HTML/CSS/JS sources.

No downloads or third-party executables. Fonts and their licenses are embedded.
"""
import base64
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def inline_asset(match):
    relative_path = match.group(1)
    path = ROOT / relative_path
    mime = 'font/ttf' if path.suffix == '.ttf' else 'image/svg+xml'
    encoded = base64.b64encode(path.read_bytes()).decode('ascii')
    return f'url("data:{mime};base64,{encoded}")'


def build():
    html = (ROOT / 'index.html').read_text()
    css = (ROOT / 'styles.css').read_text()
    css = re.sub(r"url\('([^']+)'\)", inline_asset, css)
    javascript = (ROOT / 'app.js').read_text()
    html = re.sub(r'  <link rel="preload"[^>]+>\n', '', html)
    html = html.replace('<link rel="stylesheet" href="styles.css">', f'<style>\n{css}\n</style>')
    html = html.replace('<script src="app.js" defer></script>', '')
    for filename, mime in [('favicon.svg', 'image/svg+xml'), ('favicon-96.png', 'image/png')]:
        favicon = base64.b64encode((ROOT / 'assets' / filename).read_bytes()).decode('ascii')
        html = html.replace(f'href="assets/{filename}"', f'href="data:{mime};base64,{favicon}"')
    licenses = {path.name: path.read_text() for path in (ROOT / 'assets/fonts').glob('*.txt')}
    license_data = json.dumps(licenses, ensure_ascii=False).replace('<', '\\u003c')
    html = html.replace('</body>', f'<script type="application/json" id="bundled-font-licenses">{license_data}</script>\n<script>\n{javascript}\n</script>\n</body>')
    (ROOT / 'preview.html').write_text(html)
    print('Built preview.html: all CSS, JavaScript, fonts, favicon and font licenses embedded.')


if __name__ == '__main__':
    build()

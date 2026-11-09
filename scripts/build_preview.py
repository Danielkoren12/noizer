"""Build a portable preview from the maintained HTML/CSS/JS sources.

No downloads or third-party executables. Fonts and their licenses are embedded.
"""
import base64
import json
import mimetypes
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def inline_asset(match):
    relative_path = match.group(1)
    path = ROOT / relative_path
    mime = 'font/ttf' if path.suffix == '.ttf' else 'image/svg+xml'
    encoded = base64.b64encode(path.read_bytes()).decode('ascii')
    return f'url("data:{mime};base64,{encoded}")'


def build(language='he', page='home'):
    if page == 'partnership':
        source = 'en/partnership-ads/index.html' if language == 'en' else 'partnership-ads/index.html'
        output = 'preview-partnership-en.html' if language == 'en' else 'preview-partnership.html'
    else:
        source = 'en/index.html' if language == 'en' else 'index.html'
        output = 'preview-en.html' if language == 'en' else 'preview.html'
    html = (ROOT / source).read_text()
    # English uses root-relative URLs in production; previews embed the same assets.
    for attribute in ['href', 'src', 'poster']:
        html = html.replace(f'{attribute}="/assets/', f'{attribute}="assets/')
    html = html.replace('href="/styles.css"', 'href="styles.css"')
    html = html.replace('src="/app.js"', 'src="app.js"')
    html = re.sub(r'href="(/[^"]*)"', lambda m: f'href="https://noizer.co.il{m.group(1)}"', html)
    css = (ROOT / 'styles.css').read_text()
    css = re.sub(r"url\('([^']+)'\)", inline_asset, css)
    javascript = (ROOT / 'app.js').read_text()
    html = re.sub(r'  <link rel="preload"[^>]+>\n', '', html)
    html = html.replace('<link rel="stylesheet" href="styles.css">', f'<style>\n{css}\n</style>')
    html = html.replace('<script src="app.js" defer></script>', '')
    for filename, mime in [('favicon.svg', 'image/svg+xml'), ('favicon-96.png', 'image/png')]:
        favicon = base64.b64encode((ROOT / 'assets' / filename).read_bytes()).decode('ascii')
        html = html.replace(f'href="assets/{filename}"', f'href="data:{mime};base64,{favicon}"')
    # Keep user-supplied examples usable in the standalone preview as well.
    def inline_example(match):
        attribute, relative_path = match.groups()
        data = base64.b64encode((ROOT / relative_path).read_bytes()).decode('ascii')
        mime = mimetypes.guess_type(relative_path)[0] or 'application/octet-stream'
        return f'{attribute}="data:{mime};base64,{data}"'
    html = re.sub(r'(src|poster|href)="(assets/examples/[^"]+)"', inline_example, html)
    licenses = {path.name: path.read_text() for path in (ROOT / 'assets/fonts').glob('*.txt')}
    license_data = json.dumps(licenses, ensure_ascii=False).replace('<', '\\u003c')
    html = html.replace('</body>', f'<script type="application/json" id="bundled-font-licenses">{license_data}</script>\n<script>\n{javascript}\n</script>\n</body>')
    (ROOT / output).write_text(html)
    print(f'Built {output}: CSS, JavaScript, fonts, examples and licenses embedded.')


if __name__ == '__main__':
    build('he')
    build('en')
    build('he', 'partnership')
    build('en', 'partnership')

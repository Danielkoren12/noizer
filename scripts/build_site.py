"""Prepare only public website files for static hosting; no dependencies."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'public'
PUBLIC_FILES = ['index.html', 'styles.css', 'app.js', 'robots.txt']
ASSET_TYPES = {'.ttf', '.woff', '.woff2', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.avif', '.mp4', '.webm', '.txt'}


def build():
    files = [ROOT / name for name in PUBLIC_FILES]
    files += [path for path in (ROOT / 'assets').rglob('*')
              if path.is_file() and path.suffix.lower() in ASSET_TYPES]
    expected = {path.relative_to(ROOT) for path in files}
    if OUTPUT.exists():
        unexpected = [path.relative_to(OUTPUT) for path in OUTPUT.rglob('*')
                      if path.is_file() and path.relative_to(OUTPUT) not in expected]
        if unexpected:
            raise RuntimeError(f'Preserving unexpected files in public: {unexpected}')
    for source in files:
        if source.is_symlink():
            raise RuntimeError(f'Asset symlinks must be reviewed before publishing: {source}')
        destination = OUTPUT / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    print(f'Prepared {len(files)} website files in public/; font licenses included.')


if __name__ == '__main__':
    build()

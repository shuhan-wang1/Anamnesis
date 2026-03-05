"""Download KaTeX and D3.js for local bundling (offline desktop support)."""

import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_DIR = os.path.join(ROOT, 'frontend', 'vendor')
KATEX_VERSION = '0.16.11'
D3_VERSION = '7'


def download(url: str, dest: str):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        return  # already downloaded
    print(f'  Downloading {os.path.basename(dest)}...')
    urllib.request.urlretrieve(url, dest)


def main():
    print(f'Vendoring KaTeX {KATEX_VERSION} and D3.js v{D3_VERSION}...')
    base = f'https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist'

    # --- KaTeX core files ---
    katex_dir = os.path.join(VENDOR_DIR, 'katex')
    download(f'{base}/katex.min.css',
             os.path.join(katex_dir, 'katex.min.css'))
    download(f'{base}/katex.min.js',
             os.path.join(katex_dir, 'katex.min.js'))
    download(f'{base}/contrib/auto-render.min.js',
             os.path.join(katex_dir, 'contrib', 'auto-render.min.js'))

    # --- KaTeX fonts (all families, all formats) ---
    KATEX_FONTS = [
        'KaTeX_AMS-Regular',
        'KaTeX_Caligraphic-Bold',
        'KaTeX_Caligraphic-Regular',
        'KaTeX_Fraktur-Bold',
        'KaTeX_Fraktur-Regular',
        'KaTeX_Main-Bold',
        'KaTeX_Main-BoldItalic',
        'KaTeX_Main-Italic',
        'KaTeX_Main-Regular',
        'KaTeX_Math-BoldItalic',
        'KaTeX_Math-Italic',
        'KaTeX_SansSerif-Bold',
        'KaTeX_SansSerif-Italic',
        'KaTeX_SansSerif-Regular',
        'KaTeX_Script-Regular',
        'KaTeX_Size1-Regular',
        'KaTeX_Size2-Regular',
        'KaTeX_Size3-Regular',
        'KaTeX_Size4-Regular',
        'KaTeX_Typewriter-Regular',
    ]
    fonts_dir = os.path.join(katex_dir, 'fonts')
    for font in KATEX_FONTS:
        for ext in ['woff2', 'woff', 'ttf']:
            download(f'{base}/fonts/{font}.{ext}',
                     os.path.join(fonts_dir, f'{font}.{ext}'))

    # --- D3.js ---
    download(f'https://cdn.jsdelivr.net/npm/d3@{D3_VERSION}/dist/d3.min.js',
             os.path.join(VENDOR_DIR, 'd3', 'd3.min.js'))

    total_files = 3 + len(KATEX_FONTS) * 3 + 1  # core + fonts + d3
    print(f'Done! {total_files} files in frontend/vendor/')


if __name__ == '__main__':
    main()

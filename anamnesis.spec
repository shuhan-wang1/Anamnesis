# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Anamnesis desktop app."""

import sys
import os

block_cipher = None

# Determine platform
is_mac = sys.platform == 'darwin'
is_win = sys.platform == 'win32'

# Icon paths
icon_win = os.path.join('assets', 'icon.ico') if os.path.exists(os.path.join('assets', 'icon.ico')) else None
icon_mac = os.path.join('assets', 'icon.icns') if os.path.exists(os.path.join('assets', 'icon.icns')) else None

a = Analysis(
    ['desktop.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('frontend', 'frontend'),
        ('parser', 'parser'),
        ('inference', 'inference'),
        ('scripts', 'scripts'),
        ('server', 'server'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        # Flask and dependencies
        'flask',
        'flask_cors',
        'werkzeug',
        'jinja2',
        'markupsafe',
        'click',
        'itsdangerous',
        'blinker',
        # Server route modules (dynamically imported)
        'server.routes',
        'server.routes.graph_api',
        'server.routes.progress_api',
        'server.routes.diagnostic_api',
        'server.routes.learning_api',
        'server.routes.quiz_api',
        'server.routes.dashboard_api',
        'server.routes.spaced_repetition',
        'server.routes.course_api',
        'server.state',
        'server.course_manager',
        # Parser modules
        'parser',
        'parser.latex_parser',
        'parser.katex_converter',
        'parser.macro_expander',
        'parser.ref_resolver',
        'parser.section_tracker',
        # Inference modules
        'inference',
        'inference.concept_analyzer',
        'inference.dependency_inferrer',
        'inference.graph_merger',
        'inference.prompt_templates',
        # Scripts (used by course_manager)
        'scripts.parse_all',
        'scripts.analyze_nodes',
        'scripts.name_nodes',
        'scripts.build_graph',
        'scripts.infer_deps',
        # Config
        'config',
        # Desktop dependencies
        'webview',
        'platformdirs',
        # Standard library modules that may be needed
        'json',
        'math',
        'datetime',
        'collections',
        'hashlib',
        'uuid',
        'shutil',
        'threading',
        'socket',
        'regex',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Anthropic is optional — only used for CLI inference scripts
        'anthropic',
        # Heavy science/data packages
        'tkinter', '_tkinter',
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'PIL', 'Pillow', 'cv2',
        # Qt — pywebview uses EdgeChromium (WebView2) on Windows, not Qt
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'qtpy',
        'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtNetwork', 'PyQt5.QtWebChannel',
        'PyQt5.QtQuick', 'PyQt5.QtQml', 'PyQt5.QtPositioning',
        'PyQt5.QtPrintSupport', 'PyQt5.QtQuickWidgets',
        # IPython / Jupyter — not needed for web app
        'IPython', 'jupyter', 'notebook', 'nbformat', 'nbconvert',
        'ipykernel', 'ipywidgets', 'traitlets',
        # Documentation / dev tools
        'sphinx', 'docutils', 'pygments', 'lib2to3', 'jedi', 'parso',
        # Other unnecessary packages
        'pytest', 'setuptools', 'pip', 'distutils',
        'lxml', 'zmq', 'tornado', 'psutil',
        'cryptography', 'nacl', 'paramiko', 'bcrypt',
        'cloudpickle', 'shelve',
        'sqlite3',
        'babel', 'pytz',
        'pkg_resources',
        'cairosvg', 'cairocffi', 'cssselect2',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if is_win:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='Anamnesis',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_win,
    )
elif is_mac:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Anamnesis',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_mac,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Anamnesis',
    )
    app = BUNDLE(
        coll,
        name='Anamnesis.app',
        icon=icon_mac,
        bundle_identifier='com.anamnesis.app',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleName': 'Anamnesis',
        },
    )
else:
    # Linux — single file
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='Anamnesis',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        runtime_tmpdir=None,
        console=False,
        icon=None,
    )

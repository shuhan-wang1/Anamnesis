"""Build automation for Anamnesis desktop app."""

import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))


def check_vendor_assets():
    """Ensure vendored frontend assets exist."""
    vendor_dir = os.path.join(ROOT, 'frontend', 'vendor')
    katex_css = os.path.join(vendor_dir, 'katex', 'katex.min.css')
    d3_js = os.path.join(vendor_dir, 'd3', 'd3.min.js')

    if not os.path.exists(katex_css) or not os.path.exists(d3_js):
        print("Vendored assets missing. Downloading...")
        vendor_script = os.path.join(ROOT, 'scripts', 'vendor_assets.py')
        result = subprocess.run([sys.executable, vendor_script], cwd=ROOT)
        if result.returncode != 0:
            print("ERROR: Failed to download vendor assets.")
            sys.exit(1)
        print("Vendor assets downloaded successfully.")
    else:
        print("Vendor assets found.")


def check_icons():
    """Warn if icon files are missing."""
    assets_dir = os.path.join(ROOT, 'assets')
    if sys.platform == 'win32':
        icon = os.path.join(assets_dir, 'icon.ico')
        if not os.path.exists(icon):
            print(f"WARNING: {icon} not found. Executable will use default icon.")
    elif sys.platform == 'darwin':
        icon = os.path.join(assets_dir, 'icon.icns')
        if not os.path.exists(icon):
            print(f"WARNING: {icon} not found. App will use default icon.")


def check_dependencies():
    """Verify required packages are installed."""
    # Map of display name -> import name
    required = {
        'pywebview': 'webview',
        'platformdirs': 'platformdirs',
        'PyInstaller': 'PyInstaller',
    }
    missing = []
    for pkg_name, import_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        print(f"ERROR: Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install -r requirements-desktop.txt")
        sys.exit(1)
    print("All dependencies found.")


def build():
    """Run PyInstaller build."""
    spec_file = os.path.join(ROOT, 'anamnesis.spec')
    if not os.path.exists(spec_file):
        print(f"ERROR: {spec_file} not found.")
        sys.exit(1)

    print("\n=== Building Anamnesis Desktop App ===\n")

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        spec_file,
    ]

    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode != 0:
        print("\nERROR: Build failed.")
        sys.exit(1)

    # Report output location
    dist_dir = os.path.join(ROOT, 'dist')
    if sys.platform == 'win32':
        exe_path = os.path.join(dist_dir, 'Anamnesis.exe')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\nBuild successful!")
            print(f"  Output: {exe_path}")
            print(f"  Size:   {size_mb:.1f} MB")
    elif sys.platform == 'darwin':
        app_path = os.path.join(dist_dir, 'Anamnesis.app')
        if os.path.exists(app_path):
            # Get total size of .app bundle
            total = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, fns in os.walk(app_path)
                for f in fns
            )
            size_mb = total / (1024 * 1024)
            print(f"\nBuild successful!")
            print(f"  Output: {app_path}")
            print(f"  Size:   {size_mb:.1f} MB")
    else:
        exe_path = os.path.join(dist_dir, 'Anamnesis')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\nBuild successful!")
            print(f"  Output: {exe_path}")
            print(f"  Size:   {size_mb:.1f} MB")


def main():
    print("Anamnesis Desktop Build\n")
    check_dependencies()
    check_vendor_assets()
    check_icons()
    build()


if __name__ == '__main__':
    main()

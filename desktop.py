"""Desktop entry point — launches Flask + pywebview native window."""

import os
import sys
import socket
import threading
import time

# Handle PyInstaller frozen paths
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

# Must set these BEFORE importing config / server modules
os.environ['ANAMNESIS_BUNDLE_DIR'] = BUNDLE_DIR
os.environ['ANAMNESIS_DESKTOP'] = '1'

# Ensure project root is on sys.path for imports
sys.path.insert(0, BUNDLE_DIR)

import webview
from server.app import app, startup


def find_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def wait_for_server(port: int, timeout: float = 5.0):
    """Poll until the Flask server is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.1)
    return False


def start_server(port: int):
    """Start Flask in a background thread."""
    startup()
    app.run(
        host='127.0.0.1',
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def main():
    port = find_free_port()
    url = f'http://127.0.0.1:{port}'

    # Start Flask server as daemon thread (dies when main thread exits)
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to be ready
    if not wait_for_server(port):
        print("Warning: Server may not be ready yet, opening window anyway...")

    # Create native window
    webview.create_window(
        title='Anamnesis',
        url=url,
        width=1280,
        height=860,
        min_size=(900, 600),
        background_color='#0f1117',  # match CSS body background
    )
    webview.start(debug=False)


if __name__ == '__main__':
    main()

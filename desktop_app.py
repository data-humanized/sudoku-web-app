"""
desktop_app.py
Desktop Application wrapper for ZenSudoku.
Runs the NiceGUI server locally and embeds it in a native window using PyWebView,
or opens the default desktop web browser.
"""

import sys
import threading
import time
import webbrowser
from nicegui import ui
import main


def start_server():
    ui.run(
        title='ZenSudoku - Minimalist Sudoku Desktop',
        favicon='🎯',
        port=3000,
        reload=False,
        show=False,
    )


def main_desktop():
    # Start NiceGUI server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    time.sleep(1.2)
    url = 'http://localhost:3000'

    # Try opening inside a native PyWebView window if available
    try:
        import webview
        webview.create_window(
            'ZenSudoku - Minimalist Sudoku Desktop',
            url,
            width=540,
            height=860,
            resizable=True,
            min_size=(400, 600),
        )
        webview.start()
    except ImportError:
        # Fallback to default browser
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)


if __name__ == '__main__':
    main_desktop()

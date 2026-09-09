"""Launch the bundled Streamlit application on loopback with a small desktop controller."""
import argparse
import ctypes
import json
import multiprocessing
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser

APP_NAME = 'K Vitrimer Analysis'
VERSION = '1.0.0'


def resource_root():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def server_options(port):
    return {
        'server.address': '127.0.0.1',
        'server.port': port,
        'server.headless': True,
        'server.fileWatcherType': 'none',
        'server.showEmailPrompt': False,
        'browser.serverAddress': '127.0.0.1',
        'browser.gatherUsageStats': False,
        'client.toolbarMode': 'minimal',
        'global.developmentMode': False,
    }


def watch_parent(pid):
    """Also stop the server if Windows terminates the launcher unexpectedly."""
    if sys.platform != 'win32' or not pid:
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
    if not handle:
        os._exit(0)
    try:
        kernel.WaitForSingleObject(handle, 0xFFFFFFFF)
    finally:
        kernel.CloseHandle(handle)
    os._exit(0)


def serve(port, parent_pid):
    # Windowed PyInstaller executables start without stdout/stderr.
    log_dir = Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / APP_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / f'server-{os.getpid()}.log').open('w', encoding='utf-8', buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            threading.Thread(target=watch_parent, args=(parent_pid,), daemon=True).start()
            os.environ['MPLBACKEND'] = 'Agg'
            from streamlit.web import bootstrap
            options = server_options(port)
            bootstrap.load_config_options(flag_options=options)
            bootstrap.run(str(resource_root() / 'can_relax/gui/app.py'), False, [], options)
        except BaseException:
            traceback.print_exc()
            raise


class LocalServer:
    def __init__(self):
        self.port = free_port()
        self.url = f'http://127.0.0.1:{self.port}'
        self.process = None
        # Bypass configured corporate proxies for this machine's local server.
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def start(self):
        command = [sys.executable]
        if not getattr(sys, 'frozen', False):
            command.append(str(Path(__file__).resolve()))
        command += ['--serve', '--port', str(self.port), '--parent-pid', str(os.getpid())]
        env = os.environ.copy()
        env['PYTHONUTF8'] = '1'
        self.process = subprocess.Popen(
            command, cwd=resource_root(), env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )

    def ready(self):
        if self.process is None or self.process.poll() is not None:
            return False
        try:
            with self.http.open(self.url + '/_stcore/health', timeout=.3) as response:
                return response.status == 200 and response.read() == b'ok'
        except (OSError, urllib.error.URLError):
            return False

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)


def run_desktop():
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry('470x245')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text=APP_NAME, font=('Segoe UI', 18, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Offline desktop edition', font=('Segoe UI', 11)).pack(anchor='w', pady=(4, 18))
    status = tk.StringVar(value='Starting the analysis application…')
    ttk.Label(frame, textvariable=status, wraplength=420).pack(anchor='w')
    ttk.Label(frame, text='Keep this window open while you work in your browser.\nClosing it stops the application.',
              wraplength=420).pack(anchor='w', pady=12)
    server = LocalServer()
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x')

    def open_browser():
        if not webbrowser.open(server.url):
            status.set('Open this address in your browser: ' + server.url)

    launch = ttk.Button(buttons, text='Open application', command=open_browser, state='disabled')
    launch.pack(side='left')

    def close():
        server.stop()
        root.destroy()

    ttk.Button(buttons, text='Quit', command=close).pack(side='right')
    root.protocol('WM_DELETE_WINDOW', close)
    deadline = time.monotonic() + 90
    opened = False

    def poll():
        nonlocal opened
        if server.process.poll() is not None:
            status.set('Startup stopped. See the server log in %LOCALAPPDATA%\\' + APP_NAME)
            launch.configure(state='disabled')
            return
        if not opened:
            if server.ready():
                opened = True
                status.set('Running locally at ' + server.url)
                launch.configure(state='normal')
                open_browser()
            elif time.monotonic() > deadline:
                server.stop()
                status.set('Startup timed out. See the server log in %LOCALAPPDATA%\\' + APP_NAME)
                return
        root.after(1000 if opened else 300, poll)

    try:
        server.start()
        root.after(100, poll)
        root.mainloop()
    finally:
        server.stop()


def main():
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=8501, help=argparse.SUPPRESS)
    parser.add_argument('--parent-pid', type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument('--self-test', type=Path, metavar='REPORT_JSON', help='Verify the offline bundle without opening a browser')
    args = parser.parse_args()
    if args.serve:
        serve(args.port, args.parent_pid)
    elif args.self_test:
        report = {'version': VERSION, 'frozen': bool(getattr(sys, 'frozen', False)), 'ok': False}
        try:
            from desktop.verify_bundle import verify
            report.update(verify())
            report['ok'] = True
        except Exception:
            report['error'] = traceback.format_exc()
        args.self_test.parent.mkdir(parents=True, exist_ok=True)
        args.self_test.write_text(json.dumps(report, indent=2), encoding='utf-8')
        return 0 if report['ok'] else 1
    else:
        run_desktop()
    return 0


if __name__ == '__main__':
    # Needed for source execution as well as the frozen entry point.
    sys.path.insert(0, str(resource_root()))
    raise SystemExit(main())

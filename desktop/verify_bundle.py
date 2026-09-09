"""A real application smoke test runnable inside the frozen executable."""
import io
from pathlib import Path
import re
import socket
import tempfile
import time
import sys


def verify():
    from desktop.launcher import LocalServer, resource_root, server_options
    from streamlit import config
    from streamlit.testing.v1 import AppTest
    from PIL import Image
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import pandas as pd
    from can_relax.gui.exporting import figure_bytes

    if sys.platform == 'win32':
        import tkinter as tk
        controller = tk.Tk()
        controller.withdraw()
        controller.update_idletasks()
        controller.destroy()

    # Block outbound connections in the analysis process. Loopback remains
    # available to verify the HTTP server and its bundled frontend resources.
    original_connect = socket.socket.connect

    def offline_connect(sock, address):
        if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
            raise RuntimeError(f'Offline test blocked external connection: {address}')
        return original_connect(sock, address)

    socket.socket.connect = offline_connect
    server = LocalServer()
    try:
        server.start()
        deadline = time.monotonic() + 90
        while not server.ready():
            if server.process.poll() is not None:
                raise RuntimeError('Packaged HTTP server exited before startup; inspect the server log.')
            if time.monotonic() > deadline:
                raise TimeoutError('Packaged HTTP server did not become ready in 90 seconds.')
            time.sleep(.25)
        with server.http.open(server.url, timeout=10) as response:
            html = response.read().decode('utf-8')
        scripts = re.findall(r'src="(\.?/?static/[^\"]+\.js)"', html)
        if not scripts:
            raise RuntimeError('Streamlit frontend JavaScript is missing from the bundle.')
        for script in scripts:
            with server.http.open(server.url + '/' + script.removeprefix('./').lstrip('/'), timeout=10) as response:
                if response.status != 200 or len(response.read()) < 100:
                    raise RuntimeError('Bundled frontend script is unavailable.')
        for key, value in server_options(server.port).items():
            config.set_option(key, value)
        app = AppTest.from_file(str(resource_root() / 'can_relax/gui/app.py'), default_timeout=90).run()
        if app.exception:
            raise RuntimeError(str(app.exception))
        app.checkbox(key='use_example_data').check().run()
        next(button for button in app.button if 'Run Analysis' in button.label).click().run()
        if app.exception:
            raise RuntimeError(str(app.exception))
        results = app.session_state['results']
        if len(results) != 4 or not all(result['Valid'] for result in results):
            raise RuntimeError('Bundled example analysis failed.')
        next(button for button in app.button if 'Generate Mastercurve' in button.label).click().run()
        if app.exception or 'master_data' not in app.session_state:
            raise RuntimeError('Bundled mastercurve workflow failed.')
        with tempfile.TemporaryDirectory() as temp_dir:
            xlsx = Path(temp_dir) / 'roundtrip.xlsx'
            pd.DataFrame({'value': [1., 2.]}).to_excel(xlsx, index=False)
            if pd.read_excel(xlsx)['value'].tolist() != [1, 2]:
                raise RuntimeError('Excel support is unavailable.')
        fig, ax = plt.subplots(figsize=(2, 2))
        ax.plot([0, 1], [1, 0])
        exports = {}
        try:
            for fmt in ('tiff', 'jpg', 'pdf', 'svg'):
                payload = figure_bytes(fig, fmt, dpi=300)
                if len(payload) < 100:
                    raise RuntimeError(f'Empty {fmt} export.')
                if fmt in ('tiff', 'jpg'):
                    with Image.open(io.BytesIO(payload)) as image:
                        image.load()
                        exports[fmt] = {'format': image.format, 'size': list(image.size)}
                else:
                    exports[fmt] = {'bytes': len(payload)}
        finally:
            plt.close('all')
        return {'http': 'ok', 'frontend_scripts': len(scripts), 'example_curves': len(results),
                'mastercurve': 'ok', 'excel': 'ok', 'exports': exports,
                'desktop_window': 'ok' if sys.platform == 'win32' else 'not tested',
                'analysis_outbound_connections': 'blocked during test'}
    finally:
        server.stop()
        socket.socket.connect = original_connect

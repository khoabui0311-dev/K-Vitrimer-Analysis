"""Reproduce the audit's file inventory, dependency snapshot and export specimens.

Run from the repository root with: python shared_review/audit_reproduce.py
This does not modify experimental data or historical scientific review outputs.
"""
import ast
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def main():
    output = ROOT / 'shared_review' / 'audit_evidence'
    output.mkdir(exist_ok=True)
    inventory = []
    for directory, names, files in os.walk(ROOT):
        names[:] = [name for name in names if name not in
                    ('.git', '.venv', '__pycache__', '.pytest_cache', 'audit_evidence')
                    and not name.startswith('.pytest_tmp')]
        for filename in sorted(files):
            path = Path(directory) / filename
            raw = path.read_bytes()
            item = {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest()}
            if path.suffix == '.py':
                tree = ast.parse(raw, filename=str(path))
                item.update(syntax='pass', lines=len(raw.splitlines()),
                            functions=sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree)))
            elif path.suffix == '.json':
                json.loads(raw)
                item['json_syntax'] = 'pass'
            inventory.append(item)
    (output/'file_inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
    packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
    (output/'environment.json').write_text(json.dumps({'python': sys.version, 'packages': packages}, indent=2), encoding='utf-8')
    if '--inventory-only' in sys.argv:
        print(f'Inventoried {len(inventory)} project files; all Python and JSON syntax checks passed.')
        return

    import matplotlib
    matplotlib.use('Agg')
    from PIL import Image
    from streamlit.testing.v1 import AppTest
    from can_relax.gui.tabs import tab_pub_main
    from can_relax.gui.exporting import figure_bytes

    figures = {}
    def capture(fig, title, *args):
        figures[title] = fig
    original = tab_pub_main.save_and_download
    tab_pub_main.save_and_download = capture
    try:
        app = AppTest.from_file(str(ROOT/'can_relax/gui/app.py'), default_timeout=90).run()
        app.checkbox(key='use_example_data').check().run()
        next(b for b in app.button if 'Run Analysis' in b.label).click().run()
        app.checkbox(key='sh_fig3').check().run()
        app.checkbox(key='sh_fig4').check().run()
        assert not app.exception, list(app.exception)
        for name, fig in figures.items():
            (output/f'{name}_preview.png').write_bytes(figure_bytes(fig, 'png', 180))
        fig = figures['Relaxation_Curves']
        metadata = {}
        for fmt, dpi in [('tiff', 1200), ('jpg', 600)]:
            content = figure_bytes(fig, fmt, dpi)
            (output/f'Relaxation_Curves.{fmt}').write_bytes(content)
            with Image.open(io.BytesIO(content)) as specimen:
                metadata[fmt] = {'pixels': specimen.size, 'dpi': [float(v) for v in specimen.info['dpi']], 'mode': specimen.mode}
        (output/'export_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(json.dumps({'files': len(inventory), 'python_files': sum(p['path'].endswith('.py') for p in inventory),
                          'exports': metadata}, indent=2))
    finally:
        tab_pub_main.save_and_download = original


if __name__ == '__main__':
    main()

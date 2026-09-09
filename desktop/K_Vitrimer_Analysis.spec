# Build from the repository root with python -m PyInstaller desktop/K_Vitrimer_Analysis.spec
from pathlib import Path
from importlib import metadata
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
sys.path.insert(0, str(root))
# A venv may be based on a Conda Python, whose DLLs live in Library/bin.
conda_bin = Path(sys.base_prefix) / 'Library/bin'
binaries = []
if conda_bin.is_dir():
    os.environ['PATH'] = str(conda_bin) + os.pathsep + os.environ.get('PATH', '')
    for name in ('sqlite3.dll', 'tk86t.dll', 'tcl86t.dll'):
        if (conda_bin / name).exists():
            binaries.append((str(conda_bin / name), '.'))
datas = [(str(root / 'examples/toy_data.csv'), 'examples'), (str(root / 'LICENSE'), '.')]
# Streamlit executes this source file and its imports at runtime.
for source in (root / 'can_relax').rglob('*.py'):
    datas.append((str(source), str(source.relative_to(root).parent)))
datas += collect_data_files('streamlit')
for package in ('streamlit', 'numpy', 'pandas', 'scipy', 'matplotlib', 'plotly',
                'openpyxl', 'scikit-learn', 'Pillow'):
    datas += copy_metadata(package, recursive=True)

# Keep redistribution notices for the installed dependencies in the package.
for distribution in metadata.distributions():
    for item in distribution.files or []:
        if any(part.lower().startswith(('license', 'copying', 'notice')) for part in item.parts):
            source = Path(distribution.locate_file(item))
            if source.is_file():
                datas.append((str(source), str(Path('third_party_licenses') / distribution.metadata['Name'] / item.parent)))
for name in ('LICENSE.txt', 'LICENSE_PYTHON.txt'):
    python_license = Path(sys.base_prefix) / name
    if python_license.exists():
        datas.append((str(python_license), 'third_party_licenses/Python'))
runtime_notices = Path(sys.base_prefix) / 'bundle_license.rtf'
if runtime_notices.exists():
    datas.append((str(runtime_notices), 'third_party_licenses/PythonRuntime'))

hiddenimports = collect_submodules('can_relax') + collect_submodules('streamlit')
hiddenimports += ['desktop.verify_bundle', 'desktop.launcher', 'openpyxl',
                  'matplotlib.backends.backend_agg', 'matplotlib.backends.backend_pdf',
                  'matplotlib.backends.backend_svg']
a = Analysis(
    [str(root / 'desktop/launcher.py')], pathex=[str(root)],
    binaries=binaries, datas=datas, hiddenimports=hiddenimports,
    hookspath=[], hooksconfig={'matplotlib': {'backends': ['Agg']}},
    runtime_hooks=[], excludes=['pytest', 'IPython', 'notebook', 'PyQt5', 'PyQt6', 'PySide6'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='K_Vitrimer_Analysis',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='K_Vitrimer_Analysis')

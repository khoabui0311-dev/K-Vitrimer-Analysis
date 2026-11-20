# Running VitriFit 2.0 locally (development beta)

VitriFit 2.0 is in a separate development branch. The original Streamlit
application and its Publication tab remain available in v1.

## Windows — quick start

1. Install Python 3.11+ and Node.js 22+ on your development machine.
2. Check out the vitrifit2 branch and double-click run_v2.bat.
3. The first startup creates a Python virtual environment, installs the
   existing scientific dependencies plus FastAPI, installs the web dependencies
   and builds the React interface. This step needs internet.
4. Open http://127.0.0.1:8000 — all raw data and the SQLite database remain
   on this computer. Subsequent runs do not require internet once dependencies
   and the web bundle are installed.
5. Close the launch terminal to stop the local server.

The existing v1 Streamlit app can be launched separately using run_app.bat.
The two interfaces do not share a live session; the new persistent library is
stored separately.

## Other operating systems / manual developer start

    python -m pip install -r requirements.txt -r requirements-v2.txt
    cd vitrifit2/web
    npm install
    npm run build
    cd ../..
    python run_v2.py

For hot-reload development instead of production build, start
python run_v2.py in one terminal, then cd vitrifit2/web && npm run dev
in another terminal, and open http://127.0.0.1:5173.

## Data safety

- The application binds to 127.0.0.1:8000 only. There is no login; do not
  deploy the service to a public host or LAN.
- By default, persistent data is at ~/.vitrifit2 (Windows user home).
  Override with VITRIFIT2_DATA_DIR if needed.
- Use the **Download complete local-library backup** link in the Library tab.
  The resulting ZIP contains vitrifit.sqlite3, raw_blobs/<SHA256> and manifest.json.
- To restore a backup: stop both v1 and v2 local services, make a separate
  copy of the existing target directory, then extract the ZIP into the target
  directory. Start the app again and verify the project and experiment list.
- Keep independent offline backups, especially before upgrading the software.
- Editing a curve produces masks and revisions, never destructive changes to
  the original uploaded file. A new edit flags earlier fitting runs as stale.
- Inputs are subject to current parser limitations: CSV/TXT/XLSX, wide
  relaxation time/modulus data (canonical seconds/MPa/°C). Legacy XLS requires
  conversion. DMA, DSC and tensile import are not yet available in v2.

## Current feature status

Implemented on branch: projects/samples/experiments, immutable uploaded files,
independent curve trimming, undo/redo, auto trim proposal, revision-pinned
Maxwell/KWW/Prony fitting, saved runs, fixed-temperature & kinetic comparisons,
per-sample kinetic windows, style presets, saved figure-project records, and
local database backup.

Still incomplete: browser UI acceptance testing with real instrument files,
publication render parity in the new UI, image-diff regression specimens,
multi-panel export, fitting uncertainty expansion, desktop installer packaging,
and additional DMA/DSC/tensile modules.

Do not replace v1 for production publication work until the parity matrix
in PUBLICATION_PARITY.md is checked.

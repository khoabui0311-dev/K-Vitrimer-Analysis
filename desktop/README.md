# Windows offline distribution

The desktop edition bundles the existing Streamlit application and scientific
libraries with PyInstaller. Inno Setup provides per-user installation, Start menu
and optional desktop shortcuts, upgrades, and uninstallation. The interface runs
in the user's web browser; a small native launcher starts and stops the server.

## Install and use

1. Run `dist/K_Vitrimer_Analysis_Setup_1.0.0_x64.exe`.
2. Launch **K Vitrimer Analysis** from the desktop or Start menu.
3. Use the browser interface normally. Save downloaded results before quitting.
4. Click **Quit** in the launcher to stop the server. Closing the browser tab alone
   does not stop it; **Open application** reopens the interface.

The intended target is Windows 10/11 x64. No Python or internet connection is
required at runtime. The local server listens only on `127.0.0.1`, uses an
available port, disables Streamlit usage telemetry, and retains default CORS and
XSRF protection. Files are processed locally. Citation links need internet access.
The installer does not require administrator privileges. It installs under
`%LOCALAPPDATA%\Programs\K Vitrimer Analysis` by default. Uninstall through
Windows Settings > Apps. Diagnostic logs are under
`%LOCALAPPDATA%\K Vitrimer Analysis`; these are retained after uninstall.

This first build is unsigned. Windows may display an unknown-publisher warning.
Public distribution should add publisher code signing and testing on clean
Windows machines. macOS and Linux installers are not included.

## Build

Build on Windows x64 with Python 3.11+ and [Inno Setup 6](https://jrsoftware.org/isdl.php):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File desktop\build_windows.ps1
```

Pass `-InnoCompiler 'C:\path\to\ISCC.exe'` if it is not detected. Pass
`-SkipInstaller` to build and verify the portable folder only. The build machine
needs internet to install dependencies; the resulting application does not.
Do not copy only the launcher EXE: the entire `dist/K_Vitrimer_Analysis` folder
is required for portable use. The Setup EXE includes that complete folder.

Outputs under ignored `dist/`:

- `K_Vitrimer_Analysis/`: complete portable application.
- `K_Vitrimer_Analysis_Setup_1.0.0_x64.exe`: installable package.
- `K_Vitrimer_Analysis_Setup_1.0.0_x64.exe.sha256`: download verification hash.
- `desktop-self-test.json`: packaged application verification report.

The build refuses to produce an installer if its bundled self-test fails. That
test checks HTTP startup and frontend JavaScript, four example curve analyses,
mastercurve generation, Excel reading/writing, and TIFF/JPEG/PDF/SVG exports.
It blocks outbound socket connections in the analysis test process. The HTTP
server runs in a separate process, so this is not a system-wide network block.
The regression suite separately checks launching from another working folder
and server shutdown. The Windows parent-process watcher stops orphaned servers.

Run the same test on a portable or installed build:

```powershell
$exe = 'C:\path\to\K_Vitrimer_Analysis.exe'
Start-Process -FilePath $exe -ArgumentList '--self-test "C:\path\to\report.json"' -Wait
Get-Content 'C:\path\to\report.json'
```

On a Windows account without an existing installation, run
`desktop\test_installer.ps1` to test silent installation into `dist/installer-test`,
run the installed application from another working folder without Python on PATH,
and uninstall the test copy. It avoids creating shortcuts during the test and
refuses to overwrite an existing installation.

Third-party license files and package metadata are bundled under `_internal`.
The application remains covered by the repository's Academic and Research License.

## Implementation references

- [PyInstaller runtime resource paths](https://pyinstaller.org/en/stable/runtime-information.html).
- [Inno Setup per-user installation](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm).

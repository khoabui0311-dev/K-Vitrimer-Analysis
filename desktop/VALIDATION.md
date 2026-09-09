# Desktop edition 1.0.0 validation

Built and checked on Windows x64 on 2026-09-09 with Python 3.11.13,
Streamlit 1.58.0, PyInstaller 6.22.2, and Inno Setup 6.7.3.

- Full regression suite: **165 passed**. Final focused desktop checks: **3 passed**.
- Fatal-error lint and dependency compatibility checks passed. Desktop Bandit
  scan reported no medium- or high-severity findings.
- Frozen executable passed with Python/development tools removed from PATH and
  PYTHONPATH cleared: native Tk window initialization, localhost HTTP and frontend
  JavaScript, four example curve fits, mastercurve generation, Excel round trip,
  and TIFF/JPEG/PDF/SVG exports. Analysis-process outbound sockets were blocked
  during this smoke test; the separate HTTP process was not network-isolated.
- Browser verification of the frozen server displayed four processed curves,
  the fitted curves, and the fitting-parameter table.
- The final installer was installed silently into a temporary project folder.
  The installed executable passed the same smoke test from a different working
  directory with Python removed from PATH. Uninstallation removed its executable
  and Windows uninstall registration. No test server processes remained.
- Python runtime and third-party notices are included in the bundle. The final
  installer is **104,294,344 bytes** (about 104 MB).

Installer SHA-256:

```text
cebc65d2ddde63705e5fc493581c3691aec6cdf9b20c2f735c5e984fd4f7393b
```

The local reports are `dist/desktop-self-test.json` and
`dist/installed-self-test.json`. Build outputs are ignored by Git; the manual
GitHub Actions desktop workflow builds an installer artifact and both reports.

This is an unsigned first Windows build. It has not yet been tested on a clean
Windows virtual machine or other users' computers, and no macOS/Linux installer
has been produced. The existing scientific-validation limitations still apply.

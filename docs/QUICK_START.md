# Getting started with VitriFit 2.0

This is release candidate **2.0.0-rc.1** for Windows 10/11 x64.

1. Obtain `VitriFit_Setup_2.0.0-rc.1_x64.exe` from the project's release assets
   or the researcher distributing this candidate. Downloading the repository's
   source ZIP does not include the installer. Do not assume a public release
   exists until it is listed under GitHub Releases.
2. Run the installer. No separate Python installation or administrator account
   is required. The candidate is unsigned; verify the distributor and the
   accompanying SHA-256 checksum.
3. Launch **VitriFit** from the Start menu or desktop shortcut. Keep the launcher
   window open while working in the browser. Analysis runs on your computer.
4. Select **Use toy_data.csv Example**, then **Run Analysis** to try the workflow.
5. Upload your own CSV/XLSX. Use paired Time/Modulus columns under temperature
   headers, or repeating Temp/Time/Modulus triplets. Explicitly label units:
   Celsius, seconds or minutes, and Pa/kPa/MPa. Unlabelled values are interpreted
   as Celsius, seconds, and MPa. Import relaxation modulus, not raw stress or G'.
6. Set the loading time origin, cutoff and below-Tg exclusion threshold. Review
   point exclusions and import notices. Fit a model, then inspect residuals,
   fit warnings and the measurement time range.
7. For two exponentials, select **Two-Maxwell (Prony)**. Choose **Zero** for
   `G(t)=G_fast exp(-t/tau_fast)+G_slow exp(-t/tau_slow)`. Fixed/Fit adds a
   long-time plateau. Each temperature is fitted independently.
8. Select fast or slow fitted time for kinetics. Arrhenius regression is separate
   from the curve fits. Review the selected temperatures and uncertainty; a
   straight fitted line does not establish Arrhenius behavior or a mechanism.
9. Save the fit CSV, kinetics selection, Arrhenius result, figures and provenance
   JSON before quitting. Sessions are in memory and are not saved automatically.
10. Use **Quit** in the launcher when finished. Closing only the browser tab
    leaves the local server running.

## Updating from K Vitrimer Analysis

The installer retains the previous application's Windows identity so it can
upgrade the existing installation. It may keep the previous installation folder.
The new shortcut and executable are named VitriFit. Close the old application
before updating. Upgrade behavior needs verification on a clean test account
before general distribution.

## Reporting a problem

Use the repository's Issues page. Include the software version, Windows version,
selected model/plateau, steps to reproduce, and the error text. Share a small
synthetic or nonconfidential data sample if possible. Provenance contains selected
settings and results; inspect it before sharing. Diagnostic logs are in
`%LOCALAPPDATA%\VitriFit`.

The Academic and Research License in the repository applies. This candidate is
not an independently validated measurement method.

# Getting started with VitriFit 2.0

Release candidate **2.0.0-rc.2** for Windows 10/11 x64. No separate Python
installation is needed. Analysis works offline in your web browser.

The newer source development preview adds a **Fit reliability** tab. Its workflow
and interpretation are described in [Fit reliability](FIT_RELIABILITY.md); that
feature is not included in the rc.2 installer described below.

## Install and open

1. Open [GitHub Releases](https://github.com/khoabui0311-dev/K-Vitrimer-Analysis/releases)
   and download `VitriFit_Setup_2.0.0-rc.2_x64.exe` and its `.sha256` file from
   the rc.2 release. The source ZIP is not the installer.
2. Check the installer checksum against the accompanying file. The candidate
   is unsigned; Windows may show an unknown-publisher notice. Use only the
   release assets from this repository.
3. Close any running VitriFit/K Vitrimer Analysis launcher, then run Setup.
   Installation is per user and does not need administrator access.
4. Launch **VitriFit** from the Start menu. It opens a local browser page.
   Keep the small launcher window open while you work. **Quit** stops the app.

## Your first analysis

1. In **Analysis → Bring in your data**, select **Use toy_data.csv Example**
   to practice, or upload a CSV/XLSX. Check the curve count and temperatures.
2. Open **Data review: timing and incorrect points**. Select a curve, then
   use a graph box/lasso, point-number ranges such as `2-10, 25-30`, or a time
   interval. Click **Exclude highlighted points** once for the group.
   **Undo last point edit** reverses mistakes. Point numbers refer to original
   imported rows. Review each curve separately.
3. Set the loading origin and early-time cutoff if needed. Review the below-Tg
   exclusion setting; it defaults to 50 °C and must suit your material.
4. Under **Choose your fit**, select Maxwell, Single KWW or **Two-Maxwell (Prony)**.
   For the two-term equation below, choose **Long-time plateau → Zero**:

   `G(t) = G_fast exp(-t/tau_fast) + G_slow exp(-t/tau_slow)`

   Fixed/Fit adds a plateau. Each temperature is fitted independently; no
   Arrhenius law is imposed on these curve fits.
5. Click **Run Analysis**. Inspect residuals and warnings as well as the fitted
   curves. A high R² alone does not mean both times are reliable. Compare models
   using the same observations under **Compare models** if useful.
6. For kinetics, choose the fitted fast/slow component and included temperatures.
   This regression happens after independent curve fitting. A straight line
   does not establish Arrhenius behavior or identify molecular mechanisms.

## Save, reopen and export

- Open the sidebar using the arrow at the upper left. **Save project** downloads
  a `.vfit` containing the original data, exclusions, analysis choices and figure
  formatting. Move it from Downloads to your experiment folder.
- After restarting, use **Open a saved project → Open project**. Fits are
  recalculated. Check any version-mismatch notice and retain previous exports
  when you need an unchanged record.
- Download fit parameters and kinetics CSVs from the results. In **Report**,
  prepare the offline HTML report and JSON snapshot. The HTML opens without the
  app; your browser's Print → Save as PDF produces a printable report.
- In **Publish**, adjust figures and show/hide fits or the Tv marker. Prepare
  SVG/PDF for vector figures, or TIFF/JPEG for raster figures. Changed settings
  require preparing the download again.
- Under **Save or load figure formatting**, save a `.vstyle` to reuse colors,
  sizes, fonts and labels. When loading it for new data, optionally choose
  automatic axis limits. Undo restores the previous apply/reset.
- Saving is explicit: closing the app does **not** automatically save your work.
  Projects and reports contain experimental measurements; format files do not.

## Prepare your input

Use paired Time/Modulus columns under temperature headers, or repeating
Temperature/Time/Modulus triplets. XLSX imports the first worksheet. Label units:
°C, seconds or minutes, and Pa/kPa/MPa. Unlabelled values are interpreted as °C,
seconds and MPa. Import relaxation modulus, not raw stress or storage modulus G'.
Convert stress using the imposed strain before importing. Convert old XLS files
to XLSX. The repository's `examples/toy_data.csv` is a working input example.

## Updating and reporting problems

The installer retains the previous product's Windows identity and should reuse
its installation folder. Save your projects and exports and close the app before
upgrading. See the release's verification reports for tested upgrade paths.

Report problems through [Issues](https://github.com/khoabui0311-dev/K-Vitrimer-Analysis/issues).
Include the software/Windows versions, model and plateau choices, steps and error
text. Use synthetic or nonconfidential samples when sharing data. Diagnostic logs
are under `%LOCALAPPDATA%\VitriFit`.

The Academic and Research License applies. See the release notes and validation
report for scientific limitations. This candidate is not an independently
validated measurement method.

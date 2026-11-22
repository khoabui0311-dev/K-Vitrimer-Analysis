# VitriFit 2.0 workspace guide

Version **2.0.0-rc.2** includes publication export controls, bulk point review,
an offline analysis report and expanded project restoration alongside model
comparison. The earlier `2.0.0-rc.1` installer does not include these additions.

## Try the workflow

1. Start the app from this branch. In **Analysis**, use **Bring in your data**
   to upload a CSV/XLSX or select **Use toy_data.csv Example**.
2. Check the source name, number of curves, measurements and temperatures.
   Expand **Data review: timing and incorrect points** to adjust each curve's
   loading origin/cutoff and exclude incorrect observations.
3. In **Choose your fit**, choose the model and plateau policy. Expand
   **Timing and material settings** for the global defaults and Tg threshold.
4. Click **Run Analysis**. **Understand your results** shows how many curves
   fitted and how many carry fit warnings. Residuals are expanded in **Curves**.
5. In **Compare models**, choose one curve and click **Compare three models**.
   Review the table, overlaid fits and residuals. The comparison fits Maxwell,
   single KWW and two-Maxwell using the same observations and plateau policy.
   It neither changes the current analysis nor imposes Arrhenius behavior.
6. Optionally choose a model and click **Use this model and refit all curves**.
   This is an explicit user decision. Scores from one curve are not a global
   model recommendation and do not identify physical mechanisms.

## Exclude many points at once

In **Data review**, select the curve and drag a box over its graph. The graph
toolbar also offers lasso selection. Click **Exclude highlighted points** to
remove the whole group from fitting, or **Restore highlighted points** to keep it.

Alternatively, select **Point numbers** and enter inclusive ranges such as
`1-40, 75-90`, or select **Time interval** and enter inclusive elapsed-time bounds.
Point numbers always refer to original imported rows, even when times are duplicated
or unsorted. Actions apply only to the current curve.

**Undo last point edit** reverses up to 30 changes in the open session, including
individual table edits. **Restore all manually excluded points** clears that curve's
manual exclusions. The table remains available under **Individual points and reviewed
data table**. Restoring points does not override the loading origin or time cutoff.
Run Analysis again after edits. Saved projects retain exclusions; undo history is
only kept in the current session.

## Save and reopen

Use **Save project** in the sidebar to download an `analysis.vfit` file. If the
sidebar is collapsed, open it with the arrow at the upper left.

The project contains the original input file (up to 25 MB), its checksum,
software version, model/plateau, Tg, rubbery modulus, kinetics base, global and
per-curve time settings, excluded points, and the selected curves. It also saves
the kinetics model, fitted component and excluded curves; mastercurve reference
temperature/replicate and modulus convention; spectrum settings; curve display
options; report title/notes; and publication formatting, including colors and fit visibility.

Open the file through **Open a saved project → Open project**. If the saved
workspace had an analysis or mastercurve, it is recalculated with the current software. A
version mismatch is reported. Results can change across software versions;
retain exported numerical results and provenance for the original analysis.

Older project files remain readable and use defaults for missing downstream
choices or publication formatting; the interface reports this. Model-comparison
runs are not saved. Review those again and keep their exported results.
Projects contain the source data; consider that before sharing a project file.

**New project** clears the open workspace. Download your project and exports
before using it. Saving is explicit; closing the app does not automatically
save a project.

Malformed projects, unsupported versions, source checksum mismatches and curve
settings that do not match the source are rejected before replacing the open
workspace. Projects are JSON data and do not deserialize executable objects.

## Create an analysis report

After running the analysis, choose the curves to include and open **Report**.
Enter a title and research notes, then click **Prepare analysis report**.
Download the HTML report and its JSON numerical snapshot. The report contains:

- Selected curves, fit parameters with local standard errors, residuals and warnings.
- The current kinetics selection and regression, including excluded rows.
- The current mastercurve if generated, spectrum estimates, and model comparison if run.
- Preprocessing choices, source checksum, software version and creation time.

HTML reports contain their own vector figures and styles and require no internet
connection. Open a report in a browser and use Print / Save as PDF to obtain a PDF.
The JSON snapshot preserves the numerical arrays and treats unavailable values as
`null`. The report always uses linear time for curve/residual figures so t = 0 is
not hidden; display-axis preferences are recorded separately.

Changing selections, settings, comparisons or report notes removes outdated
downloads. Prepare the report again to capture the updated calculation. Failed
or unavailable kinetics are labelled explicitly; an earlier successful regression
is never substituted. Saving a project preserves a recipe for recalculation;
saving a report/snapshot preserves a fixed record of the calculation now shown.

Reports contain selected measurements and research notes. Review these before
sharing. They are analysis records, not independent scientific validation.

## Prepare publication figures

In **Publish**, each figure has a fit-visibility switch: **Show fitted curves**
for relaxation curves, or **Show fitted line** for Arrhenius/VFT, Eyring and
Van 't Hoff plots. Hiding a fit also removes its legend entry; measured points
remain visible. The fitted parameters above the figure are still available.
The Arrhenius **Show T_v** control independently shows or hides the Tv marker.

Use **Prepare SVG / PDF downloads** below any figure for scalable RGB exports.
These exports retain vector lines and text and follow the visible fit/legend
choices. They use RGB even when the global raster color setting is CMYK.
Use **Prepare TIFF / JPEG downloads** for raster files in the selected color
space; TIFF offers 300, 600 or 1200 DPI and JPEG uses 600 DPI.

Changing a figure setting removes previously prepared download controls.
Prepare the files again after editing so they reflect the current figure.
Publication styling is included in new `.vfit` projects (schema 3). Earlier
schema 1 and 2 projects reopen with default publication formatting.

## Save and reuse figure formats

In **Publish → Save or load figure formatting**, enter a format name and click
**Save figure format** to download a `.vstyle` file. It contains publication
settings, not experimental data: figure and fit visibility, dimensions, fonts,
colors, panel labels/positions, legends, display units, normalization, publication
kinetics model, axis choices and TIFF resolution. Custom axis bounds are included
when they have been set. Unvisited controls use the app defaults.

To reuse it, select the `.vstyle` file, review its name and physical dimensions,
and click **Apply figure format**. This
replaces the publication settings while keeping the data, point exclusions and
main analysis. Check units, axis ranges and the publication model when applying
a format to a different dataset. Choose **Use automatic axis limits when applying**
to recalculate the plot bounds while keeping the saved units and scales.
**Reset figure formatting** restores defaults without clearing the analysis.
**Undo format apply or reset** restores the formatting from immediately before
the most recent apply/reset, including its name. Undo is available for the current
session and is cleared when opening another project.
Settings of temporarily hidden figures remain
available when those figures are enabled again.

**Figure colors** lets you choose kinetics marker/fit colors and the six-color
relaxation palette. The palette repeats for additional curves. Project files
also keep these settings; a separate format file is useful when sharing a
journal format without sharing measurements. Invalid or unsupported format
files are rejected before replacing the current formatting.
Named journal presets must match their stated dimensions; use **Custom** for
another size. A format containing custom dimensions alone is treated as Custom,
so its size is not replaced by the default journal preset.

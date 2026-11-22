# VitriFit workspace preview

Version **2.0.0-dev.2** adds a working analysis workspace, portable project files,
and a dedicated comparison of relaxation models. These features are in the
development source, not in the published `2.0.0-rc.1` installer.

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

## Save and reopen

Use **Save project** in the sidebar to download an `analysis.vfit` file. If the
sidebar is collapsed, open it with the arrow at the upper left.

The project contains the original input file (up to 25 MB), its checksum,
software version, model/plateau, Tg, rubbery modulus, kinetics base, global and
per-curve time settings, excluded points, and the selected curves.

Open the file through **Open a saved project → Open project**. If the saved
workspace had an analysis, it is recalculated with the current software. A
version mismatch is reported. Results can change across software versions;
retain exported numerical results and provenance for the original analysis.

Kinetics temperature selections, downstream model choices, mastercurves,
spectrum settings, comparison runs and plot styling are not saved in this
first project format. Review those again and keep their exported results.
Projects contain the source data; consider that before sharing a project file.

**New project** clears the open workspace. Download your project and exports
before using it. Saving is explicit; closing the app does not automatically
save a project.

Malformed projects, unsupported versions, source checksum mismatches and curve
settings that do not match the source are rejected before replacing the open
workspace. Projects are JSON data and do not deserialize executable objects.

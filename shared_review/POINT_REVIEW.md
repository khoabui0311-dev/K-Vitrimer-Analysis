# Timing and measurement exclusion — 2026-09-07

Open **Data review: timing and incorrect points** after loading a file. The table
allows separate loading origins and short-time cutoffs for each curve. Sidebar
values supply defaults; changing either sidebar default resets the per-curve timing
table. Choose a curve, inspect the point numbers in the preview plot, and uncheck
Keep for incorrect measurements. Recheck Keep to restore them, then Run Analysis.
The source file is never modified. New dataset contents reset exclusions.

Elapsed time = recorded time minus loading origin. The cutoff applies to elapsed
time and does not reset the physical origin. Manual point exclusion is applied
before the existing automatic peak/drift processing and downsampling. Point numbers
are one-based imported observations, not spreadsheet row numbers; they distinguish
duplicate timestamps. Plot colors distinguish selected measurements from manually
excluded or cutoff measurements. The reviewed-points CSV contains both masks.

Exclusion IDs and per-curve timing participate in analysis identity, clearing old
fits and downstream state immediately on edits. Each successful result records a
manual_selection audit in preprocessing, while provenance includes timing and
exclusions for all curves, including skipped ones. Existing fit preprocessing can
still remove further points; the preview explicitly describes that behavior.

The user's VUEG loading time remains unknown: no automatic first-point subtraction
was introduced. The tool now supports different origins when experimentally known.

Validation covers preservation of the physical origin and source data, cutoff
boundaries, individual duplicate-point exclusion, restoration, invalid settings,
and Streamlit state invalidation/persistence and audit recording. Targeted tests:
6 passed in 9.06 seconds. Full-suite result recorded in WORK_LOG.md.

# VitriFit 2.0.0-rc.2 validation record

Assessment date: 22 November 2026. This record distinguishes numerical/software
verification from independent scientific validation. Raw experimental data are
not distributed with the release.

## Experimental consistency and stability

Input: the supplied VUGT workbook, 3 November 2026. SHA-256:
`3bc45a414f0e33dea859d7bba7f359a2464101dcc684c496028099851ceac911`.
The first worksheet provides eight curves. The selected 50 °C exclusion policy
excludes the 40 °C curve; it does not establish the material's physical Tg.
Seven curves from 100 to 180 °C were analysed. This is one experimental dataset,
not validation across multiple materials or laboratories.

Settings: two-Maxwell, zero plateau, loading origin 0 s, no manual exclusions.
The normal application preprocessing and downsampling are retained. All 450
observations per curve (339 at 180 °C) survived preprocessing; fitting uses
169 observations (163 at 180 °C). Units are seconds and MPa. No temperature law
or Arrhenius constraint enters curve fitting.

An independent least-squares solver parameterizes log relaxation times and
amplitude at the retained reference time. It uses 12 starting guesses and the
same normalized observations/objective. Every start reached the same near-best
minimum (RSS within 0.1%) for each curve. Application times agree with the best
independent solution within **0.007%**. This verifies numerical agreement on
these observations, not uniqueness of a physical interpretation.

| Temperature (°C) | Fast time (s) | Slow time (s) | R² | Largest time change using all retained points | Largest time change after removing last 20% of elapsed window |
| --- | ---: | ---: | ---: | ---: | ---: |
| 100 | 239.61 | 2571.64 | 0.9986 | 3.90% | 5.00% |
| 120 | 129.94 | 1489.21 | 0.9984 | 10.68% | 1.51% |
| 140 | 237.55 | 2675.99 | 0.9953 | 6.14% | 11.88% |
| 150 | 466.98 | 8986.89 | 0.9948 | 2.19% | 24.41% |
| 160 | 429.33 | 6007.94 | 0.9994 | 2.08% | 10.97% |
| 170 | 362.06 | 2402.27 | 0.9998 | 1.38% | 3.24% |
| 180 | 191.69 | 1304.58 | 0.9989 | 1.32% | 7.78% |

Sensitivity percentages compare each independent variant with the independent
baseline; the largest absolute relative change across the two times is shown.
Using all observations changes their weighting relative to log downsampling.
Truncation preserves the same reference and does not rerun peak/drift detection.

At 150 °C, the slow time (8987 s) exceeds the final observation (7653 s); VitriFit
reports the existing out-of-window warning. Removing the last 20% of elapsed
time changes the fast time by −24.41% and slow time by −14.21%. These parameters
must not be presented as strongly established just because the curve looks good.

Residual lag-one correlations range from 0.70 to 0.99. The residual plots show
systematic mismatch; high R² alone is insufficient. One hundred centered iid
residual resamples per curve were also computed with seed 20261122 and a fixed
reference/preprocessing. Because the observed residuals are correlated, their
percentile ranges are only conditional numerical sensitivity estimates, **not
validated experimental confidence intervals**. Neither those ranges nor the
application's local covariance capture preprocessing, reference error, model
misspecification, or between-experiment variation.

Conclusion: the current optimizer reproduces an independent multi-start solution
on this dataset. Measurement-window and sampling choices can materially change
parameters. No claim of two molecular mechanisms or Arrhenius behavior follows.
Independent domain review and additional materials/replicates remain necessary
before claiming scientific validation.

## Reproduce the experimental audit

In the application's Python environment, run:

```text
python validation/experimental_prony.py "path/to/VUGT 03_11_2026.xlsx" --output "local-audit-folder"
```

The script writes a detailed JSON record and fit/residual PDF/PNG locally. It
does not modify or upload the input. The workbook is not in the repository;
the holder of the source file can reproduce the audit using the checksum above.
Synthetic tests independently check known two-mode times and delayed references.

## Workflow and desktop verification gates

The candidate's automated workflow imports CSV, excludes original points 2–4
on one curve, runs two-Maxwell fits, saves data/settings/formatting, and opens the
project in a genuinely fresh application session. It compares fitted parameters
and exclusions and generates actual CSV, VFIT, VSTYLE, HTML, JSON, SVG and PDF
exports. File-picker input and download capture are adapted for Streamlit's test
runner; the parser, fitting and export code run normally. This is an integration
test, not an independent first-time-user usability study.

The same fresh-session workflow was also run locally on the supplied XLSX:
seven valid fitted curves reopened with identical parameters; the original
source/exclusions and formatting were preserved, and all seven export types
were generated. The CSV workflow is additionally executed inside each frozen
and installed candidate self-test.

The frozen application's self-test runs that workflow plus mastercurve creation,
Excel read/write and TIFF/JPEG exports. Python DNS and connect/connect_ex calls
outside loopback are blocked in both analysis and server processes. Local HTTP
and bundled frontend assets are checked. This verifies offline operation at the
Python application boundary; it is not a full OS/browser network-isolation test.

The Windows workflow tests clean installation, installed execution without Python
on PATH, and uninstallation. It then installs the checksum-pinned published rc.1,
upgrades without specifying an installation directory, verifies reuse of the
registered folder/version and the new executable, runs the installed self-test,
and checks three user-file sentinels survive upgrade and uninstall. Sentinels
check byte preservation, not project compatibility; fresh-session tests cover
project restoration separately.

The release's attached build/installation/upgrade JSON reports and linked GitHub
runs are authoritative pass/fail evidence for its exact commit. Do not infer a
pass from this procedure alone. Legacy 1.x upgrade results, if performed, are
recorded as separate release attachments. The installer remains unsigned.

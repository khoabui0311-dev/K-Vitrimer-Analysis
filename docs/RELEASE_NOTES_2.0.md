# VitriFit 2.0 release candidate

Version: **2.0.0-rc.1**. Intended release status: **prerelease**, not a stable
or latest release. No DOI has been assigned.

VitriFit is the new product name for K Vitrimer Analysis. It supports independent
Maxwell, KWW and two-Maxwell Prony fitting; optional plateaus; kinetics
regressions; mastercurve exploration; spectrum estimates; and figure/CSV exports.
The Windows installer bundles Python and works offline in a local browser.

## Changes for this candidate

- Consistent product name and shared version in the interface, launcher and exports.
- Versioned analysis provenance and fit/Arrhenius CSVs.
- Explicit distinction between independent curve fitting and subsequent kinetics.
- Arrhenius 95% regression intervals and notices for nonpositive slopes or
  intervals crossing zero. Negative estimates are preserved.
- Updated shortcuts, citation metadata, quick-start guide and artifact manifest.

## Limits to state with the release

- Windows build is unsigned. macOS/Linux installers are not provided.
- Two exponential terms do not by themselves identify two physical mechanisms.
- Per-curve fitting uses automatic preprocessing, logarithmic downsampling,
  retained-reference normalization and one optimization starting point.
- Local covariance and regression intervals do not establish parameter
  identifiability. Arrhenius intervals assume independent equal-variance errors
  in log times and do not propagate each fitted time's uncertainty.
- A slow mode outside the measured window is an extrapolation. TTS overlap,
  spectrum regularization and Maxwell-equivalent Tv require scientific review.
- Sessions are not persistent. Export results before quitting.
- The Academic and Research License applies; commercial use requires permission.

## Candidate publication checklist

- [ ] Full regression/static checks pass at the candidate commit.
- [ ] Frozen executable passes the offline smoke test.
- [ ] Installer installation/uninstallation passes on a clean Windows account.
- [ ] Upgrade from the old product is tested without loss of exported user files.
- [ ] Independent reviewer checks representative experimental data and model assumptions.
- [ ] Installer, SHA-256, build manifest and notes are attached to a draft GitHub release.
- [ ] Release is explicitly published as a prerelease after review.

Test results should be recorded separately with their commit and environment;
do not treat an unchecked item as completed.

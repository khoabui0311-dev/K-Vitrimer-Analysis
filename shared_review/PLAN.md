# Correctness batch — 2026-09-07

1. Explicit 1/e crossing status; incomplete and ambiguous curves excluded from raw kinetics.
2. Preserve elapsed loading time and use conditional model normalization after trimming.
3. Explicit optimizer success/failure, finite predictions, no fabricated fit curves.
4. Shared Van 't Hoff and coupled prediction functions; input validation.
5. Content/configuration-based analysis invalidation and derived-result invalidation.
6. Documented parser layouts, signed temperatures, unit conversion, replicate identity.
7. Restore spectrum amplitudes; state discrete-weight convention and reconstruction error.

Validation: existing tests, focused numerical regressions, Streamlit workflow checks where
available, independent agent review. Broader parameter uncertainty/identifiability and
experimental literature validation remain a later batch.

Ownership: root — preprocessing, fitting, spectrum, GUI, integration; parser agent — parser
and parser tests; kinetics agent — kinetics and kinetics tests; review agent — independent review.

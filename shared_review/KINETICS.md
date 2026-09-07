# Kinetics corrections — shared agent review

Status: implemented; targeted verification passed.

## Scope and decisions
- Added shared `predict_van_t_hoff(T_K, A, dH_diss, dS_diss)` using the complete A*T numerator and stable logistic calculation. Parameters take Kelvin, MPa/K, J/mol and J/(mol K).
- Van 't Hoff fit uses the shared function. Removed the misleading G0_max alias; Params now contains A. Top-level enthalpy remains kJ/mol for display. Units describes display values; Parameter_units describes raw Params values.
- Added shared `predict_coupled(T_K, ln_A, Ea, ln_C, B, T0)` returning log(tau) using logaddexp. Both fixed/free T0 fits use it; eliminated inconsistent exponent clipping and overflow-prone summation.
- All fitting methods reject mismatched, non-vector, nonfinite, nonpositive measurements and temperatures at/below absolute zero by returning None. Require sufficient distinct temperatures: linear 2, VFT/Van Hoff 4, coupled fixed T0 5, coupled free T0 6.
- Two-point linear fits remain usable, but uncertainty is NaN and a Warning field explains the lack of uncertainty estimation.
- Nonlinear fits reject nonfinite optimized parameters/predictions.

## Verification
Command: `.venv/Scripts/python.exe -m pytest tests/test_kinetics.py -q`
Result: **54 passed**, 0.86 seconds.
Added invalid input matrix, explicit two-observation uncertainty test, Van Hoff equation/result consistency and synthetic recovery, large-exponent coupled stability, minimum observation guards, and fixed/free coupled prediction agreement. Strengthened the existing coupled test to require successful fitting and R2 > 0.99.

## Integration and follow-up
Parent agent owns GUI migration to the shared prediction functions and A naming.
These guards prevent underdetermined fits but do not establish identifiability or uncertainty for nonlinear parameters. Coupled free-T0 synthetic R2 exceeded 0.998 in this check; multiple local optima remain possible. Existing Tg-derived T0 clamp remains unchanged. Independent experimental validation and nonlinear uncertainty assessment belong in the following batch.

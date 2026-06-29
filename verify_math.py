from can_relax.core.kinetics import KineticsEngine
import numpy as np

engine = KineticsEngine()
temps_C = [130, 140, 150, 160]
taus = [10000, 3000, 1000, 350]

res = engine.fit_arrhenius(temps_C, taus)

slope = res['Params']['slope']
intercept = res['Params']['intercept']
x_plot = res['Plot']['x']

print('=== fit_arrhenius return values ===')
print(f"slope (d ln_tau / d (1/T)) = {slope:.4f}")
print(f"intercept = {intercept:.4f}")
print(f"Plot x (1/T): {x_plot}")
print(f"Plot x * 1000 (1000/T): {x_plot * 1000}")
print(f"Ea = {res['Ea']:.1f} kJ/mol")
print(f"R2 = {res['R2']:.6f}")

# Check Tv calculation
G_prime = 1.0  # MPa
G_Pa = G_prime * 1e6
tau_target = 1e12 / G_Pa
ln_tau_target = np.log(tau_target)
Tv_correct = (1.0 / ((ln_tau_target - intercept)/slope)) - 273.15
print(f"Tv (correct, 1/T domain) = {Tv_correct:.1f} C")

Tv_buggy = (1000.0 / ((ln_tau_target - intercept)/slope)) - 273.15
print(f"Tv (old buggy with 1000) = {Tv_buggy:.1f} C")

# Verify: with x_data = Plot['x'] which is 1/T (NOT 1000/T)
x_1000 = x_plot * 1000
slope_for_1000T = slope / 1000.0
y_pred_from_1000T = slope_for_1000T * x_1000 + intercept
y_pred_from_1T = slope * x_plot + intercept
print(f"y_pred from 1/T domain: {y_pred_from_1T}")
print(f"y_pred from 1000/T domain: {y_pred_from_1000T}")
print(f"Match? {np.allclose(y_pred_from_1T, y_pred_from_1000T)}")

# Now check the Tv marker x-coordinate on the 1000/T axis
Tv_x_on_1000T = ((ln_tau_target - intercept) / slope) * 1000.0
print(f"Tv star x-position on 1000/T axis: {Tv_x_on_1000T:.4f}")
Tv_from_marker = 1.0 / (Tv_x_on_1000T / 1000.0) - 273.15
print(f"Tv from marker x-position: {Tv_from_marker:.1f} C (should match {Tv_correct:.1f})")

# Compare tab check
print("\n=== Compare tab Arrhenius ===")
# In compare tab, slope is NOT divided by 1000 (after fix)
# The data is: inv_T = 1000.0 / (temps_arr + 273.15)
temps_arr = np.array(temps_C)
inv_T_compare = 1000.0 / (temps_arr + 273.15)
ln_tau_compare = np.log(np.array(taus))
print(f"Compare tab inv_T (1000/T): {inv_T_compare}")

# Fit line: y = slope * x + intercept, where x is 1000/T and slope is in 1/T domain
# This is WRONG unless we adjust. The compare tab uses slope directly.
# slope is in d(ln_tau)/d(1/T), so y = slope * (x/1000) + intercept
y_fit_wrong = slope * inv_T_compare + intercept
y_fit_correct = slope * (inv_T_compare / 1000.0) + intercept
print(f"y data: {ln_tau_compare}")
print(f"y fit (slope * 1000/T, WRONG): {y_fit_wrong}")
print(f"y fit (slope * (1000/T)/1000, CORRECT): {y_fit_correct}")

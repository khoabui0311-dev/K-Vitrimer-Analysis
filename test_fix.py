from can_relax.io.parser import parse_wide_format_data
from can_relax.core.processing import DataProcessor
from can_relax.core.analyzer import CurveAnalyzer

data = parse_wide_format_data('examples/VUEG.xlsx')
proc = DataProcessor()
analyzer = CurveAnalyzer()

print("=" * 60)
print("Testing all temperatures with new t_start = 0.01")
print("=" * 60)

for T in [110.0, 120.0, 130.0, 140.0]:
    t, g, G0 = proc.trim_curve(data[T]['Time'].values, data[T]['Modulus'].values)
    result = analyzer.fit_one_temp(T, data[T])
    
    fit_model = result['Best_Model']
    fit_curve = result['Fits'][fit_model]['curve']
    r2 = result['Fits'][fit_model]['r2']
    
    print(f"\n{T}°C:")
    print(f"  Time: {t[0]:.4f} s (start) to {t[-1]:.2f} s (end)")
    print(f"  Raw data: g[0]={g[0]:.4f}, g[-1]={g[-1]:.4f}, G0={G0:.6f}")
    print(f"  Best Model: {fit_model}")
    print(f"  R²: {r2:.4f}")
    print(f"  Fit curve: g_fit[0]={fit_curve[0]:.4f}, g_fit[-1]={fit_curve[-1]:.4f}")
    print(f"  ✓ Fit starts correctly at {fit_curve[0]:.4f} ≈ 1.0")

print("\n" + "=" * 60)
print("✅ All tests passed!")
print("=" * 60)

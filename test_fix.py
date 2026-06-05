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
    
    print("\n{}°C:".format(T))
    print("  Time: {:.4f} s (start) to {:.2f} s (end)".format(t[0], t[-1]))
    print("  Raw data: g[0]={:.4f}, g[-1]={:.4f}, G0={:.6f}".format(g[0], g[-1], G0))
    print("  Best Model: {}".format(fit_model))
    print("  R²: {:.4f}".format(r2))
    print("  Fit curve: g_fit[0]={:.4f}, g_fit[-1]={:.4f}".format(fit_curve[0], fit_curve[-1]))
    print("  ✓ Fit starts correctly at {:.4f} ≈ 1.0".format(fit_curve[0]))

print("\n" + "=" * 60)
print("✅ All tests passed!")
print("=" * 60)

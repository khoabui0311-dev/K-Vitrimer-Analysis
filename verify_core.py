from can_relax.io.parser import parse_wide_format_data
from can_relax.core.analyzer import CurveAnalyzer
import pandas as pd

def test_engine():
    print("🧪 STARTING CORE VERIFICATION...")
    
    # 1. Test Input
    file_path = "examples/toy_data.csv"
    print("📂 Loading {}...".format(file_path))
    
    curves = parse_wide_format_data(file_path)
    if not curves:
        print("❌ FAILED: Could not parse data.")
        return
    print("✅ Parser loaded {} curves.".format(len(curves)))

    # 2. Test Analysis
    print("⚙️  Running Physics Engine...")
    analyzer = CurveAnalyzer()
    
    results = []
    for temp, df in curves.items():
        res = analyzer.fit_one_temp(temp, df)
        if res:
            results.append(res)
            # Print quick stats
            best = res['Best_Model']
            r2 = res['Fits'][best]['r2']
            print("   -> {}°C | Best: {:10} | R2: {:.4f}".format(temp, best, r2))
    
    if len(results) == 0:
        print("❌ FAILED: Analyzer produced no results.")
        return

    # 3. Final Check
    avg_r2 = sum([r['Fits'][r['Best_Model']]['r2'] for r in results]) / len(results)
    if avg_r2 > 0.95:
        print("\n✅ SUCCESS! Engine is accurate (Avg R2: {:.4f})".format(avg_r2))
        print("🚀 Phase 1 is COMPLETE. You are ready for the GUI.")
    else:
        print("\n⚠️ WARNING: Low accuracy (Avg R2: {:.4f}). Check data.".format(avg_r2))

if __name__ == "__main__":
    test_engine()
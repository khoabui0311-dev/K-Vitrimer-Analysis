import pandas as pd
import re
import pathlib
import logging

# Set up a logger for this module
logger = logging.getLogger("Parser")

def parse_wide_format_data(file_path):
    """
    Robustly parses a wide-format file (CSV/XLSX) into a dictionary of DataFrames.
    Returns: { temperature_float: pd.DataFrame(columns=['Time', 'Modulus']) }
    """
    path_obj = pathlib.Path(file_path)
    df_raw = None

    # 1. Robust File Loading (Handles encoding errors & renamed files)
    try:
        # A) Try reading as CSV (UTF-8)
        if path_obj.suffix.lower() in ['.csv', '.txt']:
            try:
                # Try default UTF-8
                df_raw = pd.read_csv(file_path, sep=None, engine='python')
            except Exception:
                try:
                    # Try Latin-1 (Common for Excel CSVs)
                    df_raw = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
                except Exception:
                    # Try reading as Excel (in case it's an .xlsx named .csv)
                    try:
                        df_raw = pd.read_excel(file_path)
                    except:
                        pass
        
        # B) Try reading as Excel
        else:
            df_raw = pd.read_excel(file_path)

    except Exception as e:
        print(f"❌ [PARSER] Critical failure opening file: {e}")
        return {}

    if df_raw is None:
        print("❌ [PARSER] Could not read file. Checked UTF-8, Latin-1, and Excel formats.")
        return {}

    # 2. Identify Columns via Regex
    cols = list(df_raw.columns)
    temp_pat = re.compile(r"temp|deg|°c", re.IGNORECASE)
    time_pat = re.compile(r"time|sec|s\b", re.IGNORECASE)
    mod_pat  = re.compile(r"modulus|storage|g'|g_prime|mpa|pa|stress", re.IGNORECASE)

    col_type = {}
    for c in cols:
        s = str(c).lower()
        if temp_pat.search(s): col_type[c] = 'temp'
        elif mod_pat.search(s): col_type[c] = 'mod'
        elif time_pat.search(s): col_type[c] = 'time'
        else: col_type[c] = None

    curves = {}

    # 3. Group Columns into Triplets
    print(f"🔍 [PARSER] Scanning {len(cols)} columns...")
    for i, c in enumerate(cols):
        if col_type[c] != 'temp': continue
        
        # Wide search window to catch your specific file layout
        start_search = max(0, i - 5)
        end_search = min(len(cols), i + 5)
        
        time_col = None
        mod_col = None
        
        for idx in range(start_search, end_search):
            if idx == i: continue 
            # Find closest Time
            if col_type[cols[idx]] == 'time': 
                if time_col is None or abs(idx - i) < abs(cols.index(time_col) - i):
                    time_col = cols[idx]
            # Find closest Modulus
            if col_type[cols[idx]] == 'mod':
                if mod_col is None or abs(idx - i) < abs(cols.index(mod_col) - i):
                    mod_col = cols[idx]
        
        # 4. Extract Data
        if time_col and mod_col:
            try:
                sub_df = df_raw[[c, time_col, mod_col]].dropna().copy()
                sub_df.columns = ['Temp', 'Time', 'Modulus']
                
                val_str = str(sub_df['Temp'].iloc[0])
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", val_str)
                
                if nums:
                    temp_val = float(nums[0])
                    sub_df['Time'] = pd.to_numeric(sub_df['Time'], errors='coerce')
                    sub_df['Modulus'] = pd.to_numeric(sub_df['Modulus'], errors='coerce')
                    final_df = sub_df[['Time', 'Modulus']].dropna()
                    
                    if not final_df.empty:
                        curves[temp_val] = final_df
                        print(f"  ✅ Found curve: {temp_val}°C")
            except Exception:
                continue
    
    if not curves:
        print(f"❌ [PARSER] No curves found. Columns detected: {cols}")
        
    return curves
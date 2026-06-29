import pandas as pd
import re
import pathlib
import logging

# Set up a logger for this module
logger = logging.getLogger("Parser")

def _load_file_robustly(file_path):
    """Attempt to load a file robustly as CSV or Excel."""
    path_obj = pathlib.Path(file_path)
    df_raw = None

    try:
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
                    except Exception as e:
                        logger.debug("Failed reading as Excel fallback: %s", e)
        else:
            df_raw = pd.read_excel(file_path)

    except Exception as e:
        logger.error(f"[ERROR] [PARSER] Critical failure opening file: {e}")
    
    return df_raw

def _identify_columns(df_raw):
    """Identify column types using regex."""
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
        
    return col_type, cols

def _find_matching_columns(i, cols, col_type):
    """Find the best matching Time and Modulus columns for a given Temperature column."""
    next_temp_idx = len(cols)
    for idx in range(i + 1, len(cols)):
        if col_type[cols[idx]] == 'temp':
            next_temp_idx = idx
            break
    
    time_col = None
    mod_col = None
    
    # Search within the block
    for idx in range(i + 1, next_temp_idx):
        if col_type[cols[idx]] == 'time' and time_col is None:
            time_col = cols[idx]
        if col_type[cols[idx]] == 'mod' and mod_col is None:
            mod_col = cols[idx]
            
    # Fallback to sliding window search
    if time_col is None:
        best_dist = len(cols)
        for idx in range(max(0, i - 5), min(len(cols), i + 5)):
            if idx != i and col_type[cols[idx]] == 'time':
                dist = abs(idx - i)
                if dist < best_dist:
                    best_dist = dist
                    time_col = cols[idx]
                    
    if mod_col is None:
        best_dist = len(cols)
        for idx in range(max(0, i - 5), min(len(cols), i + 5)):
            if idx != i and col_type[cols[idx]] == 'mod':
                dist = abs(idx - i)
                if dist < best_dist:
                    best_dist = dist
                    mod_col = cols[idx]
                    
    return time_col, mod_col

def _extract_curves(df_raw, col_type, cols):
    """Extract valid Temp/Time/Modulus curves from the raw dataframe."""
    curves = {}
    logger.info(f"[PARSER] Scanning {len(cols)} columns...")
    
    for i, c in enumerate(cols):
        if col_type[c] != 'temp': continue
        
        time_col, mod_col = _find_matching_columns(i, cols, col_type)
        
        if time_col and mod_col:
            temp_val = None
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
                        logger.info(f"  [OK] Found curve: {temp_val}C")
            except Exception as e:
                logger.debug("Failed extracting curve for %s: %s", temp_val, e)
                continue
                
    if not curves:
        logger.warning(f"[PARSER] No curves found. Columns detected: {cols}")
        
    return curves

def parse_wide_format_data(file_path):
    """
    Robustly parses a wide-format file (CSV/XLSX) into a dictionary of DataFrames.
    Returns: { temperature_float: pd.DataFrame(columns=['Time', 'Modulus']) }
    """
    df_raw = _load_file_robustly(file_path)
    if df_raw is None:
        logger.error("[ERROR] [PARSER] Could not read file. Checked UTF-8, Latin-1, and Excel formats.")
        return {}

    col_type, cols = _identify_columns(df_raw)
    curves = _extract_curves(df_raw, col_type, cols)
    
    return curves
import sqlite3
import pandas as pd
import json
from datetime import datetime
import os
import time

class LabDatabase:
    def __init__(self, db_name="lab_notebook.db"):
        # Robust path finding
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.db_path = os.path.join(base_dir, db_name)
        self.connected = False
        self._init_db()

    def _init_db(self):
        """Attempts to connect and migrates schema if needed."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            c = conn.cursor()
            
            # 1. Create Table (The "Flat" Master Table)
            c.execute('''
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    filename TEXT,
                    temperature REAL,
                    best_model TEXT,
                    r2 REAL,
                    tau REAL,
                    quality REAL,
                    explanation TEXT,
                    bad_data INTEGER DEFAULT 0,
                    material_class TEXT DEFAULT 'Unknown',
                    material_type TEXT DEFAULT 'Unknown',
                    composition TEXT DEFAULT 'None',
                    chemistry TEXT DEFAULT 'Unknown',
                    verdict TEXT DEFAULT 'Pending'
                )
            ''')
            
            # 2. Smart Migration (Add columns if missing from older versions)
            current_cols = [row[1] for row in c.execute("PRAGMA table_info(experiments)")]
            
            new_cols = {
                'bad_data': 'INTEGER DEFAULT 0',
                'material_class': "TEXT DEFAULT 'Unknown'",
                'material_type': "TEXT DEFAULT 'Unknown'",
                'composition': "TEXT DEFAULT 'None'",
                'chemistry': "TEXT DEFAULT 'Unknown'",
                'verdict': "TEXT DEFAULT 'Pending'"
            }
            
            for col, dtype in new_cols.items():
                if col not in current_cols:
                    try:
                        c.execute(f"ALTER TABLE experiments ADD COLUMN {col} {dtype}")
                        print(f"  [DB] Migrated: Added column '{col}'")
                    except: pass
            
            conn.commit()
            conn.close()
            self.connected = True
        except Exception as e:
            print(f"⚠️ DB Init Error: {e}")
            self.connected = False

    def save_experiment(self, filename, result, meta=None):
        """Saves a single curve result with metadata."""
        if not self.connected: return False
        try:
            conn = sqlite3.connect(self.db_path, timeout=5)
            c = conn.cursor()
            
            temp = result['Temp']
            # Skip invalid results
            if not result.get('Valid', True): return False

            model = result.get('Best_Model', 'Unknown')
            
            # Extract Physics
            r2 = 0.0; tau = 0.0
            if model in result.get('Fits', {}):
                fit = result['Fits'][model]
                r2 = fit.get('r2', 0)
                popt = fit.get('popt')
                if popt is not None:
                    # Heuristic to find Tau index
                    if model == "Maxwell": tau = popt[1]
                    elif model == "Single_KWW": tau = popt[1]
                    elif model == "Dual_KWW": tau = popt[2]

            qual = result.get('Quality', 0)
            expl = result.get('Auto_Explanation', '')
            
            # Extract Metadata (Safe Defaults)
            m_class = meta.get('class', 'Unknown') if meta else 'Unknown'
            m_type = meta.get('type', 'Unknown') if meta else 'Unknown'
            m_comp = meta.get('composition', 'None') if meta else 'None'
            m_chem = meta.get('chemistry', 'Unknown') if meta else 'Unknown'
            verdict = meta.get('verdict', 'Pending') if meta else 'Pending'

            c.execute('''
                INSERT INTO experiments 
                (timestamp, filename, temperature, best_model, r2, tau, quality, explanation, 
                 bad_data, material_class, material_type, composition, chemistry, verdict)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M"), filename, temp, model, r2, tau, qual, expl, 
                  m_class, m_type, m_comp, m_chem, verdict))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Save Error: {e}")
            return False

    def fetch_history(self):
        """Returns the full database as a DataFrame."""
        if not self.connected: return pd.DataFrame()
        try:
            conn = sqlite3.connect(self.db_path, timeout=5)
            df = pd.read_sql_query("SELECT * FROM experiments ORDER BY id DESC", conn)
            conn.close()
            return df
        except: return pd.DataFrame()

    def update_verdict(self, ids, verdict):
        """Updates the Human Verdict for specific rows."""
        if not self.connected or not ids: return
        try:
            conn = sqlite3.connect(self.db_path, timeout=5)
            c = conn.cursor()
            id_list = ','.join(map(str, ids))
            c.execute(f"UPDATE experiments SET verdict = ? WHERE id IN ({id_list})", (verdict,))
            conn.commit()
            conn.close()
        except: pass

    def delete_experiments(self, ids):
        """Deletes rows by ID list."""
        if not self.connected or not ids: return
        try:
            conn = sqlite3.connect(self.db_path, timeout=5)
            c = conn.cursor()
            id_list = ','.join(map(str, ids))
            c.execute(f"DELETE FROM experiments WHERE id IN ({id_list})")
            conn.commit()
            conn.close()
        except: pass
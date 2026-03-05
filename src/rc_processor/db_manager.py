import sqlite3
import pandas as pd
import os
import time

class DatabaseManager:
    def convert_csv_to_sqlite(self, csv_file, db_file, table_name="beneficiaries", progress_callback=None):
        if progress_callback:
            progress_callback(f"[*] Starting CSV to SQLite conversion at {time.strftime('%H:%M:%S')}")
            
        try:
            if not os.path.exists(csv_file):
                return False, f"CSV file not found: {csv_file}"

            if progress_callback:
                progress_callback(f"[*] Reading CSV file: {csv_file}...")
            
            # Read CSV with pandas
            # Use 'dtype=str' to ensure all data (like ration card numbers) is treated as text to preserve leading zeros, etc.
            df = pd.read_csv(csv_file, dtype=str)
            
            if progress_callback:
                progress_callback(f"[*] Connecting to database: {db_file}...")
            
            conn = sqlite3.connect(db_file)
            
            if progress_callback:
                progress_callback(f"[*] Writing {len(df)} rows to table '{table_name}'...")
            
            # Write to SQLite
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            conn.close()
            
            if progress_callback:
                progress_callback(f"[SUCCESS] Database created at {db_file}")
                
            return True, f"Successfully created database: {db_file}"

        except Exception as e:
            if progress_callback:
                progress_callback(f"[ERROR] {e}")
            return False, str(e)

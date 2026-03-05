import sqlite3
import pandas as pd
import os
import random

class SearchManager:
    def __init__(self, db_path="rcdb.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        if not os.path.exists(self.db_path):
            return False, f"Database {self.db_path} not found."
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row # Access columns by name
            self.cursor = self.conn.cursor()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

    def search_ration_card(self, term):
        if not self.conn:
             # Try to connect if not connected
             success, msg = self.connect()
             if not success:
                 return None, 0

        try:
            # Check if table exists
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='beneficiaries'")
            if not self.cursor.fetchone():
                return None, 0

            # Get columns to map results dynamically
            try:
                self.cursor.execute("PRAGMA table_info(beneficiaries)")
                cols = [col[1] for col in self.cursor.fetchall()]
                rc_col = "Ration Card No." if "Ration Card No." in cols else cols[1] # fallback to 2nd col usually
                
                # 1. Get Count
                count_query = f"SELECT COUNT(*) FROM beneficiaries WHERE \"{rc_col}\" LIKE ?"
                self.cursor.execute(count_query, (term + '%',))
                count = self.cursor.fetchone()[0]

                if count == 0:
                    return None, 0

                # 2. Get Data (First Row)
                query = f"SELECT * FROM beneficiaries WHERE \"{rc_col}\" LIKE ? LIMIT 1"
                self.cursor.execute(query, (term + '%',))
                row = self.cursor.fetchone()
                
                if row:
                    data = dict(row)
                    # Always generate random mobile as per requirement
                    data['Mobile No'] = str(random.randint(6000000000, 9999999999))
                    return data, count
                return None, 0
            except sqlite3.OperationalError:
                 return None, 0
                 
        except Exception as e:
            print(f"Search Error: {e}")
            return None, 0

    def save_record(self, record_data, target_file="Benef_list.csv"):
        """
        Saves the given record_data dict to a CSV or Excel file.
        If file exists, appends to it.
        If file doesn't exist, creates it with standard columns.
        """
        try:
            # Map DB columns to our Standard Output Columns
            
            def get_val(keys):
                for k in keys:
                    if k in record_data: return record_data[k]
                return ""

            standard_row = {
                "Category": get_val(["Category"]),
                "Ration card Number": get_val(["Ration Card No.", "Rationcard No."]),
                "Name": get_val(["Name"]),
                "Father/Husband Name": get_val(["Father/Husband Name"]),
                "HOF Name": get_val(["HOF Name(As Per NFSA Provision)", "HOF Name"]),
                "Dealer Name": get_val(["Dealer_Name_Mapped", "Dealer Name"]),
                "Caste": get_val(["Deducted_Caste", "Caste"]),
                "Mobile No": get_val(["Mobile No"])
            }

            is_csv = target_file.lower().endswith('.csv')

            if os.path.exists(target_file):
                # Load existing file to preserve column order/structure
                if is_csv:
                    existing_df = pd.read_csv(target_file, dtype=str)
                else:
                    existing_df = pd.read_excel(target_file, dtype=str)
                
                cols = list(existing_df.columns)
                
                # Create new row dict matching existing columns
                new_row = {}
                for col in cols:
                    # heuristic mapping
                    if col in standard_row:
                        new_row[col] = standard_row[col]
                    elif col == "Ration Card No.":
                         new_row[col] = standard_row["Ration card Number"]
                    elif "HOF" in col:
                         new_row[col] = standard_row["HOF Name"]
                    elif "Dealer" in col:
                         new_row[col] = standard_row["Dealer Name"]
                    elif "Mobile" in col:
                         new_row[col] = standard_row["Mobile No"]
                    else:
                        new_row[col] = "" 
                
                new_df = pd.DataFrame([new_row])
                # concat
                updated_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                if is_csv:
                    updated_df.to_csv(target_file, index=False, encoding='utf-8-sig')
                else:
                    updated_df.to_excel(target_file, index=False)
            else:
                # Create new file
                cols = ["Category", "Ration card Number", "Name", "Father/Husband Name", "HOF Name", "Dealer Name", "Caste", "Mobile No"]
                # Only include these columns
                final_row = {k: standard_row[k] for k in cols}
                new_df = pd.DataFrame([final_row], columns=cols)
                
                if is_csv:
                    new_df.to_csv(target_file, index=False, encoding='utf-8-sig')
                else:
                    new_df.to_excel(target_file, index=False)

            return True, f"Saved to {target_file}"

        except Exception as e:
            return False, str(e)

    def close(self):
        if self.conn:
            self.conn.close()

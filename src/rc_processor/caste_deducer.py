import pandas as pd
from rapidfuzz import process
from rapidfuzz.distance import JaroWinkler
import jellyfish
import os
import time

class DataEnricher:
    def __init__(self):
        self.default_caste = "GEN"
        self.match_not_found_text = "NOT FOUND"
        self.fuzzy_threshold_high = 0.90
        self.fuzzy_threshold_low = 0.85

    def _load_file(self, path, progress_callback=None):
        if progress_callback:
            progress_callback(f"[*] Loading: {path}...")
        try:
            if path.lower().endswith('.csv'):
                return pd.read_csv(path, dtype=str)
            else:
                return pd.read_excel(path, dtype=str)
        except Exception as e:
            raise Exception(f"Failed to load {path}: {e}")

    def _deduce_caste(self, df_data, caste_config, progress_callback):
        db_path = caste_config['db_path']
        name_col = caste_config['name_col']
        
        if progress_callback:
            progress_callback(f"[*] Starting Caste Deduction using {db_path}...")

        # Load DB
        df_db = self._load_file(db_path, progress_callback)
        
        # Standardize DB column names
        db_lastname_col = "LAST NAME"
        db_caste_col = "CASTE"
        
        # Check if required columns exist in DB
        if db_lastname_col not in df_db.columns or db_caste_col not in df_db.columns:
             # Basic check, maybe case insensitive later
             raise Exception(f"Database must have '{db_lastname_col}' and '{db_caste_col}' columns.")

        # Pre-process Database
        df_db[db_lastname_col] = df_db[db_lastname_col].astype(str).str.upper().str.strip()
        df_db[db_caste_col] = df_db[db_caste_col].astype(str).str.upper().str.strip()
        
        # Create fast lookup structures
        db_map = dict(zip(df_db[db_lastname_col], df_db[db_caste_col]))
        db_ref_list = sorted(df_db[db_lastname_col].tolist(), key=len, reverse=True)
        
        # Process Unique Last Names
        if progress_callback:
            progress_callback("[*] Extracting unique last names from data...")
        
        # Extract only the LAST word from the name column
        temp_col = 'TEMP_LAST_NAME'
        df_data[temp_col] = df_data[name_col].apply(
            lambda x: str(x).strip().upper().split()[-1] if pd.notnull(x) and str(x).strip() else "NAN"
        )
        unique_names = df_data[temp_col].unique()
        
        match_cache = {} # Stores { input_name: (caste, matched_ref_name) }
        
        total_unique = len(unique_names)
        if progress_callback:
            progress_callback(f"[*] Matching {total_unique} unique names...")
        
        for i, last_name in enumerate(unique_names):
            # Update progress every 10% or at least every 100 items
            if progress_callback and (i % 100 == 0 or i == total_unique - 1):
                    progress_callback(f"Matching Castes... ({i+1}/{total_unique})")

            # Handle invalid names
            if not last_name or last_name == 'NAN' or not isinstance(last_name, str):
                match_cache[last_name] = (self.default_caste, self.match_not_found_text)
                continue
                
            # PASS 1: Exact Match (Highest Accuracy)
            if last_name in db_map:
                match_cache[last_name] = (db_map[last_name], last_name)
                continue
                
            # PASS 2: High Confidence Fuzzy Match (OCR Error Correction)
            match = process.extractOne(last_name, db_ref_list, scorer=JaroWinkler.similarity)
            if match and match[1] >= self.fuzzy_threshold_high:
                ref_name = match[0]
                match_cache[last_name] = (db_map[ref_name], ref_name)
                continue
                
            # PASS 3: Phonetic Matching (Sound-alike Correction)
            last_name_phonetic = jellyfish.nysiis(str(last_name))
            found_phonetic = False
            for ref_name in db_ref_list:
                if not isinstance(ref_name, str): continue
                if jellyfish.nysiis(ref_name) == last_name_phonetic:
                    match_cache[last_name] = (db_map[ref_name], ref_name)
                    found_phonetic = True
                    break
            if found_phonetic:
                continue
                
            # PASS 4: Lower Confidence Fuzzy Match
            if match and match[1] >= self.fuzzy_threshold_low:
                ref_name = match[0]
                match_cache[last_name] = (db_map[ref_name], ref_name)
                continue

            # PASS 5: Fallback
            match_cache[last_name] = (self.default_caste, self.match_not_found_text)

        # Map results back
        if progress_callback:
            progress_callback("[*] Finalizing caste mapping...")
        
        df_data['Deducted_Caste'] = df_data[temp_col].map(lambda x: match_cache[x][0])
        df_data['Matched_Reference_Name'] = df_data[temp_col].map(lambda x: match_cache[x][1])
        
        # Clean up temp column
        df_data.drop(columns=[temp_col], inplace=True)
        
        return df_data

    def _map_dealers(self, df_data, dealer_config, progress_callback):
        db_path = dealer_config['db_path']
        data_code_col = dealer_config['data_code_col']
        db_code_col = dealer_config['db_code_col']
        db_name_col = dealer_config['db_name_col']

        if progress_callback:
            progress_callback(f"[*] Starting Dealer Mapping using {db_path}...")

        # Load DB
        df_db = self._load_file(db_path, progress_callback)
        
        # Validate columns
        if db_code_col not in df_db.columns:
            raise Exception(f"Column '{db_code_col}' not found in Dealer DB.")
        if db_name_col not in df_db.columns:
             raise Exception(f"Column '{db_name_col}' not found in Dealer DB.")
        
        if data_code_col not in df_data.columns:
             raise Exception(f"Column '{data_code_col}' not found in Input Data.")

        if progress_callback:
            progress_callback("[*] Mapping Dealers...")

        # Create lookup dict
        # Ensure codes are strings for matching and strip whitespace
        df_db[db_code_col] = df_db[db_code_col].astype(str).str.strip()
        dealer_map = dict(zip(df_db[db_code_col], df_db[db_name_col]))
        
        # Normalize data column for matching
        temp_code_col = 'TEMP_DEALER_CODE'
        df_data[temp_code_col] = df_data[data_code_col].astype(str).str.strip()
        
        # Map
        df_data['Dealer_Name_Mapped'] = df_data[temp_code_col].map(dealer_map).fillna("Unknown Dealer")
        
        df_data.drop(columns=[temp_code_col], inplace=True)
        
        return df_data

    def enrich_data(self, input_path, output_path, caste_config=None, dealer_config=None, progress_callback=None):
        """
        Orchestrates the data enrichment process.
        """
        if progress_callback:
            progress_callback(f"[*] Starting Enrichment Process at {time.strftime('%H:%M:%S')}")

        try:
            # 1. Load Main Data
            if progress_callback:
                progress_callback(f"[*] Loading Main Data: {input_path}...")
            
            if input_path.lower().endswith('.csv'):
                df_data = pd.read_csv(input_path, dtype=str)
            else:
                df_data = pd.read_excel(input_path, dtype=str)

            # 2. Caste Deduction
            if caste_config:
                try:
                    df_data = self._deduce_caste(df_data, caste_config, progress_callback)
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"[WARNING] Caste Deduction Failed: {e}")
                    # Decide whether to fail completely or continue. Let's fail for now as user expects it.
                    return False, f"Caste Deduction Error: {e}"

            # 3. Dealer Mapping
            if dealer_config:
                try:
                    df_data = self._map_dealers(df_data, dealer_config, progress_callback)
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"[WARNING] Dealer Mapping Failed: {e}")
                    return False, f"Dealer Mapping Error: {e}"

            # 4. Save Output
            if progress_callback:
                progress_callback(f"[*] Writing results to {output_path}...")
            
            if output_path.lower().endswith('.csv'):
                df_data.to_csv(output_path, index=False, encoding='utf-8-sig')
            else:
                df_data.to_excel(output_path, index=False)
            
            if progress_callback:
                progress_callback(f"[SUCCESS] Completed. Saved to {output_path}")
                
            return True, f"Successfully saved to {output_path}"

        except Exception as e:
            if progress_callback:
                progress_callback(f"[ERROR] {e}")
            return False, str(e)

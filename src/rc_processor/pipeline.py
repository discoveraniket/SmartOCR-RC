import os
import shutil
import time
from .downloader import BeneficiaryDownloader
from .converter import BeneficiaryConverter
from .caste_deducer import DataEnricher
from .db_manager import DatabaseManager

class PipelineManager:
    def __init__(self):
        self.downloader = BeneficiaryDownloader()
        self.converter = BeneficiaryConverter()
        self.enricher = DataEnricher()
        self.db_manager = DatabaseManager()

    def run_pipeline(self, config, progress_callback=None):
        """
        config = {
            'dealer_list_file': str,
            'dealer_code_col': str,
            'dealer_name_col': str,
            'caste_db_file': str,
            'session_id': str,
            'output_dir': str,
            'final_db_name': str
        }
        """
        try:
            base_dir = config['output_dir']
            downloads_dir = os.path.join(base_dir, '1_downloads')
            raw_csv_path = os.path.join(base_dir, '2_raw_combined.csv')
            enriched_csv_path = os.path.join(base_dir, '3_enriched.csv')
            final_db_path = os.path.join(base_dir, config.get('final_db_name', 'final_data.db'))

            # 1. Download
            if progress_callback:
                progress_callback("=== STEP 1: DOWNLOADING DATA ===")
            
            # We don't need to return results list here, just know it finished
            self.downloader.download_from_csv(
                csv_file=config['dealer_list_file'],
                output_dir=downloads_dir,
                session_id=config['session_id'],
                dealer_column=config['dealer_code_col'],
                progress_callback=progress_callback
            )

            # 2. Convert
            if progress_callback:
                progress_callback("\n=== STEP 2: CONVERTING HTML TO CSV ===")
            
            success, msg = self.converter.convert_directory(
                input_dir=downloads_dir,
                output_file=raw_csv_path,
                progress_callback=progress_callback
            )
            if not success:
                raise Exception(f"Conversion failed: {msg}")

            # 3. Enrich (Caste + Dealer)
            if progress_callback:
                progress_callback("\n=== STEP 3: ENRICHING DATA ===")

            # Setup enrichment configs
            # We assume the converted CSV has a column "Name" for beneficiaries
            # and "Source File" for the dealer code (from file name)
            
            caste_config = {
                'db_path': config['caste_db_file'],
                'name_col': 'Name' # Default assumption, strict for now
            }
            
            dealer_config = {
                'db_path': config['dealer_list_file'],
                'data_code_col': 'Source File', # Created by converter
                'db_code_col': config['dealer_code_col'],
                'db_name_col': config['dealer_name_col']
            }

            success, msg = self.enricher.enrich_data(
                input_path=raw_csv_path,
                output_path=enriched_csv_path,
                caste_config=caste_config,
                dealer_config=dealer_config,
                progress_callback=progress_callback
            )
            if not success:
                # Fallback: Maybe "Name" column is named differently?
                # We could try to read headers and guess, but for now fail fast.
                raise Exception(f"Enrichment failed: {msg}")

            # 4. Database
            if progress_callback:
                progress_callback("\n=== STEP 4: GENERATING DATABASE ===")
            
            success, msg = self.db_manager.convert_csv_to_sqlite(
                csv_file=enriched_csv_path,
                db_file=final_db_path,
                table_name='beneficiaries',
                progress_callback=progress_callback
            )
            if not success:
                raise Exception(f"Database creation failed: {msg}")

            if progress_callback:
                progress_callback("\n[ALL STEPS COMPLETED SUCCESSFULLY]")
                progress_callback(f"Final Database: {final_db_path}")

            return True, final_db_path

        except Exception as e:
            if progress_callback:
                progress_callback(f"\n[CRITICAL ERROR] Pipeline stopped: {e}")
            return False, str(e)

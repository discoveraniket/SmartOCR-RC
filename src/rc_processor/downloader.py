import requests
import urllib3
import ssl
import os
import csv
import time
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

# Disable warnings for insecure requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SSLAdapter(HTTPAdapter):
    """
    Custom SSL adapter to allow 'unsafe legacy renegotiation' 
    often required by older government servers.
    """
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        # OP_LEGACY_SERVER_CONNECT = 0x4
        context.options |= 0x4 
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

class BeneficiaryDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.mount('https://', SSLAdapter())
        self.url_session = "ouypanjk0ygg3tkihymg0q35" # TODO: Make this configurable or dynamic?

    def download_excel(self, url, output_filename):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # print(f"Connecting to: {url}")
        try:
            # Step 1: Get the initial page to extract hidden fields (__VIEWSTATE, etc.)
            response = self.session.get(url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()
        except Exception as e:
            return False, f"Error fetching page: {e}"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract all hidden input fields required for the ASP.NET postback
        data = {tag.get('name'): tag.get('value') for tag in soup.find_all('input', type='hidden')}

        # Target the Excel download button
        img_button = soup.find('input', id='ctl00_ContentPlaceHolder1_ImageButton1')
        target_name = img_button.get('name') if img_button else 'ctl00$ContentPlaceHolder1$ImageButton1'

        # Simulate clicking the ImageButton (requires .x and .y coordinates)
        data[f'{target_name}.x'] = '20'
        data[f'{target_name}.y'] = '20'

        try:
            # Step 2: POST the data to trigger the Excel generation
            post_response = self.session.post(url, data=data, headers=headers, verify=False, timeout=60)
            post_response.raise_for_status()
        except Exception as e:
            return False, f"Error during download: {e}"

        content_type = post_response.headers.get('Content-Type', '').lower()
        
        if 'excel' in content_type or 'spreadsheetml' in content_type or 'octet-stream' in content_type:
            with open(output_filename, 'wb') as f:
                f.write(post_response.content)
            return True, f"Saved to: {output_filename} ({len(post_response.content)} bytes)"
        else:
            msg = f"Failed: Received unexpected content type: {content_type}"
            if 'text/html' in content_type:
                msg += " (Server returned HTML, session might be expired)"
            return False, msg

    def download_from_csv(self, csv_file, output_dir, session_id=None, dealer_column=None, progress_callback=None):
        if session_id:
            self.url_session = session_id

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        success_records = []
        results = []

        if not os.path.exists(csv_file):
            if progress_callback:
                progress_callback(f"Error: {csv_file} not found.")
            return results

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            # Use DictReader to handle headers automatically
            reader = csv.DictReader(f)
            
            # Verify the column exists
            if dealer_column and dealer_column not in reader.fieldnames:
                msg = f"Error: Column '{dealer_column}' not found in CSV. Available columns: {', '.join(reader.fieldnames or [])}"
                if progress_callback:
                    progress_callback(msg)
                return results

            # If no column specified, try the first one
            target_col = dealer_column if dealer_column else (reader.fieldnames[0] if reader.fieldnames else None)
            
            if not target_col:
                if progress_callback:
                    progress_callback("Error: CSV appears to be empty or has no headers.")
                return results

            rows = list(reader)
            total = len(rows)
            
            for i, row in enumerate(rows):
                url_dealer = row.get(target_col, '').strip()
                if not url_dealer:
                    continue
                
                target_url = f"https://wbpds.wb.gov.in/(S({self.url_session}))/RCCount_Beneficiary.aspx?FPSCode={url_dealer},2388"
                output_file = os.path.join(output_dir, f"{url_dealer}.xls.html")
                
                if progress_callback:
                    progress_callback(f"Processing dealer: {url_dealer} ({i+1}/{total})")
                
                success, msg = self.download_excel(target_url, output_file)
                
                if success:
                    success_records.append([url_dealer, "Success"])
                    results.append({"dealer": url_dealer, "status": "Success", "file": output_file})
                else:
                    results.append({"dealer": url_dealer, "status": "Failed", "error": msg})
                
                if progress_callback:
                    progress_callback(msg)
                
                time.sleep(0.4)

        # Create success summary CSV in the output directory
        summary_file = os.path.join(output_dir, "download_summary.csv")
        with open(summary_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Dealer Number", "Status"])
            writer.writerows(success_records)
        
        if progress_callback:
            progress_callback(f"Batch processing complete. Summary saved to {summary_file}")
            
        return results

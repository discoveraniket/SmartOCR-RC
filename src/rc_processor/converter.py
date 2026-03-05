import os
import csv
from bs4 import BeautifulSoup

class BeneficiaryConverter:
    def extract_data_from_html(self, html_file_path):
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')

            table = soup.find('table', class_='mGrid')
            if not table:
                return None, [], f"No table with class 'mGrid' found in {html_file_path}"

            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            if not headers:
                first_tr = table.find('tr')
                if first_tr:
                    headers = [td.get_text(strip=True) for td in first_tr.find_all(['td', 'th'])]

            rows = []
            for tr in table.find_all('tr'):
                if tr.find('th'):
                    continue
                cells = [td.get_text(strip=True) for td in tr.find_all('td')]
                if cells:
                    rows.append(cells)
            
            return headers, rows, "Success"
        except Exception as e:
            return None, [], str(e)

    def convert_directory(self, input_dir, output_file, progress_callback=None):
        if not os.path.exists(input_dir):
            if progress_callback:
                progress_callback(f"Directory {input_dir} does not exist.")
            return False, f"Directory {input_dir} does not exist."

        headers_written = False
        files = [f for f in os.listdir(input_dir) if f.endswith('.html')]
        total_files = len(files)
        
        if total_files == 0:
            if progress_callback:
                progress_callback("No .html files found in the directory.")
            return False, "No .html files found."

        try:
            with open(output_file, 'w', encoding='utf-8', newline='') as f_out:
                writer = csv.writer(f_out)
                
                for i, filename in enumerate(files):
                    html_path = os.path.join(input_dir, filename)
                    if progress_callback:
                        progress_callback(f"Processing {filename} ({i+1}/{total_files})...")
                    
                    headers, rows, msg = self.extract_data_from_html(html_path)
                    
                    if not headers and not rows:
                        if progress_callback:
                            progress_callback(f"Skipping {filename}: {msg}")
                        continue

                    # Add Source File column
                    source_name = filename.rsplit('.html', 1)[0]
                    if source_name.endswith('.xls'):
                        source_name = source_name.rsplit('.xls', 1)[0]
                    
                    if not headers_written:
                        writer.writerow(['Source File'] + headers)
                        headers_written = True
                    
                    for row in rows:
                        writer.writerow([source_name] + row)
            
            if progress_callback:
                progress_callback(f"Successfully created {output_file}")
            return True, f"Successfully created {output_file}"

        except Exception as e:
            if progress_callback:
                progress_callback(f"Error creating CSV: {e}")
            return False, str(e)

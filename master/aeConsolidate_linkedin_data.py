import json
import os
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialize colorama
init()

def print_status(message: str, color: str = Fore.WHITE):
    print(f"{color}{message}{Style.RESET_ALL}")

def process_json_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        processed_entries = []
        for entry in data:
            # Skip if no LinkedIn URL
            if 'linkedIn' not in entry['metadata']:
                continue
                
            # Extract only required fields and handle potential missing values
            processed_entry = {
                'Full Name': entry['metadata'].get('fullName', ''),
                'Company Name': entry['metadata'].get('companyName', ''),
                'Position': entry['metadata'].get('positionName', ''),
                'LinkedIn URL': entry['metadata'].get('linkedIn', '')
            }
            processed_entries.append(processed_entry)
            
        return processed_entries
        
    except Exception as e:
        print_status(f"Error processing {filepath}: {str(e)}", Fore.RED)
        return []

def consolidate_linkedin_data():
    try:
        # Get all JSON files from googleData directory
        json_files = [f for f in os.listdir('googleData') if f.endswith('.json')]
        
        if not json_files:
            print_status("No JSON files found in googleData directory!", Fore.RED)
            return
            
        print_status(f"\nProcessing {len(json_files)} JSON files...", Fore.CYAN)
        
        all_entries = []
        total_entries = 0
        entries_with_linkedin = 0
        
        # Process each file with progress bar
        for filename in tqdm(json_files, desc="Processing files", unit="file"):
            filepath = os.path.join('googleData', filename)
            processed_entries = process_json_file(filepath)
            
            total_entries += len(processed_entries)
            entries_with_linkedin += len(processed_entries)
            all_entries.extend(processed_entries)
            
        # Save consolidated data to JSON
        json_output = 'consolidated_linkedin_data.json'
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(all_entries, f, indent=2, ensure_ascii=False)
            
        print_status(f"\nProcessing completed!", Fore.GREEN)
        print_status(f"JSON data saved to: {json_output}", Fore.GREEN)
        print_status(f"Total entries processed: {total_entries}", Fore.WHITE)
        print_status(f"Entries with LinkedIn URLs: {entries_with_linkedin}", Fore.GREEN)
        
    except Exception as e:
        print_status(f"An error occurred: {str(e)}", Fore.RED)

if __name__ == "__main__":
    consolidate_linkedin_data() 
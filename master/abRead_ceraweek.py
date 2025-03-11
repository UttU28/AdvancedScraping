import pandas as pd
import json
import os
from tqdm import tqdm
from colorama import init, Fore, Style
from dotenv import load_dotenv
from googeSearchWadiAPI import (
    search_linkedin_profile, 
    extract_essential_data,
    GoogleCustomSearch,
    create_linkedin_search_query
)

# Initialize colorama and load environment variables
init()
load_dotenv()

def print_status(message: str, color: str = Fore.WHITE):
    print(f"{color}{message}{Style.RESET_ALL}")

def load_existing_results(filepath: str) -> list:
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_results(results: list, filepath: str):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def process_file(unprocessed_file: str, status_filepath: str) -> bool:
    try:
        # Read the CSV file
        filepath = os.path.join('ceraWeek_data', unprocessed_file)
        df = pd.read_csv(filepath, encoding='utf-8')
        
        print_status(f"\nProcessing file: {unprocessed_file}", Fore.CYAN)
        print_status(f"Total entries: {len(df)}", Fore.CYAN)
        
        # Get Google API credentials from environment variables
        API_KEY = os.getenv('GOOGLE_API_KEY')
        SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not API_KEY or not SEARCH_ENGINE_ID:
            print_status("Error: Missing API credentials in environment variables", Fore.RED)
            return False

        # Create output filename and directory
        os.makedirs('googleData', exist_ok=True)
        output_filename = f"linkedin_search_{os.path.splitext(unprocessed_file)[0]}.json"
        output_filepath = os.path.join('googleData', output_filename)
        
        # Load existing results if any
        all_results = load_existing_results(output_filepath)
        processed_names = {result['metadata']['fullName'] for result in all_results}
        
        print_status(f"Found {len(processed_names)} previously processed entries", Fore.CYAN)
        
        # Process each entry with progress bar
        for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing entries"):
            try:
                fullname = row['Full Name']
                company = row['Company']
                position = row['Position']
                
                # Skip if already processed
                if fullname in processed_names:
                    continue
                
                # Search LinkedIn profile
                search_client = GoogleCustomSearch(API_KEY, SEARCH_ENGINE_ID)
                query = create_linkedin_search_query(fullname, company)
                
                results = search_client.search(query, num=7)
                if results:
                    essential_data = extract_essential_data(results)
                    result_entry = {
                        'metadata': {
                            'fullName': fullname,
                            'companyName': company,
                            'positionName': position
                        },
                        'search_results': essential_data
                    }
                    all_results.append(result_entry)
                    processed_names.add(fullname)
                    
                    # Save after each successful search
                    save_results(all_results, output_filepath)
                else:
                    print_status(f"No results found for {fullname}", Fore.YELLOW)
                
            except Exception as e:
                print_status(f"Error processing {fullname}: {str(e)}", Fore.RED)
                continue

        print_status(f"\nResults saved to '{output_filepath}'", Fore.GREEN)
        print_status(f"Total entries processed: {len(all_results)}", Fore.GREEN)

        # Update the processing status
        with open(status_filepath, 'r', encoding='utf-8') as f:
            processing_status = json.load(f)
        processing_status[unprocessed_file]['processed'] = True
        with open(status_filepath, 'w', encoding='utf-8') as f:
            json.dump(processing_status, f, indent=4)
        
        print_status(f"\nFile {unprocessed_file} marked as processed!", Fore.GREEN)
        return True

    except Exception as e:
        print_status(f"Error processing file {unprocessed_file}: {str(e)}", Fore.RED)
        return False

def read_ceraweek_data():
    try:
        # Read the processing status file
        status_filepath = os.path.join('ceraWeek_data', 'processing_status.json')
        if not os.path.exists(status_filepath):
            print_status("Error: processing_status.json not found!", Fore.RED)
            return

        while True:
            # Read current status
            with open(status_filepath, 'r', encoding='utf-8') as f:
                processing_status = json.load(f)

            # Find the first unprocessed file
            unprocessed_file = None
            for filename, status in processing_status.items():
                if not status['processed']:
                    unprocessed_file = filename
                    break

            if not unprocessed_file:
                print_status("\nAll files have been processed!", Fore.GREEN)
                break

            # Process the file
            success = process_file(unprocessed_file, status_filepath)
            if not success:
                print_status("\nError occurred. Stopping processing.", Fore.RED)
                break

            # Add a small delay between files
            import time
            time.sleep(2)

    except FileNotFoundError:
        print_status("Error: File not found!", Fore.RED)
    except Exception as e:
        print_status(f"An error occurred: {str(e)}", Fore.RED)

if __name__ == "__main__":
    read_ceraweek_data() 
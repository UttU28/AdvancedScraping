import json
from colorama import init, Fore, Style
from tqdm import tqdm
from googeSearchWadiAPI import GoogleCustomSearch
import time
import os
from dotenv import load_dotenv

# Initialize colorama and load environment variables
init()
load_dotenv()

def print_status(message: str, color: str = Fore.WHITE):
    print(f"{color}{message}{Style.RESET_ALL}")

def get_company_domain(company_name, search_client):
    try:
        query = f'"{company_name}" official company website'
        results = search_client.search(query, num=5)
        
        if results and 'items' in results:
            for result in results['items']:
                url = result['link']
                if 'wikipedia.org' in url.lower() or 'linkedin.com' in url.lower():
                    continue
                return url
        return ""
        
    except Exception:
        return ""

def save_companies(companies, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)

def extract_companies():
    try:
        # Get Google API credentials from environment variables
        API_KEY = os.getenv('GOOGLE_API_KEY')
        SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not API_KEY or not SEARCH_ENGINE_ID:
            print_status("Error: Missing API credentials in environment variables", Fore.RED)
            return
            
        search_client = GoogleCustomSearch(API_KEY, SEARCH_ENGINE_ID)
        
        output_file = 'company_domains.json'
        
        # Load existing data if file exists
        companies = {}
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                companies = json.load(f)
        
        # Read the consolidated JSON file
        with open('consolidated_linkedin_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not data:
            print_status("No data found in consolidated JSON file!", Fore.RED)
            return
            
        # Extract unique company names that haven't been processed yet or don't have a URL
        new_companies = {}
        skipped_companies = 0
        for entry in data:
            company_name = entry['Company Name']
            if company_name not in companies or not companies[company_name]:
                new_companies[company_name] = ""
            else:
                skipped_companies += 1
        
        # Process new companies with progress bar
        total_new = len(new_companies)
        found_domains = 0
        
        if total_new > 0:
            print_status(f"\nProcessing {total_new} new companies...", Fore.CYAN)
            print_status(f"Skipping {skipped_companies} companies that already have URLs", Fore.YELLOW)
            
            for company_name in tqdm(new_companies.keys(), desc="Finding domains"):
                domain_url = get_company_domain(company_name, search_client)
                companies[company_name] = domain_url
                if domain_url:
                    found_domains += 1
                # Save after each successful lookup
                save_companies(companies, output_file)
                time.sleep(0.3)  # Add delay to avoid rate limiting
                
            # Print final status
            print_status(f"\nProcessing completed!", Fore.GREEN)
            print_status(f"New companies processed: {total_new}", Fore.WHITE)
            print_status(f"New domains found: {found_domains}", Fore.GREEN)
            print_status(f"New domains not found: {total_new - found_domains}", Fore.YELLOW)
            print_status(f"Success rate: {(found_domains/total_new)*100:.1f}%", Fore.CYAN)
            print_status(f"Total companies in database: {len(companies)}", Fore.CYAN)
            print_status(f"Results saved to: {output_file}", Fore.GREEN)
        else:
            print_status("\nNo new companies to process!", Fore.YELLOW)
            print_status(f"Total companies in database: {len(companies)}", Fore.CYAN)
            print_status(f"All companies already have URLs", Fore.GREEN)
        
    except FileNotFoundError:
        print_status("Error: consolidated_linkedin_data.json not found!", Fore.RED)
    except json.JSONDecodeError:
        print_status("Error: Invalid JSON file!", Fore.RED)
    except Exception as e:
        print_status(f"An error occurred: {str(e)}", Fore.RED)

if __name__ == "__main__":
    extract_companies() 
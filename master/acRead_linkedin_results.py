import json
import re
from colorama import init, Fore, Style
from tqdm import tqdm
import openai
from prompts import SYSTEM_PROMPT, USER_PROMPT
from dotenv import load_dotenv
import os

# Initialize colorama and load environment variables
init()
load_dotenv()

# Set OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

if not openai.api_key:
    raise ValueError("OpenAI API key not found in environment variables")

def call_openai_gpt(system_prompt, user_prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        
        # Save the response to a file
        os.makedirs('openai_responses', exist_ok=True)
        output_file = 'openai_responses/response.txt'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"System Prompt:\n{system_prompt}\n\n")
            f.write(f"User Prompt:\n{user_prompt}\n\n")
            f.write(f"Response:\n{response['choices'][0]['message']['content']}")
            
        return response["choices"][0]["message"]["content"]
        
    except Exception as e:
        print_status(f"Error making OpenAI request: {str(e)}", Fore.RED)
        return None

def print_status(message: str, color: str = Fore.WHITE):
    print(f"{color}{message}{Style.RESET_ALL}")

def extract_linkedin_url(text):
    # Pattern to match URLs between quotes after "linkedin.com/in/"
    pattern = r'https://(?:www\.)?linkedin\.com/in/[^"\s]+'
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return None

def process_entry(entry):
    # Add viewed flag if not present
    if 'viewed' not in entry['metadata']:
        entry['metadata']['viewed'] = True
        
        # Prepare the user prompt with the entry
        user_prompt = USER_PROMPT.replace("{json_input}", json.dumps(entry, indent=2))
        
        # Call OpenAI API
        response = call_openai_gpt(SYSTEM_PROMPT, user_prompt)
        
        if response:
            # Extract just the LinkedIn URL using regex
            linkedin_url = extract_linkedin_url(response)
            
            if linkedin_url:
                # Add LinkedIn URL to the metadata
                entry['metadata']['linkedIn'] = linkedin_url
                return entry, True
        
        return entry, False
    return entry, False

def read_linkedin_results():
    try:
        filepath = 'googleData/linkedin_search_ceraWeek_page_3.json'
        # filepath = 'googleData/merged_results.json'
        print_status(f"\nProcessing LinkedIn results from: {filepath}", Fore.CYAN)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        total_entries = len(data)
        found_count = 0
        processed_count = 0
        
        if data:
            # Process each entry with tqdm progress bar
            for i, entry in enumerate(tqdm(data, desc="Processing entries", unit="entry")):
                updated_entry, found = process_entry(entry)
                data[i] = updated_entry
                if found:
                    found_count += 1
                processed_count += 1
                
                # Save after each entry is processed
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Add a small delay between API calls to avoid rate limiting
                import time
                time.sleep(1)
            
            # Print final statistics
            print_status("\nProcessing completed!", Fore.GREEN)
            print_status(f"Total entries in file: {total_entries}", Fore.WHITE)
            print_status(f"Entries processed: {processed_count}", Fore.WHITE)
            print_status(f"LinkedIn URLs found: {found_count}", Fore.GREEN)
            print_status(f"LinkedIn URLs not found: {processed_count - found_count}", Fore.YELLOW)
            print_status(f"Success rate: {(found_count/processed_count)*100:.1f}%", Fore.CYAN)
        else:
            print_status("No entries found in the file.", Fore.YELLOW)
            
    except FileNotFoundError:
        print_status(f"Error: File {filepath} not found!", Fore.RED)
    except json.JSONDecodeError:
        print_status("Error: Invalid JSON file!", Fore.RED)
    except Exception as e:
        print_status(f"An error occurred: {str(e)}", Fore.RED)

if __name__ == "__main__":
    read_linkedin_results() 
import requests
import ollama
import pandas as pd
import json
import sys
import re
import time
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Constants
BASE_URL = "http://localhost:3002/v1"

# Unified Logging Functions
def printSuccess(message):
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

def printError(message):
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

def printInfo(message):
    print(f"{Fore.CYAN}ℹ {message}{Style.RESET_ALL}")

def printWarning(message):
    print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")

def scrapeUrl(url):
    """Scrapes a URL and returns its content"""
    printInfo(f"Starting scrape of URL: {url}")
    
    payload = {
        "url": url,
        "formats": ["markdown", "html"]
    }

    try:
        response = requests.post(f"{BASE_URL}/scrape", json=payload)
        data = response.json()

        if data.get("success"):
            printSuccess("Scrape successful! Saving content...")
            with open('scrape_results.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            printSuccess("Scrape data saved to scrape_results.json")
            return data["data"]
        else:
            printError(f"Error in scraping: {data}")
            return None
    except Exception as e:
        printError(f"Scraping failed: {str(e)}")
        return None

def extractInfoFromMarkdown(markdownText):
    """Extracts structured data from markdown content using Ollama"""
    printInfo("Starting markdown extraction...")
    
    prompt = f"""
    You are an AI assistant that extracts structured data **ONLY** from the provided Markdown content. Your task is to extract details for all **explicitly mentioned** individuals.

    ---

    ### **TASK**  
    Extract the following details for each person:
    - **Full Name**  
    - **Position**  
    - **LinkedIn URL**  
    - **Other URLs**  

    ### **STRICT INSTRUCTIONS**  
    1. **Only return individuals explicitly named in the Markdown content.**  
    2. **DO NOT** assume, infer, or hallucinate any details. **Extract only what is explicitly written.**  
    3. **If a field is missing, return `""` (empty string) or `[]` for URLs.**  
    4. **Ensure the output format is a valid JSON array.**  
    5. **Use only the data found in the Markdown text.**  
    6. **Do not modify names, roles, or links. Preserve exact values.**  
    7. **Follow the JSON format strictly—no extra fields, no missing fields.**  

    ---

    ### **Markdown Content:**  
    {markdownText}  

    ---

    ### **EXPECTED JSON OUTPUT FORMAT**  THIS IS JUST AN EXAMPLE NAME AND POSITION DO NOT USE THIS EXAMPLE
    ```json
    [
        {{
            "fullName": "John Doe",
            "position": "Software Engineer",
            "linkedin": "https://linkedin.com/in/johndoe",
            "otherUrls": ["https://johndoe.dev"]
        }},
        {{
            "fullName": "Jane Smith",
            "position": "Product Manager",
            "linkedin": "https://linkedin.com/in/janesmith",
            "otherUrls": []
        }}
    ]
    ```

    ---

    ### **EXAMPLES TO FOLLOW**  

    ✅ **Correct Output:**  
    - `"fullName": "John Doe"` → Found in Markdown  
    - `"position": "Software Engineer"` → Found in Markdown  
    - `"linkedin": "https://linkedin.com/in/johndoe"` → Found in Markdown  
    - `"otherUrls": ["https://johndoe.dev"]` → Found in Markdown  

    ❌ **Incorrect Output:**  
    - `"fullName": "Invented Name"` → ❌ Not found in Markdown  
    - `"position": "Assumed Role"` → ❌ Not explicitly stated  
    - `"linkedin": "https://linkedin.com/in/random"` → ❌ If missing, return `""`  
    - `"otherUrls": ["https://fakewebsite.com"]` → ❌ If missing, return `[]`  

    ---

    ### **FINAL REMINDER**  
    - **STRICTLY EXTRACT ONLY WHAT EXISTS IN MARKDOWN.**  
    - **DO NOT add, infer, assume, or modify any data.**  
    - **RETURN A VALID JSON OUTPUT.**  

    ---

    """

    try:
        start_time = time.time()
        
        response = ollama.chat(model='chevalblanc/gpt-4o-mini', messages=[{'role': 'user', 'content': prompt}])
        # response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
        
        printInfo(f"Ollama request completed in {time.time() - start_time:.2f} seconds")

        rawResponse = response['message']['content']
        jsonMatch = re.search(r'\[\s*\{.*\}\s*\]', rawResponse, re.DOTALL)

        if jsonMatch:
            extractedData = json.loads(jsonMatch.group(0))
            printSuccess(f"Successfully extracted data for {len(extractedData)} people")
            return extractedData
        else:
            printError("Failed to extract valid JSON from Ollama response")
            return None

    except Exception as e:
        printError(f"Extraction failed: {str(e)}")
        return None

def saveToExcel(data, filename="extracted_data.xlsx"):
    """Saves extracted data to Excel file"""
    try:
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine='openpyxl')
        printSuccess(f"Data successfully saved to {filename}")
    except Exception as e:
        printError(f"Failed to save Excel file: {str(e)}")

def main():
    """Main execution flow"""
    printInfo("🔥 LinkedIn Profile Scraper Started...")
    
    # Get URL from command line or use default
    url = "https://www.zoom.com/en/about/team/"
    # url = "https://www.realproton.com/team"
    # url = sys.argv[1] if len(sys.argv) > 1 else input("Enter URL to scrape: ")
    
    # Step 1: Scrape the URL
    scraped_data = scrapeUrl(url)
    if not scraped_data or "markdown" not in scraped_data:
        printError("Failed to obtain markdown content")
        return

    # Step 2: Extract information
    extracted_info = extractInfoFromMarkdown(scraped_data["markdown"])
    if not extracted_info:
        printError("Failed to extract information from markdown")
        return

    # Step 3: Save to Excel
    saveToExcel(extracted_info)
    printSuccess("🎉 All tasks completed successfully!")

if __name__ == "__main__":
    main() 
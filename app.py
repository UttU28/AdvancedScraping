import requests
import ollama
import pandas as pd
import json
import sys
import re
import time
from colorama import init, Fore, Style
from prompts import EXTRACTION_PROMPT, COMPLETE_PROMPT
import openai
from dotenv import load_dotenv
import os

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

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
    
    
    try:
        start_time = time.time()
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Or use 'gpt-4' if you prefer
            messages=[
                {"role": "system", "content": "You are an AI assistant that extracts structured data ONLY from the provided Markdown content."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(markdownText=markdownText)}
                # {"role": "user", "content": COMPLETE_PROMPT}
            ],
            temperature=0.0,  # Deterministic, no randomness
            top_p=1.0,        # Standard sampling
            frequency_penalty=0.0,  # No penalty for repetition
            presence_penalty=0.0   # No penalty for repeating tokens
        )
        
        printInfo(f"Ollama request completed in {time.time() - start_time:.2f} seconds")

        rawResponse = response['choices'][0]['message']['content'].strip()
        jsonMatch = re.search(r'\[\s*\{.*\}\s*\]', rawResponse, re.DOTALL)

        if jsonMatch:
            extractedData = json.loads(jsonMatch.group(0))
            printSuccess(f"Successfully extracted data for {len(extractedData)} people")
            return extractedData
        else:
            printWarning("Failed to extract valid JSON from Ollama response. Saving prompt and response to file...")
            with open('failed_extraction.txt', 'w', encoding='utf-8') as f:
                f.write("=== PROMPT ===\n\n")
                f.write(EXTRACTION_PROMPT.format(markdownText=markdownText))
                f.write("\n\n=== RESPONSE ===\n\n")
                f.write(rawResponse)
            printInfo("Prompt and response saved to failed_extraction.txt")
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
    url = "https://www.entegris.com/en/home/about-us/corporate-overview.html"
    url = "https://www.realproton.com/team"
    url = "https://www.zoom.com/en/about/team/"
    url = "https://stg-3.com/event/rwa-london-summit/"
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
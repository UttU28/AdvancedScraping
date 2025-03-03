import requests
import pandas as pd
import json
import re
import time
from colorama import init, Fore, Style
from prompts import EXTRACTION_PROMPT
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

def printTitle(message):
    print(f"{Fore.MAGENTA}{Style.BRIGHT}{message}{Style.RESET_ALL}\n")

def printSubTitle(message):
    print(f"{Fore.YELLOW}{Style.BRIGHT}{message}{Style.RESET_ALL}\n")

def scrapeUrl(url):
    """Scrapes a URL and returns its content"""
    printSubTitle(f"Starting scrape of URL: {url}")
    
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
    printSubTitle("Starting markdown extraction...")
    
    try:
        start_time = time.time()
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Or use 'gpt-4' if you prefer
            messages=[
                {"role": "system", "content": "You are an AI assistant that extracts structured data ONLY from the provided Markdown content."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(markdownText=markdownText)}
            ],
            temperature=0.0,  # Deterministic, no randomness
            top_p=1.0,        # Standard sampling
            frequency_penalty=0.0,  # No penalty for repetition
            presence_penalty=0.0   # No penalty for repeating tokens
        )

        # Calculate costs
        input_tokens = response['usage']['prompt_tokens']
        output_tokens = response['usage']['completion_tokens']
        
        input_rate = 0.0015  # $0.0015 per 1K tokens for GPT-3.5-turbo input
        output_rate = 0.002  # $0.002 per 1K tokens for GPT-3.5-turbo output
        
        total_cost = (input_tokens * input_rate / 1000) + (output_tokens * output_rate / 1000)
        
        printInfo(f"Token usage - Input: {input_tokens}, Output: {output_tokens}")
        printInfo(f"Total cost: ${total_cost:.4f}")
        
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
    try:
        df = pd.DataFrame(data)
        printInfo(f"Saving data to Excel file: {filename}...")
        df.to_excel(filename, index=False, engine='openpyxl')
        printSuccess(f"Data successfully saved to {filename}")
    except Exception as e:
        printError(f"Failed to save Excel file: {str(e)}")

def scrapeHumans(searchUrl):
    # Step 1: Scrape the URL
    scraped_data = scrapeUrl(searchUrl)
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
    printTitle("Starting Web Scraping and Data Extraction...")

    urls = [
        "https://www.entegris.com/en/home/about-us/corporate-overview.html",
        "https://www.realproton.com/team",
        "https://www.zoom.com/en/about/team/",
        "https://stg-3.com/event/rwa-london-summit/",
        "https://www.datacenterdynamics.com/en/dcdconnect-live/virginia/2025/",
        "https://datacenternation.com/dcn-milan-2025/speakers/",
        "https://www.dcftrends.com/2025/speakers",
        "https://malaysia.dccisummit.com/all-speakers",
        "https://digitransformationsummit.com/ksa/",
        "https://www.datascience.salon/newyork/",
        "https://digitransformationsummit.com/uae/#speakers",
        "https://metro-connect-usa.com/2025-speakers",
        "https://www.terrapinn.com/conference/connected-america/speakers.stm",
    ]

    # We will demonstrate the scraping for one URL for now
    searchUrl = "https://stg-3.com/event/rwa-london-summit/"
    scrapeHumans(searchUrl=searchUrl)

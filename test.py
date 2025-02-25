import requests
import time
import json
from colorama import Fore, Style, init

# Initialize colorama for Windows compatibility
init(autoreset=True)

# Firecrawl local API URL (Make sure Docker is running)
BASE_URL = "http://localhost:3002/v1"

def printSuccess(message):
    """Print success messages in green"""
    print(f"{Fore.GREEN}[✔] {message}{Style.RESET_ALL}")

def printInfo(message):
    """Print informational messages in cyan"""
    print(f"{Fore.CYAN}[ℹ] {message}{Style.RESET_ALL}")

def printWarning(message):
    """Print warnings in yellow"""
    print(f"{Fore.YELLOW}[!] {message}{Style.RESET_ALL}")

def printError(message):
    """Print error messages in red"""
    print(f"{Fore.RED}[X] {message}{Style.RESET_ALL}")

def crawlWebsite(url):
    """Submits a crawl request and returns the job ID"""
    payload = {
        "url": url,
        "limit": 10,  # Adjust as needed
        "scrapeOptions": {"formats": ["markdown", "html"]}
    }

    response = requests.post(f"{BASE_URL}/crawl", json=payload)
    data = response.json()

    if data.get("success"):
        jobId = data["id"]
        printSuccess(f"Crawl job submitted! Job ID: {jobId}")
        return jobId
    else:
        printError(f"Error submitting crawl: {data}")
        return None

def checkCrawlStatus(jobId):
    """Polls Firecrawl to check if the crawl job is completed"""
    url = f"{BASE_URL}/crawl/{jobId}"
    
    while True:
        response = requests.get(url)
        data = response.json()

        if data.get("status") == "completed":
            printSuccess("Crawl completed successfully! Saving data...")
            # Save crawl results to JSON file
            with open(f'crawl_results_{jobId}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            printSuccess(f"Crawl data saved to crawl_results_{jobId}.json")
            return data
        else:
            printWarning("Crawl is still processing... Retrying in 5 seconds.")
            time.sleep(5)

def scrapeUrl(url):
    """Scrapes a URL and returns its content"""
    payload = {
        "url": url,
        "formats": ["markdown", "html"]
    }

    response = requests.post(f"{BASE_URL}/scrape", json=payload)
    data = response.json()

    if data.get("success"):
        printSuccess("Scrape successful! Saving content...")
        # Save scrape results to JSON file
        filename = f'scrape_results_{url.replace("://", "_").replace("/", "_")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        printSuccess(f"Scrape data saved to {filename}")
        return data["data"]
    else:
        printError(f"Error in scraping: {data}")
        return None

def extractData(url, prompt="Extract the company mission from the page."):
    """Extracts structured data using an LLM"""
    payload = {
        "urls": [url],
        "prompt": prompt
    }

    response = requests.post(f"{BASE_URL}/extract", json=payload)
    data = response.json()

    if data.get("success"):
        printSuccess("Data extraction successful! Saving structured data...")
        # Save extraction results to JSON file
        filename = f'extract_results_{url.replace("://", "_").replace("/", "_")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        printSuccess(f"Extracted data saved to {filename}")
        return data
    else:
        printError(f"Error in data extraction: {data}")
        return None

# === Run Example Requests ===
if __name__ == "__main__":
    testUrl = "https://www.realproton.com/team"

    printInfo("🔥 Firecrawl API Client Started...")

    # Crawl the website
    jobId = crawlWebsite(testUrl)
    if jobId:
        checkCrawlStatus(jobId)

    # Scrape the website
    scrapeUrl(testUrl)

    # Extract structured data
    extractData(testUrl)

    printSuccess("🎉 All tasks completed successfully!")

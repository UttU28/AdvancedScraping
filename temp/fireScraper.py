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
            with open(f'crawl_results.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            printSuccess(f"Crawl data saved to crawl_results.json")
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
        filename = f'scrape_results.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        printSuccess(f"Scrape data saved to {filename}")
        return data["data"]
    else:
        printError(f"Error in scraping: {data}")
        return None

def mapWebsite(url):
    """Creates a sitemap for the given URL and returns the list of links"""
    payload = {
        "url": url
    }

    response = requests.post(f"{BASE_URL}/map", json=payload)
    data = response.json()

    if data.get("success"):
        printSuccess(f"Site mapping successful! Found {len(data['links'])} links")
        # Save map results to JSON file
        filename = f'sitemap_results.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        printSuccess(f"Sitemap data saved to {filename}")
        return data["links"]
    else:
        printError(f"Error in mapping: {data}")
        return None

# === Run Example Requests ===
if __name__ == "__main__":
    testUrl = "https://www.entegris.com/en/home/about-us/corporate-overview.html"
    testUrl = "https://www.vcfundventures.com/"
    testUrl = "https://www.realproton.com/team"
    testUrl = "https://www.zoom.com/en/about/team/"

    printInfo("🔥 Firecrawl API Client Started...")

    # jobId = crawlWebsite(testUrl)
    # if jobId:
    #     checkCrawlStatus(jobId)

    # Map the website
    # mapWebsite(testUrl)
    
    # Scrape the website
    scrapeUrl(testUrl)

    printSuccess("🎉 All tasks completed successfully!")

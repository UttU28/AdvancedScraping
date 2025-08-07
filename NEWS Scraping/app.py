from utils import scrapingNews
from utils import filteringNews
from utils import makeExcel
import time


def run_news_pipeline():
    print("\n=== Starting News Pipeline ===\n")
    
    print("Step 1: Scraping news articles...")
    new_articles = scrapingNews.getNews()
    print(f"Scraped {len(new_articles)} new articles")
    time.sleep(1)
    
    print("\nStep 2: Filtering news articles...")
    filteringNews.updateNewsArticles()
    time.sleep(1)
    
    print("\nStep 3: Generating Excel report...")
    makeExcel.exportMatchedToExcel()
    
    print("\n=== News Pipeline Completed ===")

if __name__ == "__main__":
    run_news_pipeline() 
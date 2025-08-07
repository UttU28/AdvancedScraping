import requests
from bs4 import BeautifulSoup
import hashlib
import json
import os
from tqdm import tqdm
from datetime import datetime

# List of news sources with their configurations
newsSources = [
    {
        "url": "https://www.datacenterknowledge.com/",
        "articleSelector": "div.ContentPreview",
        "dateSelector": "span.ListPreview-Date",
        "titleSelector": "a.ListPreview-Title",
        "linkPrefix": "https://www.datacenterknowledge.com",
        "articleTextSelector": "div.ArticleBase-Body"
    },
    {
        "url": "https://www.datacenterdynamics.com/en/news/",
        "articleSelector": "article.card",
        "dateSelector": "time",
        "titleSelector": "a.block-link.headline-link",
        "linkPrefix": "https://www.datacenterdynamics.com",
        "articleTextSelector": "div.article-body"
    },
    {
        "url": "https://datacenterpost.com/",
        "articleSelector": "article.post",
        "dateSelector": "span.updated",
        "titleSelector": "h2.post-title a",
        "linkPrefix": "",
        "articleTextSelector": "div.post-content"
    }
]

# Headers to mimic a browser visit
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

jsonFile = "newsData.json"

def loadExistingNews():
    """Load existing news from the JSON file if it exists."""
    if os.path.exists(jsonFile):
        with open(jsonFile, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []

def standardizeDate(dateStr):
    """Convert various date formats to a standard format (YYYY-MM-DD)."""
    for fmt in ("%b %d, %Y", "%d %b %Y", "%b %d %Y"):
        try:
            return datetime.strptime(dateStr, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return dateStr  # Return original if no format matches

def getNews():
    """Scrape news articles from multiple sources."""
    existingNews = loadExistingNews()
    existingNewsIds = {news["newsID"] for news in existingNews}
    newArticles = []
    
    for source in newsSources:
        response = requests.get(source["url"], headers=headers)
        if response.status_code != 200:
            print(f"Failed to retrieve {source['url']}, status code: {response.status_code}")
            continue
        
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select(source["articleSelector"])
        
        for article in tqdm(articles, desc=f"Extracting articles from {source['url']}"):
            try:
                dateElem = article.select_one(source["dateSelector"])
                titleElem = article.select_one(source["titleSelector"])
                
                if not dateElem or not titleElem:
                    continue
                
                date = standardizeDate(dateElem.get_text(strip=True))
                title = titleElem.get_text(strip=True)
                link = source["linkPrefix"] + titleElem["href"]
                
                newsId = hashlib.md5(link.encode()).hexdigest()
                if newsId in existingNewsIds:
                    # print(f"Skipping existing news: {title}")
                    continue
                
                articleText = getArticleText(link, source["articleTextSelector"])
                
                newsItem = {
                    "newsID": newsId,
                    "date": date,
                    "title": title,
                    "link": link,
                    "articleText": articleText,
                    "matched": None
                }
                
                existingNews.append(newsItem)
                newArticles.append(newsItem)
                saveNews(existingNews)
            except AttributeError:
                continue
    
    return newArticles

def getArticleText(articleUrl, textSelector):
    """Retrieve the full article text from the article page."""
    response = requests.get(articleUrl, headers=headers)
    if response.status_code != 200:
        return ""
    
    soup = BeautifulSoup(response.text, "html.parser")
    articleBody = soup.select(textSelector)
    if not articleBody:
        return ""
    
    return " ".join([p.get_text(strip=True) for p in articleBody]).encode("utf-8", "ignore").decode("utf-8")

def saveNews(newsList):
    """Save the news list to the JSON file."""
    with open(jsonFile, "w", encoding="utf-8") as file:
        json.dump(newsList, file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    newNews = getNews()
    if newNews:
        print(f"{len(newNews)} new articles added and saved to {jsonFile}.")
    else:
        print("No new news articles found.")
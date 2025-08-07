import requests
from bs4 import BeautifulSoup
import hashlib
import json
import os
from tqdm import tqdm

# URL of the news page
URL = "https://www.datacenterknowledge.com/"

# Headers to mimic a browser visit
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

JSON_FILE = "newsData.json"

def loadExistingNews():
    """Load existing news from the JSON file if it exists."""
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []

def getNews():
    """Scrape news articles from the website."""
    response = requests.get(URL, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to retrieve page, status code: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("div", class_="ContentPreview")
    
    existingNews = loadExistingNews()
    existingNewsIds = {news["newsID"] for news in existingNews}
    
    newArticles = []
    for article in tqdm(articles, desc="Extracting news articles"):
        try:
            date = article.find("span", class_="ListPreview-Date").get_text(strip=True)
            titleTag = article.find("a", class_="ListPreview-Title")
            title = titleTag.get_text(strip=True)
            link = "https://www.datacenterknowledge.com" + titleTag["href"]
            
            newsId = hashlib.md5(link.encode()).hexdigest()
            
            if newsId in existingNewsIds:
                print(f"Skipping existing news: {title}")
                continue
            
            articleText = getArticleText(link)
            
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
            
            # Save incrementally after each new article
            saveNews(existingNews)
        except AttributeError:
            continue
    
    return newArticles

def getArticleText(articleUrl):
    """Retrieve the full article text from the article page."""
    response = requests.get(articleUrl, headers=HEADERS)
    if response.status_code != 200:
        return ""
    
    soup = BeautifulSoup(response.text, "html.parser")
    articleBody = soup.find("div", class_="ArticleBase-Body")
    if not articleBody:
        return ""
    
    paragraphs = articleBody.find_all("p")
    articleText = " ".join([p.get_text(strip=True) for p in paragraphs])
    return articleText.encode("utf-8", "ignore").decode("utf-8")

def saveNews(newsList):
    """Save the news list to the JSON file."""
    with open(JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(newsList, file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    newNews = getNews()
    if newNews:
        print(f"{len(newNews)} new articles added and saved to {JSON_FILE}.")
    else:
        print("No new news articles found.")

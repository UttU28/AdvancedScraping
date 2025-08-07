import spacy
import re
import json
import unicodedata
from tqdm import tqdm

def cleanText(text):
    """Remove unusual line terminators from the text."""
    return ''.join(c for c in text if unicodedata.category(c) not in ['Zl', 'Zp'])

def loadCleanedNewsData():
    """Load and clean existing news from the JSON file."""
    with open('newsData.json', 'r', encoding='utf-8') as file:
        rawData = file.read()
    
    # Remove unusual line terminators
    cleanedData = cleanText(rawData)

    # Parse JSON safely
    try:
        return json.loads(cleanedData)
    except json.JSONDecodeError:
        print("Error decoding JSON. The file may be corrupted.")
        return []

def isNewEnergyProject(text):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    
    facilityKeywords = ["data center", "datacenter", "server farm", "AI farm", "computing hub", "cloud infrastructure"]
    projectKeywords = [
        "build", "built", "building", "construct", "constructed", "constructing",
        "develop", "developed", "developing", "open", "opened", "opening",
        "launch", "launched", "launching", "expand", "expanded", "expanding",
        "deploy", "deployed", "deploying", "initiate", "initiated", "initiating"
    ]
    greenKeywords = ["green", "sustainable", "energy-efficient", "energy efficient", "eco-friendly", "eco friendly", "renewable-powered", "renewable power"]
    
    hasFacility = any(keyword in text.lower() for keyword in facilityKeywords)
    hasProject = any(word.lemma_ in projectKeywords for word in doc)
    hasGreen = any(keyword in text.lower() for keyword in greenKeywords)
    
    powerPattern = re.compile(r"(\d{2,})\s*(MW|MegaWatt|megawatt|GW|GigaWatt|gigawatt|TW|TeraWatt|terawatt|PW|PetaWatt|petawatt)", re.IGNORECASE)
    hasSufficientPower = any(int(match.group(1)) >= 100 for match in powerPattern.finditer(text))
    
    valuationPattern = re.compile(r"\$?\d+\s*(million|M|billion|B|trillion|T)", re.IGNORECASE)
    hasMoneyValuation = bool(valuationPattern.search(text))
    
    return hasFacility and hasProject and hasSufficientPower and hasMoneyValuation 

def updateNewsArticles():
    newsData = loadCleanedNewsData()
    
    # Filter only unprocessed articles (matched = None)
    unprocessedArticles = [article for article in newsData if article.get('matched') is None]
    
    if not unprocessedArticles:
        print("No new articles to process")
        return
    
    print(f"Processing {len(unprocessedArticles)} new articles...")

    # Update only unprocessed articles
    for article in tqdm(unprocessedArticles, desc="Processing articles", unit="article"):
        for original_article in newsData:
            if original_article['newsID'] == article['newsID']:
                original_article['matched'] = isNewEnergyProject(article['articleText'])
                break
    
    # Save the cleaned and updated data
    with open('newsData.json', 'w', encoding='utf-8') as file:
        json.dump(newsData, file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    updateNewsArticles()

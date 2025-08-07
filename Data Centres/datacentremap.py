import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def saveToJson(newData, filePath):
    try:
        with open(filePath, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    existingNames = {entry['name'] for entry in data}
    updatedData = data + [entry for entry in newData if entry['name'] not in existingNames]

    with open(filePath, "w") as f:
        json.dump(updatedData, f, indent=4)

chromeOptions = Options()
# chromeOptions.add_argument("--headless")
chromeOptions.add_argument("--disable-gpu")
# chromeOptions.add_argument("--no-sandbox")

service = Service("./chromedriver.exe")
driver = webdriver.Chrome(service=service, options=chromeOptions)

outputDir = "collected_data"
os.makedirs(outputDir, exist_ok=True)

states = [
    "california", "texas", "florida", "virginia", "illinois", "new-york", "missouri", "georgia", "oregon", "ohio",
    "colorado", "washington", "arizona", "nevada", "north-carolina", "iowa", "minnesota", "new-jersey", "massachusetts",
    "michigan", "district-of-columbia", "utah", "pennsylvania", "wisconsin", "alabama", "indiana", "new-mexico", "hawaii",
    "tennessee", "maryland", "nebraska", "kentucky", "montana", "oklahoma", "kansas", "west-virginia", "maine", "alaska",
    "north-dakota", "south-dakota", "south-carolina", "rhode-island", "connecticut", "delaware", "wyoming", "idaho", "vermont",
    "new-hampshire", "louisiana", "mississippi", "arkansas"
]

try:
    for state in states:
        try:
            print(f"Processing state: {state}")
            url = f"https://www.datacentermap.com/usa/{state}/"
            driver.get(url)

            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "ui.card"))
            )

            uiCards = driver.find_elements(By.CLASS_NAME, "ui.card")

            allLinks = []
            for card in uiCards:
                tbody = card.find_element(By.TAG_NAME, "tbody")
                tdElements = tbody.find_elements(By.TAG_NAME, "td")
                for td in tdElements:
                    aTags = td.find_elements(By.TAG_NAME, "a")
                    for aTag in aTags:
                        href = aTag.get_attribute("href")
                        if href:
                            allLinks.append(href)

            stateFilePath = os.path.join(outputDir, f"{state}.json")

            for link in allLinks:
                driver.get(link)

                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "ui.card"))
                )

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                cards = soup.find_all('a', class_='ui card')
                stateData = []
                for card in cards:
                    header = card.find(class_='header')
                    description = card.find(class_='description')

                    if description:
                        description = description.decode_contents()
                        description = description.split('<img')[0]
                        description = description.split('<br/>')

                    locationName = state.replace("-", ' ')

                    stateData.append({
                        'name': header.get_text(strip=True) if header else None,
                        'providerName': description[0].strip() if description else None,
                        'fullAddress': " ".join([desc.strip() for desc in description[1:]]) if description and len(description) > 1 else None,
                        'location': state.upper()
                    })

                saveToJson(stateData, stateFilePath)

        except Exception as e:
            print(f"An error occurred while processing {state}: {e}")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    driver.quit()
    print("Scraping completed.")

#!/usr/bin/env python3
import pytesseract
from PIL import Image
import glob
import json
import os
from tqdm import tqdm


def extractNamePositionCompany(ocrText):
    lines = [line.strip() for line in ocrText.strip().split('\n') if line.strip()]
    people = []
    seen = set()
    i = 0

    while i < len(lines) - 1:
        name = lines[i]
        roleLine = lines[i + 1]

        if ' at ' in roleLine:
            position, company = roleLine.split(' at ', 1)
            key = (name.lower(), position.lower(), company.lower())
            if key not in seen:
                people.append({
                    'name': name,
                    'position': position.strip(),
                    'company': company.strip()
                })
                seen.add(key)
            i += 2
        else:
            i += 1

    return people

def processImagesAndUpdateJson(imageDir='screenshots', jsonPath='people.json'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    allPeople = []
    seen = set()

    if os.path.exists(jsonPath):
        try:
            with open(jsonPath, 'r') as f:
                allPeople = json.load(f)
                for p in allPeople:
                    seen.add((p['name'].lower(), p['position'].lower(), p['company'].lower()))
        except json.JSONDecodeError:
            allPeople = []

    croppedImages = sorted(glob.glob(os.path.join(imageDir, '*_cropped.png')))

    for imagePath in tqdm(croppedImages, desc="Processing Images", unit="img"):
        try:
            image = Image.open(imagePath)
            text = pytesseract.image_to_string(image)
            people = extractNamePositionCompany(text)

            for person in people:
                key = (person['name'].lower(), person['position'].lower(), person['company'].lower())
                if key not in seen:
                    allPeople.append(person)
                    seen.add(key)

            with open(jsonPath, 'w') as f:
                json.dump(allPeople, f, indent=4)
        except Exception as e:
            continue

    return len(allPeople)

if __name__ == "__main__":
    totalPeople = processImagesAndUpdateJson()
    print(f"\nTotal people extracted: {totalPeople}")

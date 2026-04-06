#!/usr/bin/env python3
import pytesseract
from PIL import Image
import glob
import json
import os
import re
from tqdm import tqdm


def cleanField(value):
    if not value:
        return ''
    value = str(value).replace('|', ' ').strip()
    value = re.sub(r'\.{2,}$', '', value)  # remove OCR-truncated trailing dots
    value = re.sub(r'^[\\/\)\]\}\|,\-:\.;]+', '', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def normalizedKey(name, position, company):
    return (
        cleanField(name).lower(),
        cleanField(position).lower(),
        cleanField(company).lower(),
    )


def extractNamePositionCompany(ocrText):
    lines = [line.strip() for line in ocrText.strip().split('\n') if line.strip()]
    people = []
    seen = set()
    i = 0

    while i < len(lines) - 1:
        name = cleanField(lines[i])
        roleLine = lines[i + 1]

        if ' at ' in roleLine or ' - ' in roleLine or '|' in roleLine:
            if ' at ' in roleLine:
                position, company = roleLine.split(' at ', 1)
            elif ' - ' in roleLine:
                position, company = roleLine.split(' - ', 1)
            else:
                position, company = roleLine.split('|', 1)

            position = cleanField(position)
            company = cleanField(company)
            key = normalizedKey(name, position, company)
            if key not in seen and name and position and company:
                people.append({
                    'name': name,
                    'position': position,
                    'company': company
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
                    seen.add(normalizedKey(p.get('name', ''), p.get('position', ''), p.get('company', '')))
        except json.JSONDecodeError:
            allPeople = []

    croppedImages = sorted(glob.glob(os.path.join(imageDir, '*_cropped.png')))

    for imagePath in tqdm(croppedImages, desc="Processing Images", unit="img"):
        try:
            image = Image.open(imagePath)
            text = pytesseract.image_to_string(image)
            people = extractNamePositionCompany(text)

            for person in people:
                person = {
                    'name': cleanField(person.get('name', '')),
                    'position': cleanField(person.get('position', '')),
                    'company': cleanField(person.get('company', '')),
                }
                key = normalizedKey(person['name'], person['position'], person['company'])
                if key not in seen:
                    allPeople.append(person)
                    seen.add(key)

            with open(jsonPath, 'w') as f:
                json.dump(allPeople, f, indent=4)
        except Exception:
            continue

    return len(allPeople)

if __name__ == "__main__":
    totalPeople = processImagesAndUpdateJson()
    print(f"\nTotal people extracted: {totalPeople}")

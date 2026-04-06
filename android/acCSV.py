#!/usr/bin/env python3
import json
import csv
import os
import glob
import re
from difflib import SequenceMatcher


def cleanField(value):
    if value is None:
        return ''
    value = str(value).replace('|', ' ').strip()
    value = re.sub(r'\.{2,}$', '', value)  # remove OCR-truncated trailing dots
    value = re.sub(r'^[\\/\)\]\}\|,\-:\.;]+', '', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def normalizedKey(name, company, position):
    return (cleanField(name).lower(), cleanField(company).lower(), cleanField(position).lower())


def looseText(value):
    return re.sub(r'[^a-z0-9 ]+', '', cleanField(value).lower()).strip()


def isCloseText(a, b, min_ratio=0.94):
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    # OCR often drops/adds a tail character; prefix match handles that safely.
    if len(shorter) >= 6 and longer.startswith(shorter):
        return True
    return SequenceMatcher(None, a, b).ratio() >= min_ratio


def isNearDuplicate(existing, candidate):
    name_a = looseText(existing['name'])
    name_b = looseText(candidate['name'])
    if not isCloseText(name_a, name_b, min_ratio=0.97):
        return False

    company_a = looseText(existing['company'])
    company_b = looseText(candidate['company'])
    if not isCloseText(company_a, company_b, min_ratio=0.94):
        return False

    position_a = looseText(existing['position'])
    position_b = looseText(candidate['position'])
    return isCloseText(position_a, position_b, min_ratio=0.90)


def convertJsonToCsv(jsonFile='people.json', csvFile=None):
    if csvFile is None:
        csvFile = os.path.splitext(jsonFile)[0] + '.csv'
    
    try:
        with open(jsonFile, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print(f"Warning: JSON format unexpected. Expected a list of people, got {type(data).__name__}")
            if isinstance(data, dict) and "people" in data:
                data = data["people"]
            else:
                raise ValueError("Cannot process JSON: invalid format")
        
        deduped = []
        seen = set()
        by_name = {}
        for person in data:
            name = cleanField(person.get('name', ''))
            company = cleanField(person.get('company', ''))
            position = cleanField(person.get('position', ''))
            if not (name and company and position):
                continue
            key = normalizedKey(name, company, position)
            if key in seen:
                continue

            candidate = {'name': name, 'company': company, 'position': position}
            name_key = looseText(name)
            near_dupe = False
            for existing in by_name.get(name_key, []):
                if isNearDuplicate(existing, candidate):
                    near_dupe = True
                    break
            if near_dupe:
                continue

            seen.add(key)
            deduped.append(candidate)
            by_name.setdefault(name_key, []).append(candidate)

        with open(csvFile, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            writer.writerow(["Full Name", "Company", "Position"])
            
            for person in deduped:
                name = person.get('name', '')
                company = person.get('company', '')
                position = person.get('position', '')
                writer.writerow([name, company, position])
        
        print(f"Successfully converted {jsonFile} to {csvFile}")
        print(f"Found {len(data)} people entries, wrote {len(deduped)} cleaned unique rows")
        return csvFile
        
    except FileNotFoundError:
        print(f"Error: JSON file not found at {jsonFile}")
        return None
    except json.JSONDecodeError:
        print(f"Error: {jsonFile} is not a valid JSON file")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def findJsonFiles(directory='.', pattern='*_data.json'):
    return glob.glob(os.path.join(directory, pattern))

if __name__ == "__main__":
    convertJsonToCsv() 
#!/usr/bin/env python3
import json
import csv
import os
import glob

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
        
        with open(csvFile, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            writer.writerow(["Full Name", "Company", "Position"])
            
            for person in data:
                name = person.get('name', '')
                company = person.get('company', '')
                position = person.get('position', '')
                writer.writerow([name, company, position])
        
        print(f"Successfully converted {jsonFile} to {csvFile}")
        print(f"Found {len(data)} people entries")
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
import json

input_file = 'input.json'
output_file = 'data.json'

with open(input_file, 'r', encoding='utf-8') as file:
    data = json.load(file)

cleaned_data = []
for location in data.get('mapLocations', []):
    cleaned_entry = {
        "name": location.get("name", ""),
        "fullAddress": location.get("fullAddress", ""),
        "location": location.get("fullAddress", "").split(",")[-1].strip(),
        "providerName": location.get("providerName", ""),
        "url": location.get("url", "")
    }
    cleaned_data.append(cleaned_entry)

with open(output_file, 'w', encoding='utf-8') as file:
    json.dump(cleaned_data, file, ensure_ascii=False, indent=4)

print(f"Total data in input: {len(data.get('mapLocations', []))}")
print(f"Total data in output: {len(cleaned_data)}")

print(f"Cleaned data has been successfully saved to {output_file}")
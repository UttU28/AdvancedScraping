import json

# File paths
main_file = '3.json'
data_file = '4.json'
output_file = 'm.json'

try:
    # Read the main JSON file
    with open(main_file, 'r', encoding='utf-8') as file:
        main_data = json.load(file)
    
    # Read the data JSON file
    with open(data_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Extract provider names from main_data
    existing_providers = {entry['providerName'] for entry in main_data}
    
    # Iterate through data.json and add missing providers to main.json
    for entry in data:
        if entry['providerName'] not in existing_providers:
            # Create a new entry with data from `data.json` or empty strings for missing fields
            new_entry = {
                "name": entry.get("name", ""),
                "fullAddress": entry.get("fullAddress", ""),
                "location": entry.get("location", ""),
                "providerName": entry.get("providerName", ""),
                "url": entry.get("url", ""),
                "phone": entry.get("phone", "")
            }
            main_data.append(new_entry)
    
    # Write the updated main data to a new JSON file
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(main_data, file, indent=4)
    
    print(f"Updated main data has been saved to '{output_file}'.")

except Exception as e:
    print(f"An error occurred: {e}")

import json
import pandas as pd

# File paths
json_file = 'aa.json'  # Path to the merged JSON file
output_excel = 'provider_summary.xlsx'  # Path to save the Excel file

try:
    # Read the merged JSON file
    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Create a DataFrame from the JSON data
    df = pd.DataFrame(data)
    
    # Count the occurrences of each providerName
    provider_summary = df['providerName'].value_counts().reset_index()
    provider_summary.columns = ['Provider Name', 'Total Data Centres']
    
    # Save the summary to an Excel file
    provider_summary.to_excel(output_excel, index=False)
    
    print(f"Provider summary has been saved to '{output_excel}'.")

except Exception as e:
    print(f"An error occurred: {e}")

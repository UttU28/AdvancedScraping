import pandas as pd
import json
from datetime import datetime

def convertJsonToExcel():
    try:
        # Read JSON file
        with open('consolidated_linkedin_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Replace NaN values with empty string
        df = df.fillna("")
        
        # Remove duplicates (based on Full Name and Company Name)
        initial_count = len(df)
        if 'Full Name' in df.columns and 'Company Name' in df.columns:
            df = df.drop_duplicates(subset=['Full Name', 'Company Name'], keep='first')
            print(f"Removed {initial_count - len(df)} duplicate entries")
        else:
            # If those columns don't exist, try to remove exact duplicates
            df = df.drop_duplicates()
            print(f"Removed {initial_count - len(df)} duplicate entries")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outputFile = f'linkedin_data_{timestamp}.xlsx'
        
        # Convert to Excel
        df.to_excel(outputFile, index=False, sheet_name='LinkedIn Data')
        
        print(f"Successfully converted to Excel: {outputFile}")
        print(f"Final count: {len(df)} unique entries")
        
    except FileNotFoundError:
        print("Error: consolidated_linkedin_data.json not found!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    convertJsonToExcel() 
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
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outputFile = f'linkedin_data_{timestamp}.xlsx'
        
        # Convert to Excel
        df.to_excel(outputFile, index=False, sheet_name='LinkedIn Data')
        
        print(f"Successfully converted to Excel: {outputFile}")
        
    except FileNotFoundError:
        print("Error: consolidated_linkedin_data.json not found!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    convertJsonToExcel() 
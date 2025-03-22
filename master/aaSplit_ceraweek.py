import pandas as pd
import math
import os
import json

def split_ceraweek_data():
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                # Read the CSV file with different encoding
                df = pd.read_csv('people.csv', encoding=encoding)
                print(f"Successfully read file with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise Exception("Could not read the CSV file with any of the attempted encodings")
        
        # Calculate number of pages needed
        entries_per_page = 100
        total_entries = len(df)
        total_pages = math.ceil(total_entries / entries_per_page)
        
        print(f"\nTotal entries: {total_entries}")
        print(f"Creating {total_pages} files with {entries_per_page} entries each")
        print("-"*80)
        
        # Create a directory for the split files
        base_dir = "ceraWeek_data"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        
        # Dictionary to store file processing status
        processing_status = {}
        
        # Split and save data into multiple files
        for page_num in range(total_pages):
            start_idx = page_num * entries_per_page
            end_idx = min((page_num + 1) * entries_per_page, total_entries)
            
            # Get the chunk of data for this page
            page_data = df.iloc[start_idx:end_idx]
            
            # Create filename with page number in the directory
            filename = f'ceraWeek_page_{page_num + 1}.csv'
            filepath = os.path.join(base_dir, filename)
            
            # Save to CSV
            page_data.to_csv(filepath, index=False, encoding='utf-8')
            print(f"Created {filepath} with {len(page_data)} entries")
            
            # Add to processing status
            processing_status[filename] = {
                "processed": False,
                "entries": len(page_data),
                "created_at": pd.Timestamp.now().isoformat()
            }
        
        # Save processing status to JSON file
        status_filepath = os.path.join(base_dir, 'processing_status.json')
        with open(status_filepath, 'w', encoding='utf-8') as f:
            json.dump(processing_status, f, indent=4)
        
        print("\nAll files have been created successfully!")
        print(f"Files are saved in the '{base_dir}' directory")
        print(f"Files are named as: ceraWeek_page_1.csv to ceraWeek_page_{total_pages}.csv")
        print(f"Processing status saved to: {status_filepath}")

    except FileNotFoundError:
        print("Error: ceraWeek.csv file not found!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    split_ceraweek_data() 
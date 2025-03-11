import json
import os
from pathlib import Path

def process_json_file(file_path):
    # Read the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filter out entries with empty search_results
    filtered_data = [entry for entry in data if entry.get('search_results') and len(entry['search_results']) > 0]
    
    # Trim search_results to max 2 results
    for entry in filtered_data:
        if len(entry['search_results']) > 2:
            entry['search_results'] = entry['search_results'][:2]
    
    return filtered_data

def main():
    # Get the googleData directory path
    google_data_dir = Path('googleData')
    
    # Store all entries
    all_entries = []
    
    # Process all JSON files in the directory
    total_entries = 0
    for file_path in google_data_dir.glob('*.json'):
        print(f"Processing {file_path.name}...")
        entries = process_json_file(file_path)
        all_entries.extend(entries)
        total_entries += len(entries)
        print(f"Processed {len(entries)} entries from {file_path.name}")
    
    # Write all entries to a single output file
    output_file = google_data_dir / 'merged_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_entries, f, indent=2, ensure_ascii=False)
    
    print(f"\nTotal entries processed: {total_entries}")
    print(f"Merged results saved to: {output_file}")

if __name__ == "__main__":
    main() 
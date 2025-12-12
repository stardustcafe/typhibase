import json
import csv
import os
import glob

def json_to_csv(json_filepath):
    csv_filepath = json_filepath.replace('.json', '.csv')
    print(f"Converting {json_filepath} to {csv_filepath}...")
    
    try:
        with open(json_filepath, 'r') as jf:
            data = json.load(jf)
            
        if not isinstance(data, list):
            print(f"Skipping {json_filepath}: Root element is not a list.")
            return

        if not data:
            print(f"Skipping {json_filepath}: Empty list.")
            return

        # Collect all unique keys from all dictionaries to handle potential missing keys
        keys = set()
        for entry in data:
            if isinstance(entry, dict):
                keys.update(entry.keys())
        
        fieldnames = sorted(list(keys))
        
        # Ensure 'day' is first if it exists
        if 'day' in fieldnames:
            fieldnames.remove('day')
            fieldnames.insert(0, 'day')

        with open(csv_filepath, 'w', newline='') as cf:
            writer = csv.DictWriter(cf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
        print(f"Successfully converted {json_filepath}.")
        
    except Exception as e:
        print(f"Failed to convert {json_filepath}: {e}")

def main():
    # Find all JSON files in the current directory
    # We filter for files that look like history files to avoid converting config/metadata files if any
    # But user asked for "all json files", so I will try all but be careful with structure.
    json_files = glob.glob("*.json")
    
    if not json_files:
        print("No JSON files found in the current directory.")
        return

    print(f"Found {len(json_files)} JSON files.")
    
    for json_file in json_files:
        json_to_csv(json_file)

if __name__ == "__main__":
    main()

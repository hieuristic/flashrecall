import csv
import os

data_dir = '/Users/charlie/Desktop/apps/flashrecall/data'
files = {
    'A1': os.path.join(data_dir, 'A1.csv'),
    'A2': os.path.join(data_dir, 'A2.csv'),
    'B1': os.path.join(data_dir, 'B1.csv')
}
output_file = os.path.join(data_dir, 'goethe.csv')
old_file = os.path.join(data_dir, 'geothe.csv')

def merge_csvs():
    combined_data = []
    headers = []

    for level, file_path in files.items():
        if os.path.exists(file_path):
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if not headers:
                    headers = [fn for fn in reader.fieldnames if fn != 'URL'] + ['Level']
                
                for row in reader:
                    clean_row = {fn: row[fn] for fn in headers if fn != 'Level'}
                    clean_row['Level'] = level
                    combined_data.append(clean_row)
        else:
            print(f"Warning: {file_path} does not exist.")

    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(combined_data)
    
    print(f"Successfully created {output_file} with {len(combined_data)} entries.")

    if os.path.exists(old_file):
        os.remove(old_file)
        print(f"Deleted {old_file}.")
    else:
        print(f"{old_file} not found, skip deletion.")

if __name__ == "__main__":
    merge_csvs()

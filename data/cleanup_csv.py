import csv
import os
import re

csv_path = '/Users/charlie/Desktop/apps/flashrecall/goethe.csv'
temp_path = '/Users/charlie/Desktop/apps/flashrecall/goethe_clean.csv'

def clean_csv():
    if not os.path.exists(csv_path):
        print("File not found.")
        return

    def clean_quotes(text):
        if not text: return ""
        # Remove literal double quotes and common variations
        return text.replace('"', '').replace('„', '').replace('“', '').replace('”', '').strip()

    def first_sentence(text):
        if not text or text == "nan": return "nan"
        # Split by .!?
        parts = re.split(r'([.!?])', text)
        if len(parts) >= 2:
            return (parts[0] + parts[1]).strip()
        return text.strip()

    with open(csv_path, 'r', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames
        rows = list(reader)

    with open(temp_path, 'w', encoding='utf-8', newline='') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            # 1. English: First word only
            if row.get('English'):
                row['English'] = row['English'].split(',')[0].split(';')[0].strip()
            
            # 2. Examples: First sentence only
            if row.get('German_Example'):
                row['German_Example'] = first_sentence(row['German_Example'])
            if row.get('English_Example'):
                row['English_Example'] = first_sentence(row['English_Example'])
            
            # 3. All fields: remove quotes
            for key in row:
                row[key] = clean_quotes(row[key])
                
            writer.writerow(row)

    os.rename(temp_path, csv_path)
    # Also sync with the data folder
    import shutil
    shutil.copy2(csv_path, '/Users/charlie/Desktop/apps/flashrecall/data/goethe.csv')
    print("Cleanup complete.")

if __name__ == "__main__":
    clean_csv()

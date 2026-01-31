import h5py
import json
import csv
import os
from tqdm import tqdm

data_dir = '/Users/charlie/Desktop/apps/flashrecall/data'
input_csv = os.path.join(data_dir, 'goethe.csv')
h5_path = os.path.join(data_dir, 'ganz.h5')
output_csv = os.path.join(data_dir, 'goethe_enriched.csv')

def enrich():
    # 1. Load lemmas from goethe.csv
    vocab = {}
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # Filter out existing enriched columns and the URL column
        fieldnames = [fn for fn in reader.fieldnames if fn not in ['English', 'Example', 'URL']]
        for row in reader:
            lemma = row['Lemma']
            # Clean row to only include base fields
            clean_row = {fn: row[fn] for fn in fieldnames}
            vocab[lemma] = {
                'row': clean_row,
                'english_translations': set()
            }

    # 2. Iterate through ganz.h5 to find matches
    print(f"Reading {h5_path}...")
    with h5py.File(h5_path, 'r') as f:
        words = f['word']
        lang_codes = f['lang_code']
        translations = f['translations']
        senses = f['senses']
        
        n = len(words)
        batch_size = 10000
        
        for i in tqdm(range(0, n, batch_size), desc="Enriching vocab"):
            end = min(i + batch_size, n)
            
            # Filter for German entries first to avoid decoding everything
            batch_langs = lang_codes[i:end]
            indices = [j for j, l in enumerate(batch_langs) if l == b'de']
            
            if not indices:
                continue
                
            batch_words = [words[i+j].decode('utf-8', errors='ignore') for j in indices]
            batch_trans = [translations[i+j].decode('utf-8', errors='ignore') for j in indices]
            batch_senses = [senses[i+j].decode('utf-8', errors='ignore') for j in indices]
            
            for word, trans_json, senses_json in zip(batch_words, batch_trans, batch_senses):
                if word in vocab:
                    # Extract English translations
                    try:
                        trans_list = json.loads(trans_json)
                        for t in trans_list:
                            if t.get('lang_code') == 'en':
                                words_found = t.get('word', '')
                                if words_found:
                                    # Split by comma in case one entry has multiple words
                                    for w in words_found.split(','):
                                        vocab[word]['english_translations'].add(w.strip())
                    except:
                        pass
                    

    # 3. Write output
    new_fieldnames = fieldnames + ['English']
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        
        for lemma, data in vocab.items():
            row = data['row']
            # Join only the first 2 unique english translations
            eng_list = sorted(filter(None, data['english_translations']))
            eng = ", ".join(eng_list[:2])
            
            row['English'] = eng if eng else "nan"
            writer.writerow(row)

    print(f"Enrichment complete. Saved to {output_csv}")

if __name__ == "__main__":
    enrich()

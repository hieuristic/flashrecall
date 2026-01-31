import h5py
import spacy
import json
import csv
from collections import Counter
from tqdm import tqdm
import os
import sys
import re

# Load spaCy
try:
    import site
    user_site = site.getusersitepackages()
    if user_site not in sys.path:
        sys.path.append(user_site)
    import spacy
    # Disable components we don't need for lemmatization
    nlp = spacy.load("de_core_news_sm", disable=["parser", "ner"])
except Exception as e:
    print(f"Error loading spaCy: {e}")
    sys.exit(1)

def get_text_from_senses(senses_json):
    if not senses_json:
        return ""
    try:
        senses = json.loads(senses_json)
        text_parts = []
        for sense in senses:
            if 'glosses' in sense:
                text_parts.extend(sense['glosses'])
            if 'examples' in sense:
                for ex in sense['examples']:
                    if 'text' in ex:
                        text_parts.append(ex['text'])
        return " ".join(text_parts)
    except:
        return ""

def process():
    data_path = 'ganz.h5'
    output_path = 'goethe.csv'
    freq_data_path = 'lemma_freqs.json'
    
    # We remove freq_data_path to force re-calculation with correct casing
    if os.path.exists(freq_data_path):
        os.remove(freq_data_path)

    print("Highly optimized processing of ganz.h5 (Case Preserved)...")
    raw_counts = Counter()
    
    with h5py.File(data_path, 'r') as f:
        # Check available keys to be sure
        lang_codes = f['lang_code']
        senses = f['senses']
        words = f['word']
        
        n = len(lang_codes)
        batch_size = 10000
        
        # Step 1: Count raw tokens in all German entries
        # PRESERVING CASE for accurate German lemmatization
        for i in tqdm(range(0, n, batch_size), desc="Counting raw tokens"):
            end = min(i + batch_size, n)
            batch_langs = lang_codes[i:end]
            batch_senses = senses[i:end]
            batch_words = words[i:end]
            
            for j in range(len(batch_langs)):
                if batch_langs[j] == b'de':
                    # Entry word
                    word_str = batch_words[j].decode('utf-8', errors='ignore')
                    raw_counts[word_str] += 1
                    
                    # Senses and examples
                    text = get_text_from_senses(batch_senses[j].decode('utf-8', errors='ignore'))
                    if text:
                        # Regex that includes German characters, preserving case
                        tokens = re.findall(r'[A-Za-zÄÖÜäöüß]+', text)
                        for tok in tokens:
                            raw_counts[tok] += 1
    
    # Step 2: Lemmatize UNIQUE tokens and aggregate counts
    print(f"Lemmatizing {len(raw_counts)} unique tokens...")
    lemma_freqs = Counter()
    unique_tokens = list(raw_counts.keys())
    
    # Batch processing with spaCy pipe
    for doc in tqdm(nlp.pipe(unique_tokens, batch_size=5000), total=len(unique_tokens), desc="spaCy Lemmatization"):
        if not doc or len(doc) == 0:
            continue
        token_text = doc[0].text
        lemma = doc[0].lemma_
        lemma_freqs[lemma] += raw_counts[token_text]
        
    print(f"Saving frequencies to {freq_data_path}")
    with open(freq_data_path, 'w', encoding='utf-8') as f:
        json.dump(lemma_freqs, f, ensure_ascii=False)

    # Update goethe.csv
    print(f"Updating {output_path}...")
    temp_output = output_path + '.tmp'
    try:
        # Load goethe lemmas to check existence
        with open(output_path, 'r', encoding='utf-8') as f_in, \
             open(temp_output, 'w', encoding='utf-8', newline='') as f_out:
            reader = csv.DictReader(f_in)
            target_fieldnames = [fn for fn in reader.fieldnames if fn != 'Frequency'] + ['Frequency']
            writer = csv.DictWriter(f_out, fieldnames=target_fieldnames)
            writer.writeheader()
            
            for row in reader:
                lemma = row['Lemma']
                # Try direct lookup, then lower-case if missing
                freq = lemma_freqs.get(lemma, 0)
                if freq == 0:
                    # Maybe it's stored lowercased in the lemma index (less likely for nouns)
                    freq = lemma_freqs.get(lemma.lower(), 'nan')
                
                row['Frequency'] = freq
                writer.writerow(row)
        
        os.replace(temp_output, output_path)
        print("Success! goethe.csv updated with high-quality frequencies.")
    except Exception as e:
        print(f"Error updating CSV: {e}")
        if os.path.exists(temp_output):
            os.remove(temp_output)

if __name__ == "__main__":
    process()

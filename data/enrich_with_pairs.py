import csv
import os
import spacy
from tqdm import tqdm
import re

# Load spaCy for German lemmatization
try:
    nlp = spacy.load("de_core_news_sm", disable=["parser", "ner"])
except Exception as e:
    print(f"Error loading spaCy: {e}")
    import sys
    sys.exit(1)

data_dir = '/Users/charlie/Desktop/apps/flashrecall/data'
input_csv = os.path.join(data_dir, 'goethe.csv')
tsv_path = os.path.join(data_dir, 'de_en_pair.tsv')
output_csv = os.path.join(data_dir, 'goethe_enriched.csv')

def enrich_with_pairs():
    # 1. Load lemmas from goethe.csv
    vocab = {}
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            lemma = row['Lemma']
            vocab[lemma] = row
            vocab[lemma]['German_Example'] = "nan"
            vocab[lemma]['English_Example'] = "nan"

    target_lemmas = set(vocab.keys())
    matched_words = set()
    
    pbar = tqdm(total=len(target_lemmas), desc="Words Matched")
    
    print(f"Reading {tsv_path} using batches...")
    
    def get_sentences():
        with open(tsv_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    yield parts[1], parts[3]

    batch_size = 500
    current_sentences = []
    
    for de_sen, en_sen in get_sentences():
        current_sentences.append((de_sen, en_sen))
        
        if len(current_sentences) >= batch_size:
            # Process batch
            de_texts = [s[0] for s in current_sentences]
            for i, doc in enumerate(nlp.pipe(de_texts, batch_size=batch_size)):
                remaining = target_lemmas - matched_words
                if not remaining:
                    break
                
                sentence_lemmas = {token.lemma_ for token in doc}
                matches = sentence_lemmas.intersection(remaining)
                for word in matches:
                    # Get English translations from vocab
                    english_val = vocab[word].get('English', '')
                    if not english_val or english_val == "nan":
                        continue
                    
                    # Split translations and clean them (remove "to " for verbs, etc)
                    translations = [t.strip().lower() for t in re.split(r'[,;]', english_val) if t.strip()]
                    
                    en_sen_lower = current_sentences[i][1].lower()
                    
                    found_match = False
                    for trans in translations:
                        # Clean "to " prefix for verbs
                        clean_trans = re.sub(r'^to\s+', '', trans)
                        # Check for literal whole word match in English sentence
                        if re.search(r'\b' + re.escape(clean_trans) + r'\b', en_sen_lower):
                            found_match = True
                            break
                    
                    if found_match:
                        vocab[word]['German_Example'] = current_sentences[i][0]
                        vocab[word]['English_Example'] = current_sentences[i][1]
                        matched_words.add(word)
                        pbar.update(1)
            
            current_sentences = []
            if len(matched_words) == len(target_lemmas):
                break
    
    # Process final batch
    if current_sentences and len(matched_words) < len(target_lemmas):
         de_texts = [s[0] for s in current_sentences]
         for i, doc in enumerate(nlp.pipe(de_texts, batch_size=len(de_texts))):
             remaining = target_lemmas - matched_words
             sentence_lemmas = {token.lemma_ for token in doc}
             matches = sentence_lemmas.intersection(remaining)
             for word in matches:
                 # Get English translations from vocab
                 english_val = vocab[word].get('English', '')
                 if not english_val or english_val == "nan":
                     continue
                 
                 # Split translations and clean them (remove "to " for verbs, etc)
                 translations = [t.strip().lower() for t in re.split(r'[,;]', english_val) if t.strip()]
                 
                 en_sen_lower = current_sentences[i][1].lower()
                 
                 found_match = False
                 for trans in translations:
                     # Clean "to " prefix for verbs
                     clean_trans = re.sub(r'^to\s+', '', trans)
                     # Check for literal whole word match in English sentence
                     if re.search(r'\b' + re.escape(clean_trans) + r'\b', en_sen_lower):
                         found_match = True
                         break
                 
                 if found_match:
                     vocab[word]['German_Example'] = current_sentences[i][0]
                     vocab[word]['English_Example'] = current_sentences[i][1]
                     matched_words.add(word)
                     pbar.update(1)

    pbar.close()

    # Write output
    final_fieldnames = [fn for fn in fieldnames if fn not in ['German_Example', 'English_Example']]
    final_fieldnames += ['German_Example', 'English_Example']
    
    def clean_text(text):
        if not text or text == "nan": return "nan"
        # Remove all types of double quotes
        text = text.replace('"', '').replace('„', '').replace('“', '')
        return text.strip()

    def get_first_sentence(text):
        if not text or text == "nan": return "nan"
        # Split by . ! or ? but keep the punctuation. 
        # Simple split:
        match = re.split(r'([.!?])', text)
        if len(match) >= 2:
            return (match[0] + match[1]).strip()
        return text.strip()

    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=final_fieldnames)
        writer.writeheader()
        for lemma in vocab:
            row = vocab[lemma]
            
            # 1. Take only the first English translation
            if 'English' in row and row['English'] != "nan":
                row['English'] = row['English'].split(',')[0].strip()
            
            # 2. Clean quotes from all fields
            for key in row:
                row[key] = clean_text(row[key])
            
            # 3. Take only the first sentence for examples
            row['German_Example'] = get_first_sentence(row['German_Example'])
            row['English_Example'] = get_first_sentence(row['English_Example'])
            
            writer.writerow(row)

    print(f"Enrichment complete. Matched {len(matched_words)}/{len(target_lemmas)} words.")

if __name__ == "__main__":
    enrich_with_pairs()

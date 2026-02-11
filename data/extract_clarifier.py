#!/usr/bin/env python3
"""
Extract parenthesized clarifier text from the English column in goethe_final.csv
and add it as a new 'Clarifier' column. The parenthesized text is removed from
the English column.

Examples:
  "departure (flight)" -> English: "departure", Clarifier: "flight"
  "friend (male)"      -> English: "friend",    Clarifier: "male"
  "to ask (for info)"  -> English: "to ask",    Clarifier: "for info"
  "apple"              -> English: "apple",      Clarifier: ""
"""

import csv
import re
import sys


def extract_clarifier(english_text):
    """Extract text in parentheses from English translation.
    Returns (cleaned_english, clarifier)."""
    if not english_text or english_text == "nan":
        return english_text, ""

    # Match parenthesized text at end of string: "word (clarifier)"
    # Also handle: "word/word2 (clarifier)"
    match = re.search(r'\s*\(([^)]+)\)\s*$', english_text)
    if match:
        clarifier = match.group(1).strip()
        cleaned = english_text[:match.start()].strip()
        return cleaned, clarifier

    return english_text, ""


def process_csv(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        fieldnames = list(reader.fieldnames) + ['Clarifier']

        rows = []
        extracted_count = 0
        for row in reader:
            english = row.get('English', '')
            cleaned, clarifier = extract_clarifier(english)
            row['English'] = cleaned
            row['Clarifier'] = clarifier
            rows.append(row)
            if clarifier:
                extracted_count += 1

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)

    print(f"Processed {len(rows)} rows, extracted {extracted_count} clarifiers.")
    print(f"Output written to {output_file}")


if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'goethe_final.csv'
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file  # overwrite by default
    process_csv(input_file, output_file)

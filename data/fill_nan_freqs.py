import csv
import os
from collections import defaultdict

def fill_nan_frequencies():
    input_path = 'goethe.csv'
    temp_output = 'goethe.csv.tmp'
    
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    # Read data and group by level
    rows = []
    level_data = defaultdict(list)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            freq_str = str(row['Frequency']).strip().lower()
            if freq_str != 'nan' and freq_str != '':
                try:
                    freq = float(freq_str)
                    row['Frequency'] = freq
                    level_data[row['Level']].append(freq)
                except ValueError:
                    row['Frequency'] = 'nan'
            else:
                row['Frequency'] = 'nan'
            rows.append(row)

    # Calculate averages per level
    level_averages = {}
    for level, freqs in level_data.items():
        if freqs:
            level_averages[level] = sum(freqs) / len(freqs)
        else:
            level_averages[level] = 0
        print(f"Level {level}: Average Frequency = {level_averages[level]:.2f} (based on {len(freqs)} words)")

    # Fill nans
    filled_count = 0
    for row in rows:
        if row['Frequency'] == 'nan':
            avg = level_averages.get(row['Level'], 0)
            row['Frequency'] = int(round(avg))
            filled_count += 1

    # Write back
    with open(temp_output, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            # Convert back to string/int for CSV
            if isinstance(row['Frequency'], float):
                row['Frequency'] = int(round(row['Frequency']))
            writer.writerow(row)

    os.replace(temp_output, input_path)
    print(f"Successfully filled {filled_count} 'nan' values with group averages.")

if __name__ == "__main__":
    fill_nan_frequencies()

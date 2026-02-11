import csv
import sys
import data.vocab_pb2 as vocab_pb2
import os


def convert_csv_to_bin(csv_filename, bin_filename, version=0):
    """
    Convert CSV to binary protobuf format.
    Version encoding: major*10000 + minor*100 + patch
    0.0.0 = 0
    0.1.1 = 101
    """
    vocab_data = vocab_pb2.VocabularyData()
    vocab_data.version = version

    # Use a counter for ID generation if stable hashing isn't strictly required by user,
    # but user mentioned "unique id". Line number is effectively unique for a static CSV.
    # To be safer against reordering, we might want to hash the Lemma,
    # but let's stick to a simple auto-increment for now unless we need to merge.
    # User said: "add an index field so that every word has an unique id to it."

    print(f"Reading {csv_filename}...")

    try:
        with open(csv_filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")

            # Check fields
            # Expected: Lemma;Wortart;Genus;Artikel;nur_im_Plural;Level;Frequency;English;German_Example;English_Example

            for i, row in enumerate(reader):
                word = vocab_data.words.add()
                word.id = i + 1  # 1-based ID

                word.lemma = row.get("Lemma", "")
                word.wortart = row.get("Wortart", "")
                word.genus = row.get("Genus", "")
                word.artikel = row.get("Artikel", "")
                word.level = row.get("Level", "")
                word.frequency = row.get("Frequency", "")
                word.english = row.get("English", "")
                word.german_example = row.get("German_Example", "")
                word.english_example = row.get("English_Example", "")

                # Handle optional/mapping fields if necessary
                word.nur_im_plural = row.get("nur_im_Plural", "0")
                word.clarifier = row.get("Clarifier", "")

    except FileNotFoundError:
        print(f"Error: File {csv_filename} not found.")
        sys.exit(1)

    print(f"Parsed {len(vocab_data.words)} words.")

    with open(bin_filename, "wb") as f:
        f.write(vocab_data.SerializeToString())

    print(f"Successfully wrote {bin_filename} with version {vocab_data.version}")


if __name__ == "__main__":
    CSV_FILE = "goethe_final.csv"
    BIN_FILE = "vocab.bin"

    version = 0
    if os.path.exists(BIN_FILE):
        try:
            old_data = vocab_pb2.VocabularyData()
            with open(BIN_FILE, "rb") as f:
                old_data.ParseFromString(f.read())
            version = old_data.version + 1
            print(
                f"Detected existing {BIN_FILE} at version {old_data.version}. Bumping to {version}."
            )
        except Exception as e:
            print(
                f"Warning: Could not read version from existing {BIN_FILE}. Defaulting to 0. ({e})"
            )

    convert_csv_to_bin(CSV_FILE, BIN_FILE, version=version)

"""
Preprocessing script per project instructions.
Takes input from data/ and outputs to data/derived-data.
All logic lives in wrangling.py; this script runs it.
"""
from wrangling import load_and_process_all, write_derived_data

if __name__ == "__main__":
    data = load_and_process_all()
    write_derived_data(data)
    print(f"Done. Output in {data['out_dir']}")

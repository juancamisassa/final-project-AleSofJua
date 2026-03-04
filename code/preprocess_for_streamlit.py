"""
Preprocess data for Streamlit deployment.
Reads from wrangling module (single source of truth). Outputs to data/derived-data.
Run: python code/preprocess_for_streamlit.py
"""
from wrangling import load_and_process_all, write_derived_data

if __name__ == "__main__":
    print("Loading and processing (via wrangling module)...")
    data = load_and_process_all()
    print("Writing derived data for Streamlit app...")
    write_derived_data(data)
    out_dir = data["out_dir"]
    print(f"Done. Output in {out_dir}")
    print(f"  - geojson.json")
    print(f"  - country_outline.json")
    print(f"  - app_data.json")

import pandas as pd
import json

df = pd.read_excel('AUDIO_299.xlsx')
non_nan_df = df.dropna(subset=[df.columns[0]])

print(f"Total rows: {len(df)}")
print(f"Non-nan rows: {len(non_nan_df)}")

# Let's inspect the first 10 rows and see if the row index maps to wav file name
# We'll save a list of (excel_row_index, question, speaker, exists_wav)
import os
wav_dir = 'Audio_wav-20260708T055213Z-3-001/Audio_wav'
wav_files = set(os.listdir(wav_dir)) if os.path.exists(wav_dir) else set()

mapping = []
for idx, row in df.iterrows():
    # Excel row index is idx + 2 (since header is row 1, and pandas is 0-indexed)
    excel_row_idx = idx + 2
    question = str(row.iloc[0])
    speaker = str(row.iloc[1])
    
    # Check if a wav file with this index exists
    wav_name = f"{excel_row_idx}.wav"
    wav_exists = wav_name in wav_files
    
    mapping.append({
        "excel_row": excel_row_idx,
        "question": question,
        "speaker": speaker,
        "wav_file": wav_name,
        "wav_exists": wav_exists
    })

# Save to json
data = {
    "total_rows": len(df),
    "non_nan_rows": len(non_nan_df),
    "total_wavs": len(wav_files),
    "mapping": mapping
}

with open('excel_summary.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("SUCCESS: mapped excel rows to wav files.")

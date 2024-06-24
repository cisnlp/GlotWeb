import pandas as pd
import json

def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data

def remove_null_entries(data):
    if isinstance(data, dict):
        return {key: value for key, value in data.items() if value is not None}
    elif isinstance(data, list):
        return [remove_null_entries(item) for item in data if item is not None]
    return data

def write_json_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

def add_iso_code(data_frame, glotto_iso_mapping):
    data_frame['glottocode'] = data_frame['glottocode'].astype(str)
    data_frame['iso_code'] = data_frame['glottocode'].map(glotto_iso_mapping)
    return data_frame

def save_dataframe_to_csv(data_frame, file_path):
    try:
        data_frame.to_csv(file_path, index=False)
        print(f"DataFrame successfully saved to {file_path}")
    except Exception as e:
        print(f"An error occurred while saving the DataFrame: {e}")

def remove_empty_iso_codes(data_frame):
    # Replace empty strings with NaN and then drop rows with NaN in 'iso_code'
    cleaned_data_frame = data_frame.replace({'iso_code': {'': None}}).dropna(subset=['iso_code'])
    
    return cleaned_data_frame

### Execution ###
glotto_iso_mapping = read_json_file('glotto_iso.json')
dataset = pd.read_csv('glosslm-corpus-split.csv')
result_df = add_iso_code(dataset, glotto_iso_mapping)
result_df = remove_empty_iso_codes(result_df)
save_dataframe_to_csv(result_df, 'glosslm_train_with_iso.csv')

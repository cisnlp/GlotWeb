import pandas as pd
import yaml
import pycountry
from typing import Dict, Any, Optional

# Function to load configuration
def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

# Load the configuration
config = load_config('config.yaml')

# Extract the language code and script from the config
langisocode693_Script = config['language_detector']['desired_language']
langisocode693_Script = 'ada_Latn'
code, script = langisocode693_Script.split('_')

# Read only the necessary columns into a pandas DataFrame
df = pd.read_csv('language_speakers_data.csv', usecols=['ISO Alpha-3/5', 'Name', 'Speakers worldwide'])

# Set "ISO Alpha-3/5" as the index for faster lookups
df.set_index('ISO Alpha-3/5', inplace=True)

def get_language_name(code: str) -> str:
    """
    Get the language name using pycountry.
    If not found, return the original code.
    """
    try:
        language = pycountry.languages.get(alpha_3=code)
        return language.name if language else code
    except (AttributeError, KeyError):
        return code

def get_speakers(code: str) -> Optional[str]:
    """
    Get the number of speakers from the CSV data.
    If not found by code, try to find by language name.
    Return None if no data is found.
    """
    # Try to find by code (ISO 639-3 or ISO 639-5)
    if code in df.index:
        return df.loc[code, 'Speakers worldwide']
    
    # If not found by code, try to find by language name
    lang_name = get_language_name(code)
    matching_rows = df[df['Name'].str.lower() == lang_name.lower()]
    if not matching_rows.empty:
        return matching_rows['Speakers worldwide'].iloc[0]
    
    return None

# Get language name
lang_name = get_language_name(code)

# Get number of speakers
speakers = get_speakers(code)

print(f"Language: {lang_name}")
print(f"Speakers worldwide: {speakers if speakers is not None else 'No data'}")

# You can now use lang_name and speakers for further tasks or add them to a dictionary
language_info = {
    "name": lang_name,
    "speakers": speakers if speakers is not None else "No data",
    "code": code,
    "script": script
}

print("\nLanguage info dictionary:")
print(language_info)
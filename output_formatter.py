from typing import List, Dict, Any
import pandas as pd
import yaml
import pycountry

def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

config = load_config('config.yaml')

langisocode693_Script = config['language_detector']['desired_language']
code, script = langisocode693_Script.split('_')

language = pycountry.languages.get(alpha_3=code)
lang_name = language.name

df = pd.read_csv('language_speakers_data.csv', usecols=['Name', 'Speakers worldwide'])

# Set "Name" as the index for faster lookups
df.set_index('Name', inplace=True)
speakers = df['Speakers worldwide'].get(lang_name, "No data")

print(f"Speakers worldwide for {lang_name}: {speakers}")

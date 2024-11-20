import os
import yaml
import json
from typing import List, Dict, Any
import requests
from urllib.parse import urlparse

# Load configuration from a YAML file
def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

# Load data from JSON files based on a language code
def load_data(code: str, meta_data_dir: str) -> Dict[str, Any]:
    meta_file_name = os.path.join(meta_data_dir, f"{code}.json")
    with open(meta_file_name, 'r', encoding='utf-8') as file:
        return json.load(file)

# Check if a website's robots.txt file blocks CCBot
def is_ccbot_blocked(url: str) -> bool:
    """
    Check if a website's robots.txt file blocks CCBot.

    Parameters:
        url (str): The URL or domain to check.

    Returns:
        bool: True if CCBot is blocked, False otherwise.
    """
    parsed_url = urlparse(url)
    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    robots_url = f"{domain}/robots.txt"

    try:
        response = requests.get(robots_url, timeout=5)
        response.raise_for_status()

        # Parse robots.txt for CCBot rules
        lines = response.text.splitlines()
        user_agent = None

        for line in lines:
            line = line.strip()
            if line.startswith("User-agent:"):
                user_agent = line.split(":")[1].strip()
            elif user_agent == "CCBot" and line.startswith("Disallow:"):
                path = line.split(":")[1].strip()
                if path == "/":
                    return True
            elif user_agent == "CCBot" and line.startswith("Allow:"):
                path = line.split(":")[1].strip()
                if path == "/":
                    return False
        return False
    except requests.RequestException:
        return False  # Assume not blocked if robots.txt is inaccessible

# Remove sites blocked by CCBot from the dataset
def remove_cc_blocked_site(lang_code: str, meta_data_dir: str) -> Dict[str, Any]:
    data = load_data(lang_code, meta_data_dir)
    sites = data.get('Sites', [])
    data['Sites'] = [site for site in sites if not is_ccbot_blocked(site['Site URL'])]
    return data

# Process files and save cleaned data
from tqdm import tqdm

# Process files and save cleaned data
def process_files(input_label: str, meta_data_dir: str, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    print(f"Processing input label: {input_label}")
    cleaned_data = remove_cc_blocked_site(input_label, meta_data_dir)
    output_path = os.path.join(output_dir, f"{input_label}.json")

    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(cleaned_data, file, indent=4, ensure_ascii=False)
    print(f"Processed and saved: {output_path}")

# Main processing
if __name__ == "__main__":
    config = load_config('config.yaml')
    meta_data_dir = config['output']['formated_directory']
    output_dir = config['output']['cleaned_directory']

    # Determine input labels
    if config['batch_processing']['enabled']:
        input_labels = config['batch_processing']['input_labels']
    else:
        input_labels = []
        input_labels.append(config['language_detector']['desired_language'])
    
    # Process and save cleaned data with tqdm
    for input_label in tqdm(input_labels, desc="Processing input labels"):
        process_files(input_label, meta_data_dir, output_dir)


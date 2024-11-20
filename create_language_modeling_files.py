import os
import yaml
import json
from typing import List, Dict, Any


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from a YAML file."""
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)


def load_crawled_output(code: str, data_dir: str) -> List[Dict[str, Any]]:
    """Load crawled output JSON for a given code."""
    file_path = os.path.join(data_dir, f"{code}_crawled_output.json")
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def load_robots_filtered_output(code: str, data_dir: str) -> Dict[str, Any]:
    """Load robots-filtered JSON for a given code."""
    file_path = os.path.join(data_dir, f"{code}.json")
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def get_full_list(robots_filtered_data: Dict[str, Any]) -> List[str]:
    """Extract the full list of allowed links."""
    full_list = []
    for site in robots_filtered_data['Sites']:
        full_list.extend(site['Links'])
    return full_list


def generate_text_file(
    code: str, 
    crawled_output_dir: str, 
    robots_filtered_output_dir: str, 
    text_files_output_dir: str
):
    """Generate a text file containing filtered and concatenated data."""
    # Load the required data
    crawled_data = load_crawled_output(code, crawled_output_dir)
    robots_filtered_data = load_robots_filtered_output(code, robots_filtered_output_dir)
    full_list = set(get_full_list(robots_filtered_data))  # Use a set for O(1) lookups

    # Collect matching text
    text_parts = [item['text'] for item in crawled_data if item['link'] in full_list]

    # Ensure the output directory exists
    os.makedirs(text_files_output_dir, exist_ok=True)

    # Save the concatenated string to a file
    output_file_path = os.path.join(text_files_output_dir, f"{code}.txt")
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write('\n'.join(text_parts))


def main():
    """Main function to execute the script."""
    # Load configuration
    config = load_config('config.yaml')
    robots_filtered_output_dir = config['output']['cleaned_directory']
    crawled_output_dir = config['output']['directory']
    text_files_output_dir = config['output']['text_files_directory']
    code = config['language_detector']['desired_language']

    # Determine input labels
    if config['batch_processing']['enabled']:
        input_labels = config['batch_processing']['input_labels']
    else:
        input_labels = [code]

    # Process each label
    for label in input_labels:
        generate_text_file(label, crawled_output_dir, robots_filtered_output_dir, text_files_output_dir)


if __name__ == "__main__":
    main()

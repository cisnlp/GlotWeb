import os
import yaml
import json
from typing import List, Dict, Any


def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)
    
def load_crawled_output(code, data_dir):
    file_name = os.path.join(data_dir, f"{code}_crawled_output.json")
    with open(file_name, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def load_robots_filtered_output(code, data_dir):
    file_name = os.path.join(data_dir, f"{code}.json")
    with open(file_name, 'r', encoding='utf-8') as file:
        return json.load(file)
    

def get_full_list(robots_filtered_data):
    full_list = []
    all_sites = robots_filtered_data['Sites']
    for item in all_sites:
        links = item['Links']
        full_list.extend(links)
    return full_list

import os

def generate_text_file(code, crawled_output_dir, robots_filtered_output_dir, text_files_output_dir):
    # Load the crawled data
    crawled_data = load_crawled_output(code, crawled_output_dir)
    # Load the robots-filtered data
    robots_filtered_data = load_robots_filtered_output(code, robots_filtered_output_dir)
    # Get the full list of allowed links
    full_list = get_full_list(robots_filtered_data)
    
    # Initialize an empty string to store concatenated text
    giant_string = ''
    for item in crawled_data:
        if item['link'] in full_list:
            # Append the text to the giant string with a newline
            giant_string += item['text'] + '\n'
    
    # Ensure the output directory exists
    os.makedirs(text_files_output_dir, exist_ok=True)
    
    # Define the output file path
    output_file_path = os.path.join(text_files_output_dir, f"{code}.txt")
    
    # Save the concatenated string to a text file
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(giant_string)



config = load_config('config.yaml')
robots_filtered_output_dir = config['output']['cleaned_directory']
crawled_output_dir = config['output']['directory']
text_files_output_dir = config['output']['text_files_directory']
code = config['language_detector']['desired_language']

if config['batch_processing']['enabled']:
    input_labels = []
    input_labels.append(config['batch_processing']['input_labels'])
else:
    input_labels = [config['language_detector']['desired_language']]

for label in input_labels:
    generate_text_file(label, crawled_output_dir, robots_filtered_output_dir, text_files_output_dir)



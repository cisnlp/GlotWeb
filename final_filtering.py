import yaml
import os
import re
import requests
from urllib.parse import urljoin, urlparse
import json
from typing import List, Dict, Any
from tqdm import tqdm

def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

config = load_config('config.yaml')

def remove_entries_with_domains(final_list):
        with open(config['domain_file'], 'r') as f:
            domains = [line.strip() for line in f.readlines()]

        filtered_list = [
            entry for entry in final_list 
            if 'link' in entry and not any(domain in entry['link'] for domain in domains)
        ]
        
        return filtered_list

def load_crawled_output(code: str, data_dir: str) -> List[Dict[str, Any]]:
    """Load crawled output JSON for a given code."""
    file_path = os.path.join(data_dir, f"{code}_crawled_output.json")
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def save_to_json(data: List[Dict[str, Any]], filename: str):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print(f"Successfully saved data to {filename}")
    except Exception as e:
        print(f"Error saving to {filename}: {e}")

def load_meta_data(code,data_dir):
    file_path = os.path.join(data_dir, f"{code}_meta_data.json")
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def filter_list_urls(urls, domain_filter):
    """
    Filter out URLs that match domains in the filter list.
     
    Args:
    urls (list): List of URLs to filter
    domain_filter (list): List of domains to filter out
     
    Returns:
    list: Filtered list of URLs
    """
    def should_filter(url):
        # Parse the URL to extract the domain
        parsed_url = urlparse(f'http://{url}')
         
        # Check if any filter domain matches the URL
        return any(
            filter_domain in parsed_url.netloc or 
            filter_domain in url 
            for filter_domain in domain_filter
        )
    
    # Correct return statement that filters the URLs
    return [url for url in urls if not should_filter(url)]

def filter_meta_data(meta_data):
    with open(config['domain_file'], 'r') as f:
            domains = [line.strip() for line in f.readlines()]
    meta_data['seed_urls'] = filter_list_urls(meta_data['seed_urls'],domains)
    meta_data['seed_urls_len'] = len(meta_data['seed_urls'])
    meta_data['all_website_links'] = filter_list_urls(meta_data['all_website_links'],domains)
    meta_data['all_website_links_len'] = len(meta_data['all_website_links'])
    meta_data['filtered_links'] = filter_list_urls(meta_data['filtered_links'],domains)
    meta_data['filtered_links_len'] = len(meta_data['filtered_links'])
    meta_data['unique_links'] = filter_list_urls(meta_data['unique_links'],domains)
    meta_data['unique_links_len'] = len(meta_data['unique_links'])
    meta_data['rejected_links'] = filter_list_urls(meta_data['rejected_links'],domains)
    meta_data['rejected_links_len'] = len(meta_data['rejected_links'])
    meta_data['active_seed_urls'] = list(set(meta_data['seed_urls'])-set(meta_data['rejected_links']))
    meta_data['active_seed_urls_len'] = len(meta_data['active_seed_urls'])

    return meta_data


    



def main():
    config = load_config('config.yaml')
    crawled_output_dir = config['output']['directory']
    code = config['language_detector']['desired_language']
    meta_data_dir = os.path.join(config['output']['directory'], "meta_data")

    # Determine input labels
    if config['batch_processing']['enabled']:
        input_labels = config['batch_processing']['input_labels']
    else:
        input_labels = [code]

    for input_label in tqdm(input_labels, desc="Processing input labels"):
        print(f"Processing {input_label}")
        data =  load_crawled_output(input_label,crawled_output_dir)
        data = remove_entries_with_domains(data)
        output_file = os.path.join(config['output']['directory'], 
                              config['output']['output_file_name'].format(language=input_label))
        save_to_json(data, output_file)

        meta_data = load_meta_data(input_label,meta_data_dir)
        meta_data = filter_meta_data(meta_data)
        meta_file_name = os.path.join(meta_data_dir, f"{input_label}_meta_data.json")
        with open(meta_file_name, 'w', encoding='utf-8') as file:
            json.dump(meta_data, file, ensure_ascii=False, indent=4)




if __name__ == "__main__":
    main()

import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
from typing import List, Dict, Any
from tqdm import tqdm
from trafilatura import extract, fetch_url
import fasttext
import urllib3
from concurrent.futures import ThreadPoolExecutor
import logging
import yaml

def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

config = load_config('config.yaml')

log_dir = os.path.dirname(config['logging']['file_path'])
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config['logging']['level']),
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=config['logging']['file_path']
)

class SeedReader:
    def __init__(self, json_file_path: str):
        self.json_file_path = json_file_path
        self.data = self.read_json_file()

    def read_json_file(self) -> List[Dict[str, Any]]:
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for item in data:
                    if not all(key in item for key in ["link", "lid_confidence", "predicted_lid"]):
                        raise ValueError("Missing one or more required keys: 'link', 'lid_confidence', or 'predicted_lid' in the JSON data")
                return data
        except FileNotFoundError:
            logging.error(f"File not found: {self.json_file_path}")
            return []
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from file: {self.json_file_path}")
            return []

    def get_data(self) -> List[Dict[str, Any]]:
        return self.data

    def get_entry_by_index(self, index: int) -> Dict[str, Any]:
        try:
            return self.data[index]
        except IndexError:
            logging.error(f"Index out of range: {index}")
            return {}

    def filter_by_key_value(self, key: str, value: Any) -> List[Dict[str, Any]]:
        if not self.data:
            logging.warning("No data available for filtering.")
            return []

        filtered_data = [entry for entry in self.data if entry.get(key) == value]
        
        if not filtered_data:
            logging.warning(f"No entries found with {key} = {value}")
        
        return filtered_data


class SeedCrawler:

    def __init__(self, seed_urls):
        self.seed_urls = seed_urls
        self.max_pages = config['seed_crawler']['max_pages']
        self.max_time = config['seed_crawler']['max_time']
        self.visited = set()
        self.to_visit = list(set(seed_urls))  # Remove duplicates
        self.to_visit_growth_factor = config['seed_crawler']['to_visit_growth_factor']
        self.all_links = set(seed_urls)  # Initialize with seed URLs
        self.session = requests.Session()

    def get_links(self, url):
        try:
            response = self.session.get(url, timeout=config['url_settings']['request_timeout'])
            response.raise_for_status()
        except (requests.RequestException, requests.HTTPError) as e:
            logging.error(f"Error fetching {url}: {e}")
            return set()

        links = set()
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logging.warning(f"Error parsing {url} with html.parser: {e}")
            try:
                soup = BeautifulSoup(response.text, 'lxml')
            except ImportError:
                logging.error("lxml parser not available. Unable to parse the page.")
                return set()
            except Exception as e:
                logging.error(f"Error parsing {url} with lxml: {e}")
                return set()

        for anchor in soup.find_all('a', href=True):
            link = urljoin(url, anchor['href'])
            parsed_link = urlparse(link)

            if any(parsed_link.netloc.endswith(urlparse(seed).netloc) for seed in self.seed_urls) and len(link) <= config['url_settings']['max_url_length']:
                links.add(link)

        return links

    def crawl_websites(self):
        logging.info(f"Crawling links from {len(self.seed_urls)} seed URLs")
        start_time = time.time()
        with tqdm(total=self.max_pages, disable=not config['progress_bar']['enabled']) as pbar:
            while self.to_visit and len(self.visited) < self.max_pages:
                if time.time() - start_time > self.max_time:
                    logging.info("Maximum crawl time reached. Stopping.")
                    break

                current_url = self.to_visit.pop(0)

                if current_url in self.visited:
                    continue

                links = self.get_links(current_url)
                self.all_links.update(links)

                for link in links:
                    if link not in self.visited and link not in self.to_visit:
                        self.to_visit.append(link)

                self.visited.add(current_url)
                time.sleep(config['seed_crawler']['crawl_delay'])
                pbar.update(1)

                if len(self.visited) % 10 == 0:
                    if len(self.to_visit) > len(self.visited) * self.to_visit_growth_factor:
                        logging.warning("To-visit list growing too fast. Possible circular link structure.")
                        break

        logging.info(f"Finished crawling links from {len(self.seed_urls)} seed URLs")
        logging.info(f"Visited {len(self.visited)} pages in {time.time() - start_time:.2f} seconds")
        return self.all_links
    
class LanguageDetector:
    def __init__(self, model):
        self.model = model

    @staticmethod
    def extract_language_code(input_str):
        pattern = r'__(label)__([a-zA-Z]+_[a-zA-Z]+)'
        match = re.search(pattern, input_str)
        return match.group(2) if match else None

    @staticmethod
    def trafilatura_scrape(url):
        document = fetch_url(url)
        return extract(document)

    def language_predict(self, scraped_text):
        if scraped_text is not None:
            lid_label_script = self.model.predict(scraped_text.replace('\n', ''))
            lid_label = self.extract_language_code(lid_label_script[0][0])
            lid_confidence = lid_label_script[1][0]
            return lid_label, lid_confidence
        return None, None

    def filter_seeds(self, links, input_label, confidence):
        new_list = []
        logging.info(f"Starting to filter {len(links)} links")

        with ThreadPoolExecutor(max_workers=config['seed_crawler']['max_workers']) as executor:
            futures = [executor.submit(self.process_link, link, input_label, confidence) for link in links]
            for future in tqdm(futures, desc="Filtering scraped links", unit="link", disable=not config['progress_bar']['enabled']):
                try:
                    result = future.result()
                    if result:
                        new_list.append(result)
                        logging.debug(f"Appended result: {result}")
                except Exception as e:
                    logging.error(f"Error processing link: {e}")

        logging.info(f"Finished filtering. Found {len(new_list)} matching links")
        return new_list

    def process_link(self, link, input_label, confidence):
        try:
            scraped_text = self.trafilatura_scrape(link)
            lid_label, lid_confidence = self.language_predict(scraped_text)
            
            logging.debug(f"Link: {link}, LID Label: {lid_label}, LID Confidence: {lid_confidence}")
            
            if lid_label == input_label and lid_confidence >= confidence:
                if config['language_detector']['save_text'] == True:
                    return {"link": link, "lid_label": lid_label, "lid_confidence": lid_confidence, "text": scraped_text}  
                else:  
                    return {"link": link, "lid_label": lid_label, "lid_confidence": lid_confidence}
        except Exception as e:
            logging.error(f"Error processing link {link}: {e}")
        return None

def remove_entries_with_domains(final_list):
        with open(config['domain_file'], 'r') as f:
            domains = [line.strip() for line in f.readlines()]

        filtered_list = [
            entry for entry in final_list 
            if 'link' in entry and not any(domain in entry['link'] for domain in domains)
        ]
        
        return filtered_list

def save_to_json(data: List[Dict[str, Any]], filename: str):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        logging.info(f"Successfully saved data to {filename}")
        print(f"Successfully saved data to {filename}")
    except Exception as e:
        logging.error(f"Error saving to {filename}: {e}")

def process_language(input_label: str, model: fasttext.FastText._FastText) -> None:
    """Process a single language input."""
    json_file_path = os.path.join(config['seed_reader']['input_directory'], f"{input_label}.json")
    input_confidence = config['language_detector']['minimum_confidence']
    
    logging.info(f"Processing language: {input_label}")
    print(f"Processing language: {input_label}")
    
    reader = SeedReader(json_file_path)
    all_data = reader.get_data()

    all_data = remove_entries_with_domains(all_data)

    links_meta_data = {}

    seed_urls = [entry['link'] for entry in all_data if entry['lid_confidence'] > input_confidence]

    links_meta_data['seed_urls'] = seed_urls
    links_meta_data['seed_urls_len'] = len(seed_urls)
    
    if not seed_urls:
        logging.warning(f"No seed URLs found for language {input_label}")
        return
    
    crawler = SeedCrawler(seed_urls)
    all_website_links = crawler.crawl_websites()

    links_meta_data['all_website_links'] = list(all_website_links)  # Convert set to list for JSON serialization
    links_meta_data['all_website_links_len'] = len(all_website_links)

    lang_detector = LanguageDetector(model)
    filtered_links = lang_detector.filter_seeds(all_website_links, input_label, input_confidence)

    links_meta_data['filtered_links'] = [link['link'] for link in filtered_links]
    links_meta_data['filtered_links_len'] = len(filtered_links)

    unique_links = set_minus([link['link'] for link in filtered_links], seed_urls)  # Extract links from filtered_links
    links_meta_data['unique_links'] = unique_links
    links_meta_data['unique_links_len'] = len(unique_links)

    rejected_links = set_minus(seed_urls, [link['link'] for link in filtered_links])
    links_meta_data['rejected_links'] = rejected_links
    links_meta_data['rejected_links_len'] = len(rejected_links)

    # Create metadata directory if it doesn't exist
    meta_data_dir = os.path.join(config['output']['directory'], "meta_data")
    os.makedirs(meta_data_dir, exist_ok=True)

    # Construct the filename correctly
    meta_file_name = os.path.join(meta_data_dir, f"{input_label}_meta_data.json")

    try:
        # Open and save data to JSON
        with open(meta_file_name, 'w', encoding='utf-8') as file:
            json.dump(links_meta_data, file, ensure_ascii=False, indent=4)
        logging.info(f"Successfully saved metadata to {meta_file_name}")
    except Exception as e:
        logging.error(f"Error saving metadata to {meta_file_name}: {e}")

    logging.info(f"Number of filtered links for {input_label}: {len(filtered_links)}")

    output_file = os.path.join(config['output']['directory'], 
                              config['output']['output_file_name'].format(language=input_label))
    save_to_json(filtered_links, output_file)

    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        logging.info(f"Output file size for {input_label}: {file_size} bytes")
    else:
        logging.error(f"Output file was not created for {input_label}")

def set_minus(list1, list2):
    
    set1 = set(list1)
    set2 = set(list2)
    
    uncommon_elements = set1 - set2
    
    return list(uncommon_elements)

def batch_process(input_labels: List[str]) -> None:
    """Process multiple languages in batch."""
    model_path = config['language_detector']['model_path']
    model = fasttext.load_model(model_path)
    
    total_languages = len(input_labels)
    logging.info(f"Starting batch processing for {total_languages} languages")
    print(f"Starting batch processing for {total_languages} languages")
    
    for idx, input_label in enumerate(input_labels, 1):
        logging.info(f"Processing language {idx}/{total_languages}: {input_label}")
        print(f"Processing language {idx}/{total_languages}: {input_label}")
        try:
            process_language(input_label, model)
        except Exception as e:
            logging.error(f"Error processing language {input_label}: {e}")
            continue
        
        if idx < total_languages:
            cooldown = config.get('batch_processing', {}).get('cooldown_between_languages', 60)
            logging.info(f"Cooling down for {cooldown} seconds before processing next language")
            print(f"Cooling down for {cooldown} seconds before processing next language")
            time.sleep(cooldown)
    
    logging.info("Batch processing completed")
    print("Batch processing completed")

if __name__ == "__main__":
    # Check if batch processing is enabled in config
    if config.get('batch_processing', {}).get('enabled', False):
        input_labels = config['batch_processing']['input_labels']
        if not input_labels:
            logging.error("Batch processing enabled but no input labels provided in config")
        else:
            batch_process(input_labels)
    else:
        # Original single language processing
        input_label = config['language_detector']['desired_language']
        model_path = config['language_detector']['model_path']
        model = fasttext.load_model(model_path)
        process_language(input_label, model)
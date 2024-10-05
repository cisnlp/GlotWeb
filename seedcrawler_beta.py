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

# Create the directory for the log file if it doesn't exist
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
                    if not all(key in item for key in ["snippet", "title", "link", "engines", 
                                                       "category", "predicted_lid", "lid_confidence"]):
                        raise ValueError("Missing one or more required keys in the JSON data")
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
    def __init__(self, seed_url):
        self.seed_url = seed_url
        self.max_pages = config['seed_crawler']['max_pages']
        self.max_time = config['seed_crawler']['max_time']
        self.domain = urlparse(seed_url).netloc
        self.visited = set()
        self.to_visit = [seed_url]
        self.all_links = set()
        self.session = requests.Session()

    def get_links(self, url):
        try:
            response = self.session.get(url, timeout=config['url_settings']['request_timeout'])
            response.raise_for_status()
        except (requests.RequestException, requests.HTTPError) as e:
            logging.error(f"Error fetching {url}: {e}")
            return set()

        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()

        for anchor in soup.find_all('a', href=True):
            link = urljoin(url, anchor['href'])
            parsed_link = urlparse(link)

            if parsed_link.netloc.endswith(self.domain) and len(link) <= config['url_settings']['max_url_length']:
                links.add(link)

        return links

    def crawl_website(self):
        logging.info(f"Crawling links from: {self.seed_url}")
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

                # Check if we're making progress
                if len(self.visited) % 10 == 0:  # Check every 10 pages
                    if len(self.to_visit) > len(self.visited) * 10:
                        logging.warning("To-visit list growing too fast. Possible circular link structure.")
                        break

        logging.info(f"Finished crawling links from: {self.seed_url}")
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
                return {"link": link, "lid_label": lid_label, "lid_confidence": lid_confidence}
        except Exception as e:
            logging.error(f"Error processing link {link}: {e}")
        return None

def save_to_json(data: List[Dict[str, Any]], filename: str):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        logging.info(f"Successfully saved data to {filename}")
    except Exception as e:
        logging.error(f"Error saving to {filename}: {e}")

if __name__ == "__main__":
    input_label = config['language_detector']['desired_language']
    json_file_path = os.path.join(config['seed_reader']['input_directory'], f"{input_label}.json")
    input_confidence = config['language_detector']['minimum_confidence']
    model_path = config['language_detector']['model_path']
    
    model = fasttext.load_model(model_path)
    
    reader = SeedReader(json_file_path)
    all_data = reader.get_data()

    final_list = []
    lang_detector = LanguageDetector(model)
    
    for entry in all_data:
        if entry['lid_confidence'] > input_confidence:
            seed_url = entry['link']
            crawler = SeedCrawler(seed_url)
            all_website_links = crawler.crawl_website()

            save_to_json(list(all_website_links), os.path.join(config['output']['directory'], f"{input_label}_links_before_filter.json"))

            filtered_links = lang_detector.filter_seeds(all_website_links, input_label, input_confidence)
            logging.info(f"Number of filtered links: {len(filtered_links)}")
            logging.debug(f"Sample of filtered links: {filtered_links[:5]}")

            save_to_json(filtered_links, os.path.join(config['output']['directory'], f"{input_label}_links_after_filter.json"))

            final_list.extend(filtered_links)

    output_file = os.path.join(config['output']['directory'], config['output']['output_file_name'].format(language=input_label))
    save_to_json(final_list, output_file)

    logging.info(f"Final list saved. Total links: {len(final_list)}")

    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        logging.info(f"Output file size: {file_size} bytes")
    else:
        logging.error("Output file was not created")
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
from typing import List, Dict, Any, Set
from tqdm import tqdm
from trafilatura import extract, fetch_url
import fasttext
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import yaml
import aiohttp
import asyncio
from cachetools import TTLCache
from functools import lru_cache
import urllib3

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
                    if not all(key in item for key in ["link", "lid_confidence", "lid_label"]):
                        raise ValueError("Missing one or more required keys: 'link', 'lid_confidence', or 'lid_label' in the JSON data")
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

class OptimizedSeedCrawler:
    def __init__(self, seed_urls):
        self.seed_urls = seed_urls
        self.max_pages = config['seed_crawler']['max_pages']
        self.max_time = config['seed_crawler']['max_time']
        self.visited = set()
        self.to_visit = set(seed_urls)  # Using set for O(1) lookup
        self.all_links = set(seed_urls)
        self.url_cache = TTLCache(maxsize=1000, ttl=3600)  # Cache URLs for 1 hour
        
    async def get_links(self, url: str, session: aiohttp.ClientSession) -> Set[str]:
        if url in self.url_cache:
            return self.url_cache[url]
            
        try:
            async with session.get(url, timeout=config['url_settings']['request_timeout']) as response:
                if response.status != 200:
                    return set()
                html = await response.text()
                
                soup = BeautifulSoup(html, 'lxml')  # Using lxml parser for better performance
                links = {
                    urljoin(url, anchor['href'])
                    for anchor in soup.find_all('a', href=True)
                    if self._is_valid_link(anchor['href'], url)
                }
                
                self.url_cache[url] = links
                return links
                
        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            return set()

    @lru_cache(maxsize=1000)
    def _is_valid_link(self, href: str, base_url: str) -> bool:
        link = urljoin(base_url, href)
        parsed_link = urlparse(link)
        return (
            any(parsed_link.netloc.endswith(urlparse(seed).netloc) for seed in self.seed_urls)
            and len(link) <= config['url_settings']['max_url_length']
        )

    async def crawl_websites(self):
        async with aiohttp.ClientSession() as session:
            tasks = []
            start_time = time.time()
            
            with tqdm(total=self.max_pages, disable=not config['progress_bar']['enabled']) as pbar:
                while self.to_visit and len(self.visited) < self.max_pages:
                    if time.time() - start_time > self.max_time:
                        break

                    # Process URLs in batches
                    batch_size = min(50, len(self.to_visit))
                    current_batch = set(list(self.to_visit)[:batch_size])
                    self.to_visit -= current_batch
                    
                    new_tasks = [self.get_links(url, session) for url in current_batch]
                    batch_results = await asyncio.gather(*new_tasks)
                    
                    for url, links in zip(current_batch, batch_results):
                        self.all_links.update(links)
                        self.visited.add(url)
                        self.to_visit.update(links - self.visited)
                        pbar.update(1)

            return self.all_links

class OptimizedLanguageDetector:
    def __init__(self, model):
        self.model = model
        self.text_cache = TTLCache(maxsize=1000, ttl=3600)
        
    @lru_cache(maxsize=1000)
    def extract_language_code(self, input_str):
        pattern = r'__(label)__([a-zA-Z]+_[a-zA-Z]+)'
        match = re.search(pattern, input_str)
        return match.group(2) if match else None

    def language_predict(self, scraped_text):
        if scraped_text is not None:
            lid_label_script = self.model.predict(scraped_text.replace('\n', ''))
            lid_label = self.extract_language_code(lid_label_script[0][0])
            lid_confidence = lid_label_script[1][0]
            return lid_label, lid_confidence
        return None, None

    async def trafilatura_scrape(self, url: str, session: aiohttp.ClientSession):
        try:
            if url in self.text_cache:
                return self.text_cache[url]
                
            async with session.get(url) as response:
                html = await response.text()
                text = extract(html)
                if text:
                    self.text_cache[url] = text
                return text
        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")
            return None

    async def process_link_async(self, link: str, input_label: str, confidence: float, session: aiohttp.ClientSession):
        try:
            scraped_text = await self.trafilatura_scrape(link, session)
            if scraped_text:
                lid_label, lid_confidence = self.language_predict(scraped_text)
                
                if lid_label == input_label and lid_confidence >= confidence:
                    return {
                        "link": link,
                        "lid_label": lid_label,
                        "lid_confidence": lid_confidence,
                        "text": "" if config['language_detector']['save_text'] else None
                    }
        except Exception as e:
            logging.error(f"Error processing link {link}: {e}")
        return None

    async def filter_seeds_async(self, links: List[str], input_label: str, confidence: float):
        new_list = []
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.process_link_async(link, input_label, confidence, session)
                for link in links
            ]
            
            for result in tqdm(
                asyncio.as_completed(tasks),
                total=len(tasks),
                desc="Filtering scraped links",
                disable=not config['progress_bar']['enabled']
            ):
                try:
                    processed = await result
                    if processed:
                        new_list.append(processed)
                except Exception as e:
                    logging.error(f"Error in filter_seeds_async: {e}")
                    
        return new_list

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

def set_minus(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    uncommon_elements = set1 - set2
    return list(uncommon_elements)

async def process_language_async(input_label: str, model: fasttext.FastText._FastText) -> None:
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
    
    crawler = OptimizedSeedCrawler(seed_urls)
    all_website_links = await crawler.crawl_websites()

    links_meta_data['all_website_links'] = list(all_website_links)
    links_meta_data['all_website_links_len'] = len(all_website_links)

    lang_detector = OptimizedLanguageDetector(model)
    filtered_links = await lang_detector.filter_seeds_async(all_website_links, input_label, input_confidence)

    links_meta_data['filtered_links'] = [link['link'] for link in filtered_links]
    links_meta_data['filtered_links_len'] = len(filtered_links)

    unique_links = set_minus([link['link'] for link in filtered_links], seed_urls)
    links_meta_data['unique_links'] = list(unique_links)
    links_meta_data['unique_links_len'] = len(unique_links)

    rejected_links = set_minus(seed_urls, [link['link'] for link in filtered_links])
    links_meta_data['rejected_links'] = list(rejected_links)
    links_meta_data['rejected_links_len'] = len(rejected_links)

    meta_data_dir = os.path.join(config['output']['directory'], "meta_data")
    os.makedirs(meta_data_dir, exist_ok=True)

    meta_file_name = os.path.join(meta_data_dir, f"{input_label}_meta_data.json")
    
    try:
        with open(meta_file_name, 'w', encoding='utf-8') as file:
            json.dump(links_meta_data, file, ensure_ascii=False, indent=4)
        logging.info(f"Successfully saved metadata to {meta_file_name}")
    except Exception as e:
        logging.error(f"Error saving metadata to {meta_file_name}: {e}")

    output_file = os.path.join(config['output']['directory'], 
                              config['output']['output_file_name'].format(language=input_label))
    save_to_json(filtered_links, output_file)

async def batch_process_async(input_labels: List[str]) -> None:
    model_path = config['language_detector']['model_path']
    model = fasttext.load_model(model_path)
    
    total_languages = len(input_labels)
    logging.info(f"Starting batch processing for {total_languages} languages")
    print(f"Starting batch processing for {total_languages} languages")
    
    for idx, input_label in enumerate(input_labels, 1):
        logging.info(f"Processing language {idx}/{total_languages}: {input_label}")
        print(f"Processing language {idx}/{total_languages}: {input_label}")
        try:
            await process_language_async(input_label, model)
        except Exception as e:
            logging.error(f"Error processing language {input_label}: {e}")
            continue
            
        if idx < total_languages:
            cooldown = config.get('batch_processing', {}).get('cooldown_between_languages', 60)
            logging.info(f"Cooling down for {cooldown} seconds before processing next language")
            print(f"Cooling down for {cooldown} seconds before processing next language")
            await asyncio.sleep(cooldown)
    
    logging.info("Batch processing completed")
    print("Batch processing completed")

if __name__ == "__main__":
    if config.get('batch_processing', {}).get('enabled', False):
        input_labels = config['batch_processing']['input_labels']
        if not input_labels:
            logging.error("Batch processing enabled but no input labels provided in config")
        else:
            asyncio.run(batch_process_async(input_labels))
    else:
        input_label = config['language_detector']['desired_language']
        model_path = config['language_detector']['model_path']
        model = fasttext.load_model(model_path)
        asyncio.run(process_language_async(input_label, model))

# if __name__ == "__main__":
#     import nest_asyncio
#     nest_asyncio.apply()
    
#     if config.get('batch_processing', {}).get('enabled', False):
#         input_labels = config['batch_processing']['input_labels']
#         if not input_labels:
#             logging.error("Batch processing enabled but no input labels provided in config")
#         else:
#             asyncio.run(batch_process_async(input_labels))
#     else:
#         input_label = config['language_detector']['desired_language']
#         model_path = config['language_detector']['model_path']
#         model = fasttext.load_model(model_path)
#         asyncio.run(process_language_async(input_label, model))
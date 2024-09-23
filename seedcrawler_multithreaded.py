import os
import re
import requests
import yaml
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
from typing import List, Dict, Any
from tqdm import tqdm
from trafilatura import extract, fetch_url
import fasttext
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load YAML configuration
with open('config.yaml', 'r') as config_file:
    config = yaml.safe_load(config_file)

# Extract configuration settings
seed_reader_config = config['seed_reader']
seed_crawler_config = config['seed_crawler']
language_detector_config = config['language_detector']
output_config = config['output']
logging_config = config['logging']
progress_bar_config = config['progress_bar']
executor_config = config['executor']
url_settings = config['url_settings']
domain_file = config['domain_file']
# Increase max URL length if needed
urllib3.util.url.MAX_URL_LENGTH = url_settings['max_url_length']

class SeedReader:
    def __init__(self, json_file_path: str):
        """
        Initializes the SeedReader with the path to a JSON file.
        
        :param json_file_path: The path to the JSON file containing the data.
        """
        self.json_file_path = json_file_path
        self.data = self.read_json_file()

    def read_json_file(self) -> List[Dict[str, Any]]:
        """
        Reads the JSON file and returns a list of dictionaries containing the data.

        :return: A list of dictionaries with keys: "snippet", "title", "link", "engines",
                 "category", "predicted_lid", "lid_confidence".
        """
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                # Validate that each item in the list is a dictionary with required keys
                for item in data:
                    if not all(key in item for key in ["snippet", "title", "link", "engines", 
                                                       "category", "predicted_lid", "lid_confidence"]):
                        raise ValueError("Missing one or more required keys in the JSON data")
                return data
        except FileNotFoundError:
            print(f"File not found: {self.json_file_path}")
            return []
        except json.JSONDecodeError:
            print(f"Error decoding JSON from file: {self.json_file_path}")
            return []

    def get_data(self) -> List[Dict[str, Any]]:
        """
        Returns the list of dictionaries containing the data.
        
        :return: List of data entries as dictionaries.
        """
        return self.data

    def get_entry_by_index(self, index: int) -> Dict[str, Any]:
        """
        Returns a specific entry by its index in the data list.

        :param index: The index of the entry to retrieve.
        :return: A dictionary representing the entry at the specified index.
        :raises IndexError: If the index is out of range.
        """
        try:
            return self.data[index]
        except IndexError:
            print(f"Index out of range: {index}")
            return {}

    def filter_by_key_value(self, key: str, value: Any) -> List[Dict[str, Any]]:
        """
        Filters the data based on a specified key-value pair.

        :param key: The key to filter by.
        :param value: The value to match.
        :return: A list of dictionaries where the specified key has the given value.
        """
        if not self.data:
            print("No data available for filtering.")
            return []

        filtered_data = [entry for entry in self.data if entry.get(key) == value]
        
        if not filtered_data:
            print(f"No entries found with {key} = {value}")
        
        return filtered_data
    
    def remove_entries_with_domains(self, final_list):
        with open(domain_file, 'r') as f:
            domains = [line.strip() for line in f.readlines()]

        # Filter the final_list
        filtered_list = [
            entry for entry in final_list 
            if 'link' in entry and not any(domain in entry['link'] for domain in domains)
        ]
        
        return filtered_list


class SeedCrawler:
    def __init__(self, seed_url, max_pages=seed_crawler_config['max_pages']):
        """
        Initializes the SeedCrawler with a seed URL and maximum pages to crawl.
        
        :param seed_url: The URL to start crawling from.
        :param max_pages: The maximum number of pages to crawl.
        """
        self.seed_url = seed_url
        self.max_pages = max_pages
        self.domain = urlparse(seed_url).netloc  # Extract domain from seed URL
        self.visited = set()
        self.to_visit = [seed_url]
        self.all_links = set()

    def get_links(self, url):
        """
        Fetches all links from a webpage belonging to the specified domain.

        :param url: The URL of the webpage to fetch links from.
        :return: A set of links belonging to the specified domain.
        """
        try:
            response = requests.get(url, timeout=url_settings['request_timeout'])
            response.raise_for_status()  # Raise an error for bad responses
        except (requests.RequestException, requests.HTTPError) as e:
            print(f"Error fetching {url}: {e}")
            return set()

        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()

        # Find all anchor tags with href attributes
        for anchor in soup.find_all('a', href=True):
            # Resolve relative URLs
            link = urljoin(url, anchor['href'])
            # Parse the URL to check its domain
            parsed_link = urlparse(link)

            # Check if the link belongs to the specified domain
            if parsed_link.netloc.endswith(self.domain):
                links.add(link)

        return links

    def crawl_website(self):
        """
        Crawls the entire website starting from the seed URL.

        :return: A set of all found links belonging to the specified domain.
        """
        print(f"Crawling links from: {self.seed_url}")
        with ThreadPoolExecutor(max_workers=seed_crawler_config['max_workers']) as executor:
            futures = {}
            
            while self.to_visit and len(self.visited) < self.max_pages:
                current_url = self.to_visit.pop(0)
                
                if current_url in self.visited:
                    continue
                
                future = executor.submit(self.get_links, current_url)
                futures[future] = current_url
                
                # Sleep after submitting the request to be polite
                time.sleep(seed_crawler_config['crawl_delay'])

            for future in as_completed(futures):
                current_url = futures[future]
                try:
                    links = future.result()
                    self.all_links.update(links)
                    
                    # Add new links to the to_visit list
                    for link in links:
                        if link not in self.visited and link not in self.to_visit:
                            self.to_visit.append(link)
                    
                    self.visited.add(current_url)
                except Exception as e:
                    print(f"Exception occurred while crawling {current_url}: {e}")

        print(f"Finished crawling links from: {self.seed_url}")
        return self.all_links


class LanguageDetector:
    def __init__(self, model):
        """
        Initialize the LanguageDetector class with a FastText model.

        Args:
            model: The loaded FastText model.
        """
        self.model = model  # Store the model reference instead of loading again.

    @staticmethod
    def extract_language_code(input_str):
        """
        Extract the language code from a FastText prediction string.

        Args:
            input_str (str): The input prediction string from FastText.

        Returns:
            str or None: Extracted language code or None if not found.
        """
        pattern = r'__(label)__([a-zA-Z]+_[a-zA-Z]+)'
        match = re.search(pattern, input_str)
        if match:
            return match.group(2)
        else:
            return None

    @staticmethod
    def trafilatura_scrape(url):
        """
        Scrape text content from a given URL using Trafilatura.

        Args:
            url (str): The URL to scrape.

        Returns:
            str: Extracted text content from the URL.
        """
        document = fetch_url(url)
        text = extract(document)
        return text

    def language_predict(self, scraped_text):
        """
        Predict the language of the given text using the FastText model.

        Args:
            scraped_text (str): The text content to predict language for.

        Returns:
            tuple: (language label, confidence score) or (None, None) if text is empty.
        """
        if scraped_text is not None:
            lid_label_script = self.model.predict(scraped_text.replace('\n', ''))
            lid_label = self.extract_language_code(lid_label_script[0][0])
            lid_confidence = lid_label_script[1][0]
            return lid_label, lid_confidence
        return None, None

    def filter_seeds(self, links, input_label, confidence):
        """
        Filter URLs based on language prediction and confidence score.

        Args:
            links (list): List of URLs to filter.
            input_label (str): The desired language label.
            confidence (float): The minimum confidence score required.

        Returns:
            list: Filtered list of URLs matching the language criteria.
        """
        new_list = []

        def filter_link(link):
            scraped_text = self.trafilatura_scrape(link)
            lid_label, lid_confidence = self.language_predict(scraped_text)
            if (lid_label == input_label) and (lid_confidence >= confidence):
                return {
                    "link": link,
                    "lid_label": lid_label,
                    "lid_confidence": lid_confidence,
                    "scraped_text": scraped_text  # Add scraped text to the dictionary
        }
            return None 


        with ThreadPoolExecutor(max_workers=seed_crawler_config['max_workers']) as executor:
            futures = {executor.submit(filter_link, link): link for link in links}
            
            # Use tqdm to add a progress bar to the loop
            for future in tqdm(as_completed(futures), desc="Filtering scraped links", unit="link", total=len(futures)):
                result = future.result()
                if result:
                    new_list.append(result)

        return new_list


# Example usage
if __name__ == "__main__":
    input_label = language_detector_config['desired_language']  # Replace with your JSON file name
    json_file_path = os.path.join(seed_reader_config['input_directory'], seed_reader_config['json_file_name'])
    input_confidence = language_detector_config['minimum_confidence']
    model_path = language_detector_config['model_path']
    
    # Load the model once
    model = fasttext.load_model(model_path)
    
    reader = SeedReader(json_file_path)

    all_data = reader.get_data()

    final_list = []
    lang_detector = LanguageDetector(model)  # Initialize once and reuse
    
    with ThreadPoolExecutor(max_workers=executor_config['max_workers_reader']) as executor:
        futures = []

        for entry in all_data:
            # If confidence level threshold condition met.
            # Initialize a big list of websites and put the seed in it.
            
            if entry['lid_confidence'] > input_confidence:
                seed_url = entry['link']
                crawler = SeedCrawler(seed_url, max_pages=seed_crawler_config['max_pages'])
                futures.append(executor.submit(crawler.crawl_website))

        for future in as_completed(futures):
            all_website_links = future.result()
            # Use the same LanguageDetector instance
            filtered_links = lang_detector.filter_seeds(all_website_links, input_label, input_confidence)
            final_list.extend(filtered_links)
            print(filtered_links)



    # Create directory if it doesn't exist
    output_dir = output_config['directory']
    os.makedirs(output_dir, exist_ok=True)

    noise = {"link":"http://aboriginalbibles.org.au/this/is/a_test.html",
                       "lid_label": "urd_Latn",
                        "lid_confidence": 0.946052610874176,
                        "scraped_text":"blah blah"}
    ### Noise injection for testing
    final_list.append(noise)

    # Save the final list as a JSON file
    # Save the final list as a JSON file
    ### Saving with the noise
    output_file = os.path.join(output_dir, output_config['output_file_name'].format(language=input_label))

    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(final_list, file, ensure_ascii=False, indent=4)
    
    print(f"Final list saved to {output_file}")

    filtered_final_list = reader.remove_entries_with_domains(final_list)

    # Save the filtered final list as a JSON file
    output_filtered_file = os.path.join(output_dir, 'filtered_' + output_config['output_file_name'].format(language=input_label))

    with open(output_filtered_file, 'w', encoding='utf-8') as file:
        json.dump(filtered_final_list, file, ensure_ascii=False, indent=4)

    print(f"Filtered final list saved to {output_filtered_file}")

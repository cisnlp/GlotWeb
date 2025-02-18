import os
import re
import json
import fasttext
from trafilatura import extract, fetch_url
import urllib3
from tqdm import tqdm
import yaml

class LanguageFilter:
    def __init__(self, config_file):
        self.load_config(config_file)
        self.model = self.load_model()
    
    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)
    
    def load_model(self):
        model_path = self.config['model_path']  # Use the local model path from the config
        return fasttext.load_model(model_path)

    def remove_entries_with_domains(self, json_data):
        with open(self.config['domain_file'], 'r') as f:
            domains = [line.strip() for line in f.readlines()]
        
        for iso_key, entries in json_data.items():
            json_data[iso_key] = [entry for entry in entries if 'link' in entry and not any(domain in entry['link'] for domain in domains)]
        
        return json_data

    def extract_language_code(self, input_str):
        pattern = r'__(label)__([a-zA-Z]+_[a-zA-Z]+)'
        match = re.search(pattern, input_str)
        if match:
            return match.group(2)
        else:
            return None

    def trafilatura_scrape(self, url):
        document = fetch_url(url)
        text = extract(document)
        return text

    def scraped_lang_filter(self, filtered_data, iso_list):
        scraped_lang_list = []
        output_directory = self.config['output_directory']
        
        for key in tqdm(filtered_data, desc="Processing"):
            entry = filtered_data[key]
            for item in entry:
                link = item['link']
                scraped_text = self.trafilatura_scrape(link)
                
                if scraped_text is not None:
                    lid_label_script = self.model.predict(scraped_text.replace('\n', ''))
                    lid_label = self.extract_language_code(lid_label_script[0][0])
                    lid_confidence = lid_label_script[1][0]
                    item['predicted_lid'] = lid_label
                    item['lid_confidence'] = lid_confidence

                    if lid_label not in iso_list:
                        output_file_path = os.path.join(output_directory, f'{lid_label}.json')
                        if os.path.exists(output_file_path):
                            with open(output_file_path, 'r') as output_file:
                                existing_data = json.load(output_file)
                        else:
                            existing_data = []

                        scraped_lang_list.append(lid_label)
                        existing_data.append(item)
                        
                        with open(output_file_path, 'w') as output_file:
                            json.dump(existing_data, output_file, ensure_ascii=False, indent=4)

        print(scraped_lang_list)
        print(len(scraped_lang_list))

    def run(self):
        # Load the JSON dump of web search
        with open(self.config['json_filename'], 'r') as json_file:
            data = json.load(json_file)

        # Load ISO code list
        with open(self.config['iso_list_file'], 'r') as f:
            iso_list = json.load(f)
        
        # Filter the search results using the domain list
        filtered_data = self.remove_entries_with_domains(data)
        
        # Perform the language filter and scraping
        self.scraped_lang_filter(filtered_data, iso_list)
        
        print("DONE ALL")

if __name__ == "__main__":
    config_file = "filter_config.yaml"
    filter_instance = LanguageFilter(config_file)
    filter_instance.run()

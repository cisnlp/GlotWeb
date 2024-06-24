#IMPORTS

import os
import re
import json
from trafilatura import extract
from trafilatura import fetch_url
import fasttext
from huggingface_hub import hf_hub_download
import urllib3
import time
from tqdm import tqdm

#FUNCTIONS

def remove_entries_with_domains(json_data, domain_file):
    with open(domain_file, 'r') as f:
        domains = [line.strip() for line in f.readlines()]

    for iso_key, entries in json_data.items():
        json_data[iso_key] = [entry for entry in entries if 'link' in entry and not any(domain in entry['link'] for domain in domains)]

    return json_data


def extract_language_code(input_str):
    pattern = r'__(label)__([a-zA-Z]+_[a-zA-Z]+)'
    match = re.search(pattern, input_str)
    if match:
        return match.group(2)
    else:
        return None

def trafilatura_scrape(url):
  document = fetch_url(url)
  text = extract(document)

  return text

def scraped_lang_filter(filtered_data, model, iso_list, output_directory):

    scraped_lang_list = []
    for key in tqdm(filtered_data, desc = "Processing"):
        entries = filtered_data[key]
        for entry in entries:
          new_entry = []
          for item in entry:
            link = item['link']
            scraped_text = trafilatura_scrape(link)
            if scraped_text is not None:

              lid_label_script = model.predict(scraped_text.replace('\n', ''))
              lid_label = extract_language_code(lid_label_script[0][0])
              lid_confidence = lid_label_script[1][0]
              item['predicted_lid'] = lid_label
              item['lid_confidence'] = lid_confidence

              if lid_label not in iso_list:
                output_file_path = os.path.join(output_directory, f'{lid_label}.json')
                if os.path.exists(output_file_path):
                  # If it exists, read the existing content
                  with open(output_file_path, 'r') as output_file:
                      existing_data = json.load(output_file)
                else:
                  # If it doesn't exist, create a new list
                  existing_data = []

                print(lid_confidence) # Add this line for debugging
                print("lid_label:", lid_label)  # Add this line for debugging
                scraped_lang_list.append(lid_label) # Add this line for debugging
                existing_data.append(item)
                with open(output_file_path, 'w') as output_file:
                  json.dump(existing_data, output_file, ensure_ascii = False, indent=4)

    print(scraped_lang_list)      # Add this line for debugging
    print(len(scraped_lang_list)) # Add this line for debugging
    return None

#Execution

start_time = time.time()

model_path = hf_hub_download(repo_id="cis-lmu/glotlid", filename="model.bin")
model = fasttext.load_model(model_path)

filename = '0-200.json'
### Load Json dump of web search.
with open(filename, 'r') as json_file:
    data = json.load(json_file)
### ISO code list of top 200 languages
with open('iso_list.json', 'r') as f:
    iso_list = json.load(f)

### Filter searches using filterlist.txt
filtered_data = remove_entries_with_domains(data, 'filterlist.txt')
#scraped_lang_filtered_data = scraped_lang_filter(filtered_data, model, iso_list)

urllib3.disable_warnings()
output_directory = '/content/drive/MyDrive/glotsparse/glosslm_dump/lang_dump_confidence'
scraped_lang_filtered_data = scraped_lang_filter(filtered_data, model, iso_list, output_directory)
filepath = f"{filename}_filtered.json"

print("DONE ALL")
print(filename)
end_time = time.time()
time_min = (end_time - start_time)/60
print(time_min)

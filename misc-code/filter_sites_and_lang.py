#import dependencies
import json
import re
import fasttext
from huggingface_hub import hf_hub_download
import requests
from bs4 import BeautifulSoup
import urllib3


#FUNCTIONS

def remove_html_tags(text):
    # Remove HTML tags using BeautifulSoup
    soup = BeautifulSoup(text, "html.parser")
    cleaned_text = soup.get_text(separator=" ")

    # Remove extra whitespaces and artifacts
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    return cleaned_text

def read_website_text(url):
    # Send a GET request to the URL
    response = requests.get(url, verify=False)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Remove HTML tags and artifacts from the webpage text
        cleaned_text = remove_html_tags(response.text)

        return cleaned_text
    else:
        print("Failed to retrieve the webpage. Status code:", response.status_code)
        return None

def remove_entries_with_domains(json_data, domain_file):
    with open(domain_file, 'r') as f:
        domains = [line.strip() for line in f.readlines()]
    for iso_key, entries in json_data.items():
        json_data[iso_key] = [entry for entry in entries if not any(domain in entry['link'] for domain in domains)]
    return json_data

def extract_language_code(input_str):
    pattern = r'__(label)__([a-zA-Z]+_[a-zA-Z]+)'
    match = re.search(pattern, input_str)
    if match:
        return match.group(2)
    else:
        return None

def lang_filter(filtered_data, model, iso_list):
  lang_filtered_data = {}
  for key in filtered_data:
    entry = filtered_data[key]
    for item in entry:
      lid_label = model.predict(item['snippet'])
      lid_label = extract_language_code(lid_label[0][0])
      if lid_label not in iso_list:
        new_entry = item
        if key not in lang_filtered_data:
          lang_filtered_data[key]=[]
        lang_filtered_data[key].append(item)

  return lang_filtered_data

def scraped_lang_filter(filtered_data, model, iso_list):
  lang_filtered_data = {}
  #lid_prediction_list = [] #optional line for comparison. Must be removed in final build
  for key in filtered_data:
    entry = filtered_data[key]
    for item in entry:
      link = item['link']
      scraped_text = read_website_text(link)
      if(scraped_text != None):
        lid_label_script = model.predict(scraped_text)

        lid_label = extract_language_code(lid_label_script[0][0])
        if lid_label not in iso_list:
          #lid_prediction_list.append(lid_label) #optional line for comparison. Must be removed in final build
          new_entry = item
          new_entry['glotLID'] = lid_label
          if key not in lang_filtered_data:
            lang_filtered_data[key]=[]
          lang_filtered_data[key].append(item)
  #for lpl in lid_prediction_list: #optional line for comparison. Must be removed in final build
  #  print(lpl)  #optional line for comparison. Must be removed in final build
  return lang_filtered_data

### Download LID Model for Language Filtering
model_path = hf_hub_download(repo_id="cis-lmu/glotlid", filename="model.bin")
model = fasttext.load_model(model_path)

### Load list of High resource language iso codes.
with open('iso_list.json', 'r') as f:
    iso_list = json.load(f)

### Load Json dump of web search.
with open('now.json', 'r') as json_file:
    data = json.load(json_file)

### Filter searches using filterlist.txt
filtered_data = remove_entries_with_domains(data, 'filterlist.txt')
### Filter searches to remove High resource languages
lang_filtered_data = lang_filter(filtered_data, model, iso_list)
### Disable wanrings for unverified certificate
urllib3.disable_warnings()
### Lang filter using scraped web content
scraped_lang_filtered_data = scraped_lang_filter(filtered_data, model, iso_list)

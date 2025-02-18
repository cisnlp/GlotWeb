# Import packages
import pprint
import json
from langchain_community.utilities import SearxSearchWrapper
from tqdm import tqdm

### Search and save dump function
import requests
from requests.exceptions import RequestException
from urllib3.exceptions import ProtocolError
import json
import time

def search_and_save_results(file_path, start_index, end_index):
    search = SearxSearchWrapper(searx_host="http://127.0.0.1:8080")
    with open(file_path, 'r') as file:
        results_dict = {}
        lines = file.readlines()
        
        for i, line in enumerate(tqdm(lines[start_index:end_index], initial=start_index, total=end_index - start_index)):
            iso_code, sentence = line.strip().split('\t')
            try:
                results = retry_request(
                    lambda: search.results(
                        sentence,
                        num_results=50,
                        engines=["bing", "yahoo", "qwant", "duckduckgo"]
                    )
                )
                if iso_code not in results_dict:
                    results_dict[iso_code] = []
                for result in results:
                    result['query'] = sentence
                results_dict[iso_code].extend(results)
            except RequestException as e:
                print(f"Error occurred: {e}")
                continue

    with open(f'{start_index}-{end_index}.json', 'w') as json_file:
        json.dump(results_dict, json_file, indent=4)

def retry_request(request_func, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            return request_func()
        except (RequestException, ProtocolError) as e:
            print(f"Error occurred: {e}")
            retries += 1
            if retries < max_retries:
                print("Retrying...")
                time.sleep(2)  # Wait for 2 seconds before retrying
            else:
                print("Max retries exceeded.")
                raise

search_and_save_results('glosslm_samples.txt',1001,1200)

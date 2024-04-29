# Import packages
import pprint
import json
from langchain_community.utilities import SearxSearchWrapper

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
        i = 0
        for line in file:
            if start_index <= i < end_index:  # range
                iso_code, sentence = line.strip().split('\t')
                try:
                    results = retry_request(
                        lambda: search.results(
                            sentence,
                            num_results=50,
                            engines=["bing", "yahoo", "qwant", "duckduckgo"]
                        )
                    )
                    results_dict[iso_code] = results
                except RequestException as e:
                    print(f"Error occurred: {e}")
                    continue
            if i == end_index:  # end point
                break
            i += 1 # increment
    with open(f'{start_index}-{end_index}.json', 'w') as json_file:  # file name
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

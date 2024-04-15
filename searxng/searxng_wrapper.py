# Import packages
import pprint
import json
from langchain_community.utilities import SearxSearchWrapper

### Search and save dump function
def search_and_save_results(file_path):
    search = SearxSearchWrapper(searx_host="http://127.0.0.1:8080")
    with open(file_path, 'r') as file:
        results_dict = {}
        for line in file:
            iso_code, sentence = line.strip().split('\t')
            results = search.results(
                sentence,
                num_results=15,
                engines=["bing","yahoo"]
            )
            results_dict[iso_code] = results
    with open('now.json', 'w') as json_file:
        json.dump(results_dict, json_file, indent=4)

### EXAMPLE USAGE
search_and_save_results('randomsample.txt')
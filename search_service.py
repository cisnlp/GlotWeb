import os
import yaml
import json
import time
from langchain_community.utilities import SearxSearchWrapper
from requests.exceptions import RequestException
from urllib3.exceptions import ProtocolError

class SearchService:
    def __init__(self, config_file):
        self.config = self.load_config(config_file)
        self.search = SearxSearchWrapper(searx_host=self.config['searx_host'])

    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            return yaml.safe_load(file)

    def search_and_save_results(self):
        start_index = self.config['start_index']
        end_index = self.config['end_index']
        file_path = self.config['input_file']
        output_directory = self.config['output_directory']

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        with open(file_path, 'r') as file:
            results_dict = {}
            for i, line in enumerate(file):
                if start_index <= i < end_index:
                    iso_code, sentence = line.strip().split('\t')
                    try:
                        results = self.retry_request(
                            lambda: self.search.results(
                                sentence,
                                num_results=self.config['num_results'],
                                engines=self.config['engines']
                            )
                        )
                        results_dict[iso_code] = results
                    except RequestException as e:
                        print(f"Error occurred: {e}")
                        continue
                if i >= end_index:
                    break

        output_file = os.path.join(output_directory, f"{self.config['output_file_prefix']}_{start_index}-{end_index}.json")
        with open(output_file, 'w') as json_file:
            json.dump(results_dict, json_file, indent=4)

    def retry_request(self, request_func):
        retries = 0
        max_retries = self.config['max_retries']
        while retries < max_retries:
            try:
                return request_func()
            except (RequestException, ProtocolError) as e:
                print(f"Error occurred: {e}")
                retries += 1
                if retries < max_retries:
                    print("Retrying...")
                    time.sleep(self.config['retry_wait_time'])
                else:
                    print("Max retries exceeded.")
                    raise

if __name__ == "__main__":
    config_file = "search_config.yaml"
    search_service = SearchService(config_file)
    search_service.search_and_save_results()
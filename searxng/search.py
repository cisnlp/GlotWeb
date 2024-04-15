import requests
import json
from itertools import islice

def search_and_save_results(file_path, output_file_path, start_line=0, end_line=None):
    all_results = {}
    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, start=1):
            if end_line is not None and line_number > end_line:
                break
            if line_number >= start_line:
                # Splitting the line into language ISO code and sentence
                language_iso, sentence = line.split('\t')

                # Performing the search
                search_result = search(query=sentence, categories="web", engines="bing,yahoo", page=1, format="json")

                # Saving the search result
                if search_result:
                    if language_iso not in all_results:
                        all_results[language_iso] = []
                    all_results[language_iso].append(search_result['results'][:25])

    # Saving all results in a single JSON file
    with open(output_file_path, 'w') as output_file:
        json.dump(all_results, output_file)

def search(query, categories=None, engines=None, language=None, page=1, time_range=None, format=None, results_on_new_tab=None, image_proxy=None, autocomplete=None, safesearch=None, theme=None, enabled_plugins=None, disabled_plugins=None, enabled_engines=None, disabled_engines=None):
    url = "http://localhost:8080/search"
    params = {
        "q": query,
        "categories": categories,
        "engines": engines,
        "language": language,
        "page": page,
        "time_range": time_range,
        "format": format,
        "results_on_new_tab": results_on_new_tab,
        "image_proxy": image_proxy,
        "autocomplete": autocomplete,
        "safesearch": safesearch,
        "theme": theme,
        "enabled_plugins": enabled_plugins,
        "disabled_plugins": disabled_plugins,
        "enabled_engines": enabled_engines,
        "disabled_engines": disabled_engines
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error:", response.text)
        return None

# Example usage: Read lines 101 to 200 from the file
search_and_save_results("randomsample.txt", "randomsample_100_200.json", start_line=101, end_line=200)

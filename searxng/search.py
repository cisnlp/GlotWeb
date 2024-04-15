import requests

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

# Example usage
result = search(query="sahˬ boꞈ dehˬ qhahˬ -ahˇ neh dawˬ chawˬ", categories="web", engines="bing,duckduckgo,google,qwant,yahoo", page=1, format="json")
print(result)

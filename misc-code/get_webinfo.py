import requests
from bs4 import BeautifulSoup

def get_webpage_metadata(url):
    try:
        # Fetch the webpage
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        html_content = response.content

        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Get metadata
        metadata = {}

        # Content language
        lang_attribute = soup.find('html').get('lang')
        if lang_attribute:
            metadata['Content Language'] = lang_attribute

        # Content-Language header
        content_language_header = response.headers.get('Content-Language')
        if content_language_header:
            metadata['Content-Language Header'] = content_language_header

        # Title
        title = soup.find('title')
        if title:
            metadata['Title'] = title.text.strip()

        # Description
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description and meta_description.get('content'):
            metadata['Description'] = meta_description.get('content')

        # Keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            metadata['Keywords'] = meta_keywords.get('content')

        return metadata

    except Exception as e:
        print("Error:", e)
        return None

# Example usage
url = "https://Akhaliterature.com"
metadata = get_webpage_metadata(url)
if metadata:
    print("Metadata:")
    for key, value in metadata.items():
        print(f"{key}: {value}")
else:
    print("Failed to retrieve metadata.")

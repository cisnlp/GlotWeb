import json
import os
from urllib.parse import urlparse, urlunparse

def normalize_url(url):
    """
    Normalize URL by removing the fragment (hashtag) portion.
    Returns the URL without the fragment.
    """
    parsed = urlparse(url)
    # Create new parsed URL without fragment
    clean_parsed = parsed._replace(fragment='')
    return urlunparse(clean_parsed)

def deduplicate_links(links):
    """
    Deduplicate links by removing URLs that are the same except for hashtags.
    """
    # Create a dictionary to store unique normalized URLs
    unique_urls = {}
    
    # For each link, store only the first occurrence of its normalized version
    for link in links:
        normalized = normalize_url(link)
        if normalized not in unique_urls:
            unique_urls[normalized] = link
    
    # Return the deduplicated links in the same order they first appeared
    return list(unique_urls.values())

def process_file(input_path, output_path):
    """Process a single JSON file to deduplicate links."""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Process each site's links
    for site in data.get('Sites', []):
        if 'Links' in site:
            site['Links'] = deduplicate_links(site['Links'])
    
    # Write the processed data
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    # Specify your input and output directories here
    input_dir = "output/http_merged"  # Replace with your input directory path
    output_dir = "output/deduplication"  # Replace with your output directory path
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each JSON file
    for filename in os.listdir(input_dir):
        if filename.endswith('.json'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            
            try:
                process_file(input_path, output_path)
                print(f"Processed {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    main()
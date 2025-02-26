import json
import os
from urllib.parse import urlparse
import shutil

def normalize_url(url):
    """
    Normalize URL by removing protocol, trailing slashes, and standardizing www.
    """
    parsed = urlparse(url)
    # Remove 'www.' if present
    netloc = parsed.netloc.replace('www.', '')
    # Combine with path and remove trailing slashes
    return netloc + parsed.path.rstrip('/')

def normalize_link(link):
    """
    Normalize a link URL in the same way as the main site URL.
    """
    parsed = urlparse(link)
    netloc = parsed.netloc.replace('www.', '')
    # Preserve query parameters and fragments in links
    normalized = netloc + parsed.path.rstrip('/')
    if parsed.query:
        normalized += '?' + parsed.query
    if parsed.fragment:
        normalized += '#' + parsed.fragment
    return normalized

def merge_sites(sites):
    """Merge sites that have the same URL but different protocols or www prefix."""
    # Group sites by site name and normalized URL
    site_groups = {}
    for site in sites:
        norm_url = normalize_url(site['Site URL'])
        site_name = site['Site Name']
        key = (site_name, norm_url)
        if key not in site_groups:
            site_groups[key] = []
        site_groups[key].append(site)
    
    # Merge sites that need to be merged
    merged_sites = []
    for sites_group in site_groups.values():
        if len(sites_group) == 1:
            merged_sites.append(sites_group[0])
        else:
            # Prefer https over http for the main site URL
            https_site = next((site for site in sites_group if site['Site URL'].startswith('https')), None)
            base_site = https_site if https_site else sites_group[0]
            
            # Merge all links from all versions and normalize them
            all_links = set()
            for site in sites_group:
                # Normalize each link to handle www consistently
                normalized_links = [link for link in site['Links']]
                all_links.update(normalized_links)
            
            # Create merged site entry
            merged_site = base_site.copy()
            merged_site['Links'] = sorted(list(all_links))
            merged_sites.append(merged_site)
    
    return merged_sites

def process_file(input_path, output_path):
    """Process a single JSON file."""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Merge sites
    data['Sites'] = merge_sites(data['Sites'])
    
    # Write the processed data
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main(input_dir, output_dir):
    """Process all JSON files in the input directory."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each JSON file
    for filename in os.listdir(input_dir):
        if filename.endswith('.json'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            process_file(input_path, output_path)
            print(f"Processed {filename}")

if __name__ == "__main__":
    import sys
    
    
    
    input_dir = "output/robots_filtered"  # Replace with your input directory path
    output_dir = "output/http_merged"
    
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        sys.exit(1)
    
    main(input_dir, output_dir)
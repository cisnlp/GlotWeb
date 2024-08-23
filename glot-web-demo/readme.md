# Step 1: Set up SearXNG and perform search

##  SearXNG

### Install
```bash

export PORT=8080

docker pull searxng/searxng
docker run --rm \
             -d -p ${PORT}:8080 \
             -v "${PWD}/searxng:/etc/searxng" \
             -e "BASE_URL=http://localhost:${PORT}/" \
             -e "INSTANCE_NAME=my-instance" \
             searxng/searxng
```

**add JSON output format:**

In the `${PWD}/searxng` directory, there is a file named `settings.yml`. In that file, you need to enable the JSON output format in the SearX configuration under the `search.formats` key like this:

```yml
search:
  formats:
    - html
    - json
```

**modify uwsgi.ini :**
In the `${PWD}/searxng` directory, there is a file named `uwsgi.ini`. In that file you need to modify buffer-size. Default is 8k. Increasing to 9k sometimes help with 'Internal Error 500'.

Default Value:
```ini
buffer-size = 8192
```
Change to:
```ini
buffer-size = 9216
```

## Search Service Script: search_service.py

This is an object-oriented Python script that leverages the Searx API to perform searches and save the results to JSON files. The script is configurable using a YAML configuration file called 'search_config.yaml'.

### Features

- Uses SearxSearchWrapper for querying multiple search engines.
- Handles retries for failed requests.
- Configurable search parameters through a YAML file.
- Configurable input file, search range, output directory, and other parameters.
- Automatically saves results in a structured JSON format.

### Configuration file parameters:

```yml
searx_host: "http://127.0.0.1:8080"  # Searx instance URL
engines:
  - "bing"
  - "yahoo"
  - "qwant"
  - "duckduckgo"  # Search engines to be used
num_results: 50  # Number of results to fetch for each query
max_retries: 3  # Maximum number of retries for failed requests
retry_wait_time: 2  # Wait time (in seconds) between retries
output_file_prefix: "results"  # Prefix for output file names
output_directory: "search_dump"  # Directory to save output files
input_file: "input.txt"  # Path to the input file containing search queries
start_index: 0  # Start index for queries to process
end_index: 10  # End index for queries to process
```

# Step 2: Filter and generate seeds

# Step 3: Seacrch and scrape with seeds

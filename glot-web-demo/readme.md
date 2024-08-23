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

## Features

- Uses SearxSearchWrapper for querying multiple search engines.
- Handles retries for failed requests.
- Configurable search parameters through a YAML file.
- Configurable input file, search range, output directory, and other parameters.
- Automatically saves results in a structured JSON format.

import json

# Function to read JSON file
def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Function to transform the JSON entries into a dictionary
def transform_entries_to_dict(entries):
    if not isinstance(entries, list):
        raise TypeError("The input data must be a list of dictionaries.")
    
    transformed_dict = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise TypeError("Each entry must be a dictionary.")
        
        glottocode = entry['id']
        isocode = next((identifier['identifier'] for identifier in entry['identifiers'] if identifier['type'] == 'iso639-3'), None)
        transformed_dict[glottocode] = isocode
    return transformed_dict

# Function to write JSON to file
def write_json_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

# Main process
# We used https://glottolog.org/resourcemap.json?rsc=language as our source and saved it as 'resourcemap.json'
input_file_path = 'resourcemap.json'  # Change this to your input file path
output_file_path = 'glotto_iso.json'  # Change this to your desired output file path


# Read the JSON file
data = read_json_file(input_file_path)

entries = data["resources"]

# Transform the entries into a dictionary
transformed_dict = transform_entries_to_dict(entries)

# Write the transformed dictionary to a new JSON file
write_json_file(transformed_dict, output_file_path)

print(f"Transformed data has been written to {output_file_path}")

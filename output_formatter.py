import os
import pandas as pd
import yaml
import pycountry
from typing import Dict, Any, Optional
import json
import json
from urllib.parse import urlparse
from collections import defaultdict


flores_list = [
    "ace_Arab", "ace_Latn", "acm_Arab", "acq_Arab", "aeb_Arab", "afr_Latn", "ajp_Arab",
    "aka_Latn", "amh_Ethi", "apc_Arab", "arb_Arab", "ars_Arab", "ary_Arab", "arz_Arab",
    "asm_Beng", "ast_Latn", "awa_Deva", "ayr_Latn", "azb_Arab", "azj_Latn", "bak_Cyrl",
    "bam_Latn", "ban_Latn", "bel_Cyrl", "bem_Latn", "ben_Beng", "bho_Deva", "bjn_Arab", 
    "bjn_Latn", "bod_Tibt", "bos_Latn", "bug_Latn", "bul_Cyrl", "cat_Latn", "ceb_Latn", 
    "ces_Latn", "cjk_Latn", "ckb_Arab", "crh_Latn", "cym_Latn", "dan_Latn", "deu_Latn", 
    "dik_Latn", "dyu_Latn", "dzo_Tibt", "ell_Grek", "eng_Latn", "epo_Latn", "est_Latn", 
    "eus_Latn", "ewe_Latn", "fao_Latn", "pes_Arab", "fij_Latn", "fin_Latn", "fon_Latn", 
    "fra_Latn", "fur_Latn", "fuv_Latn", "gla_Latn", "gle_Latn", "glg_Latn", "grn_Latn", 
    "guj_Gujr", "hat_Latn", "hau_Latn", "heb_Hebr", "hin_Deva", "hne_Deva", "hrv_Latn", 
    "hun_Latn", "hye_Armn", "ibo_Latn", "ilo_Latn", "ind_Latn", "isl_Latn", "ita_Latn", 
    "jav_Latn", "jpn_Jpan", "kab_Latn", "kac_Latn", "kam_Latn", "kan_Knda", "kas_Arab", 
    "kas_Deva", "kat_Geor", "knc_Arab", "knc_Latn", "kaz_Cyrl", "kbp_Latn", "kea_Latn", 
    "khm_Khmr", "kik_Latn", "kin_Latn", "kir_Cyrl", "kmb_Latn", "kon_Latn", "kor_Hang", 
    "kmr_Latn", "lao_Laoo", "lvs_Latn", "lij_Latn", "lim_Latn", "lin_Latn", "lit_Latn", 
    "lmo_Latn", "ltg_Latn", "ltz_Latn", "lua_Latn", "lug_Latn", "luo_Latn", "lus_Latn", 
    "mag_Deva", "mai_Deva", "mal_Mlym", "mar_Deva", "min_Latn", "mkd_Cyrl", "plt_Latn", 
    "mlt_Latn", "mni_Beng", "khk_Cyrl", "mos_Latn", "mri_Latn", "zsm_Latn", "mya_Mymr", 
    "nld_Latn", "nno_Latn", "nob_Latn", "npi_Deva", "nso_Latn", "nus_Latn", "nya_Latn", 
    "oci_Latn", "gaz_Latn", "ory_Orya", "pag_Latn", "pan_Guru", "pap_Latn", "pol_Latn", 
    "por_Latn", "prs_Arab", "pbt_Arab", "quy_Latn", "ron_Latn", "run_Latn", "rus_Cyrl", 
    "sag_Latn", "san_Deva", "sat_Beng", "scn_Latn", "shn_Mymr", "sin_Sinh", "slk_Latn", 
    "slv_Latn", "smo_Latn", "sna_Latn", "snd_Arab", "som_Latn", "sot_Latn", "spa_Latn", 
    "als_Latn", "srd_Latn", "srp_Cyrl", "ssw_Latn", "sun_Latn", "swe_Latn", "swh_Latn", 
    "szl_Latn", "tam_Taml", "tat_Cyrl", "tel_Telu", "tgk_Cyrl", "tgl_Latn", "tha_Thai", 
    "tir_Ethi", "taq_Latn", "taq_Tfng", "tpi_Latn", "tsn_Latn", "tso_Latn", "tuk_Latn", 
    "tum_Latn", "tur_Latn", "twi_Latn", "tzm_Tfng", "uig_Arab", "ukr_Cyrl", "umb_Latn", 
    "urd_Arab", "uzn_Latn", "vec_Latn", "vie_Latn", "war_Latn", "wol_Latn", "xho_Latn", 
    "ydd_Hebr", "yor_Latn", "yue_Hant", "zho_Hans", "zho_Hant", "zul_Latn"
]

IGNORED_SUBDOMAINS = [
    "www", "en", "de", "fr", "us", "uk", "ca",
    "mail", "webmail", "email", "ftp", "blog", 
    "shop", "help", "support", "docs", "kb", 
    "api", "cdn", "assets", "static", "analytics",
    "track", "metrics", "m", "beta", "staging", 
    "dev", "portal", "dashboard", "media", "http", "https", "www1", "www2", "www3"
]


# Function to load configuration
def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

def get_language_name(code: str) -> str:
    """
    Get the language name using pycountry.
    If not found, return the original code.
    """
    try:
        language = pycountry.languages.get(alpha_3=code)
        return language.name if language else code
    except (AttributeError, KeyError):
        return code

def get_speakers(code: str) -> Optional[str]:
    """
    Get the number of speakers from the CSV data.
    If not found by code, try to find by language name.
    Return None if no data is found.
    """
    # Try to find by code (ISO 639-3 or ISO 639-5)
    if code in df.index:
        return df.loc[code, 'Speakers worldwide']
    
    # If not found by code, try to find by language name
    lang_name = get_language_name(code)
    matching_rows = df[df['Name'].str.lower() == lang_name.lower()]
    if not matching_rows.empty:
        return matching_rows['Speakers worldwide'].iloc[0]
    
    return None

def is_in_madlad(code):
    with open('madlad_aplha_3.json', 'r') as file:
        madlad_aplha_3 = json.load(file)
    
    if code in madlad_aplha_3:
        return 1
    else:
        return 0
    
def is_in_flores(langisocode693_Script):
    if langisocode693_Script in flores_list:
        return 1
    else:
        return 0

def is_in_glot500(langisocode693_Script):
    with open('madlad_aplha_3.json', 'r') as file:
        glot500_aplha_3 = json.load(file)
    
    if langisocode693_Script in glot500_aplha_3:
        return 1
    else:
        return 0
    
def categorize_urls(json_file):
    # Read the JSON file
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    # Create a defaultdict to store URLs by site
    url_categories = defaultdict(list)
    
    # Categorize URLs
    for item in data:
        url = item['link']
        parsed_url = urlparse(url)
        site_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        url_categories[site_url].append(url)
    
    # Format the result
    result = []
    for site_url, links in url_categories.items():
        # Extract site name intelligently
        netloc_parts = urlparse(site_url).netloc.split('.')
        
        # Filter out ignored subdomains
        primary_domain_parts = [
            part for part in netloc_parts 
            if part.lower() not in IGNORED_SUBDOMAINS
        ]
        
        # Determine the site name based on conditions
        if primary_domain_parts:
            # Check if the first part is short (<= 3 characters) and not ignored
            if len(primary_domain_parts[0]) <= 3 and len(primary_domain_parts) > 1:
                site_name = primary_domain_parts[1]  # Use the next part if available
            else:
                site_name = primary_domain_parts[0]  # Otherwise, use the first part
        else:
            site_name = netloc_parts[0]  # Fallback to the first part if all are ignored
        
        result.append({
            "Site Name": site_name,
            "Site URL": site_url,
            "Info": 'confirmed by glotlid',
            "confidence": "🟩",
            "Links": links
        })
    
    return result

def save_language_info(language_info, language_name, config):
    # Extract directory and file name from config
    directory = config['output']['formated_directory']
    file_name_template = config['output']['formated_file_name']
    
    # Replace {language} in the file name with the actual language name
    file_name = file_name_template.format(language=language_name)
    
    # Ensure the directory exists
    os.makedirs(directory, exist_ok=True)
    
    # Create the full path
    file_path = os.path.join(directory, file_name)
    
    # Save the dictionary to the file as JSON
    with open(file_path, 'w') as json_file:
        json.dump(language_info, json_file, ensure_ascii=False, indent=4)

#### Big function to be made.

# Load the configuration
config = load_config('config.yaml')

# Extract the language code and script from the config
langisocode693_Script = config['language_detector']['desired_language']
#langisocode693_Script = 'ada_Latn'
code, script = langisocode693_Script.split('_')

# Read only the necessary columns into a pandas DataFrame
df = pd.read_csv('language_speakers_data.csv', usecols=['ISO Alpha-3/5', 'Name', 'Speakers worldwide'])

# Set "ISO Alpha-3/5" as the index for faster lookups
df.set_index('ISO Alpha-3/5', inplace=True)

# Get language name
lang_name = get_language_name(code)

# Get number of speakers
speakers = get_speakers(code)
# You can now use lang_name and speakers for further tasks or add them to a dictionary
language_info = {
    "Language Name": lang_name,
    "Number of Speakers": speakers if speakers is not None else "No data",
    "Family":'',
    "Subgrouping": '',
    "Supported by allenai/MADLAD-400": is_in_madlad(code),
    "Supported by facebook/flores": is_in_flores(langisocode693_Script),
    "Supported by cis-lmu/Glot500": is_in_glot500(langisocode693_Script)

}
json_file_name = config['output']['directory']+ langisocode693_Script + '_crawled_output.json'
categorized_urls = categorize_urls(json_file_name)

language_info['Sites'] = categorized_urls

save_language_info(language_info, langisocode693_Script, config)

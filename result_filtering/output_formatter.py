import os
import pandas as pd
import yaml
import pycountry
from typing import Dict, Any, Optional, List
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

def get_speakers(code: str, df: pd.DataFrame) -> Optional[str]:
    """
    Get the number of speakers from the CSV data.
    If not found by code, try to find by language name.
    Return None if no data is found.
    """
    if code in df.index:
        return df.loc[code, 'Speakers worldwide']
    
    lang_name = get_language_name(code)
    matching_rows = df[df['Name'].str.lower() == lang_name.lower()]
    if not matching_rows.empty:
        return matching_rows['Speakers worldwide'].iloc[0]
    
    return None


def get_number_of_speakers(file_path, iso_639_3_code):
    """
    Reads a TSV file and retrieves the 'estimated_number_of_speakers' for a given 'iso_639_3_code'.
    
    Args:
        file_path (str): Path to the 'linguameta.tsv' file.
        iso_639_3_code (str): The ISO 639-3 code to look up.
        
    Returns:
        int or None: The estimated number of speakers for the given 'iso_639_3_code', 
                     or None if the code is not found.
    """
    try:
        # Load the TSV file into a DataFrame
        df = pd.read_csv(file_path, sep='\t')
    except Exception as e:
        print(f"Error reading the file: {e}")
        return None

    # Filter the DataFrame to find the row matching the 'iso_639_3_code'
    row = df[df['iso_639_3_code'] == iso_639_3_code]
    if row.empty:
        print(f"No matching row found for iso_639_3_code: {iso_639_3_code}")
        return None

    # Retrieve the value of 'estimated_number_of_speakers'
    try:
        estimated_speakers = row['estimated_number_of_speakers'].values[0]
        return estimated_speakers
    except KeyError as e:
        print(f"Error: Column not found - {e}")
        return None


def get_family_name_from_iso(file_path, iso639P3code):
    """
    Reads a CSV file and retrieves the family name corresponding to a given 'iso639P3code'.
    
    Args:
        file_path (str): Path to the 'languoid.csv' file.
        iso639P3code (str): The ISO 639-3 code to look up.
        
    Returns:
        str: The family name corresponding to the given 'iso639P3code', or None if not found.
    """
    # Load the CSV file into a DataFrame
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading the file: {e}")
        return None

    # Step 1: Retrieve the 'family_id' for the given 'iso639P3code'
    family_id_row = df[df['iso639P3code'] == iso639P3code]
    if family_id_row.empty:
        print(f"No matching row found for iso639P3code: {iso639P3code}")
        return None

    family_id = family_id_row['family_id'].values[0]

    # Step 2: Retrieve the 'name' where 'id' equals the retrieved 'family_id'
    family_name_row = df[df['id'] == family_id]
    if family_name_row.empty:
        print(f"No matching row found for family_id: {family_id}")
        return None

    family_name = family_name_row['name'].values[0]

    return family_name

def is_in_madlad(code: str) -> int:
    with open('metadata/madlad_aplha_3.json', 'r') as file:
        madlad_aplha_3 = json.load(file)
    return 1 if code in madlad_aplha_3 else 0

def is_in_flores(langisocode693_Script: str) -> int:
    return 1 if langisocode693_Script in flores_list else 0

def is_in_glot500(langisocode693_Script: str) -> int:
    with open('metadata/glot500_iso_code.json', 'r') as file:
        glot500_aplha_3 = json.load(file)
    return 1 if langisocode693_Script in glot500_aplha_3 else 0

def categorize_urls(json_file: str) -> List[Dict[str, Any]]:
    try:
        with open(json_file, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Warning: File not found: {json_file}")
        return []
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in file: {json_file}")
        return []

    url_categories = defaultdict(list)
    
    for item in data:
        url = item['link']
        parsed_url = urlparse(url)
        site_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        url_categories[site_url].append(url)
    
    result = []
    for site_url, links in url_categories.items():
        netloc_parts = urlparse(site_url).netloc.split('.')
        
        primary_domain_parts = [
            part for part in netloc_parts 
            if part.lower() not in IGNORED_SUBDOMAINS
        ]
        
        if primary_domain_parts:
            if len(primary_domain_parts[0]) <= 3 and len(primary_domain_parts) > 1:
                site_name = primary_domain_parts[1]
            else:
                site_name = primary_domain_parts[0]
        else:
            site_name = netloc_parts[0]
        
        result.append({
            "Site Name": site_name,
            "Site URL": site_url,
            "Info": 'confirmed by glotlid',
            "confidence": "🟩",
            "Links": links
        })
    
    return result

def save_language_info(language_info: Dict[str, Any], language_name: str, config: Dict[str, Any]) -> None:
    directory = config['output']['formated_directory']
    file_name = config['output']['formated_file_name'].format(language=language_name)
    
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, file_name)
    
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(language_info, json_file, ensure_ascii=False, indent=4)
    
    print(f"Saved formatted output for {language_name} to {file_path}")

def process_single_language(langisocode693_Script: str, df: pd.DataFrame, config: Dict[str, Any]) -> None:
    """Process a single language and generate its formatted output."""
    code, script = langisocode693_Script.split('_')
    
    # Get language information
    lang_name = get_language_name(code)
    speakers = get_number_of_speakers('metadata/linguameta.tsv', code)
    family = get_family_name_from_iso('metadata/languoid.csv', code)
    
    # Create language info dictionary
    language_info = {
        "Language Name": lang_name,
        "Number of Speakers": speakers if speakers is not None else "No data",
        "Family": family if family is not None else "No data",
        "Subgrouping": '',
        "Supported by allenai/MADLAD-400": is_in_madlad(code),
        "Supported by facebook/flores": is_in_flores(langisocode693_Script),
        "Supported by cis-lmu/Glot500": is_in_glot500(langisocode693_Script)
    }
    
    # Process URLs
    json_file_name = os.path.join(
        config['output']['directory'],
        f"{langisocode693_Script}_crawled_output.json"
    )
    categorized_urls = categorize_urls(json_file_name)
    language_info['Sites'] = categorized_urls
    
    # Save formatted output
    save_language_info(language_info, langisocode693_Script, config)

def batch_process_languages(config: Dict[str, Any]) -> None:
    """Process multiple languages in batch."""
    print("Starting batch processing...")
    
    # Read the speakers data once for all languages
    df = pd.read_csv('metadata/language_speakers_data.csv', usecols=['ISO Alpha-3/5', 'Name', 'Speakers worldwide'])
    df.set_index('ISO Alpha-3/5', inplace=True)
    
    # Get list of languages to process
    if config.get('batch_processing', {}).get('enabled', False):
        languages = config['batch_processing']['input_labels']
    else:
        languages = [config['language_detector']['desired_language']]
    
    total_languages = len(languages)
    print(f"Processing {total_languages} languages...")
    
    for idx, language in enumerate(languages, 1):
        print(f"\nProcessing language {idx}/{total_languages}: {language}")
        try:
            process_single_language(language, df, config)
        except Exception as e:
            print(f"Error processing language {language}: {str(e)}")
            continue
    
    print("\nBatch processing completed!")

def main():
    # Load configuration
    config = load_config('pipeline/config.yaml')
    
    # Start batch processing
    batch_process_languages(config)

if __name__ == "__main__":
    main()

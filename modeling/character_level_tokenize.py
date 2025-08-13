#!/usr/bin/env python3
"""
Text processing utilities for truncation and character-level tokenization.

This module provides functions to:
1. Truncate all text files to the length of the shortest file
2. Tokenize text at the character level
3. Process multiple text files in batch

Pipeline: raw text -> truncated text -> tokenized text
"""

import re
import os
import sys
from pathlib import Path


def tokenizer_char(sentence: str) -> str:
    """
    Convert sentence to character-level tokens separated by spaces.
    
    Args:
        sentence (str): Input sentence to tokenize
        
    Returns:
        str: Character-tokenized string with spaces between characters
    """
    if sentence == "":
        return ""
    elif sentence.strip() == "":
        return ""
    else:
        s = ' '.join(list(sentence))
        # Replace multiple spaces with double space
        s = re.sub(r"\s\s+", '  ', s)
        return s.strip()


def truncate_files(source_dir: str, target_dir: str):
    """
    Truncate all text files in source directory to the length of the shortest file.
    
    Reads all .txt files, finds the shortest one, and truncates all files to that length.
    Saves the truncated files to the target directory.
    
    Args:
        source_dir (str): Path to directory containing source .txt files
        target_dir (str): Path to directory where truncated files will be saved
        
    Returns:
        int: Length that files were truncated to (0 if no files found)
        
    Raises:
        FileNotFoundError: If source directory doesn't exist
        PermissionError: If unable to create target directory or write files
    """
    source_path = Path(source_dir)
    target_path = Path(target_dir)
    
    # Check if source directory exists
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory '{source_dir}' does not exist")
    
    if not source_path.is_dir():
        raise NotADirectoryError(f"'{source_dir}' is not a directory")
    
    # Ensure the target directory exists
    try:
        target_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise PermissionError(f"Unable to create target directory '{target_dir}'")
    
    # List all text files in the source directory
    text_files = list(source_path.glob("*.txt"))
    
    if not text_files:
        print("No text files found in the source directory.")
        return 0
    
    print(f"Found {len(text_files)} text files to process")
    
    # Read all files and find the length of the shortest one
    file_contents = {}
    shortest_length = float('inf')
    
    for txt_file in text_files:
        try:
            with open(txt_file, 'r', encoding='utf-8') as file:
                content = file.read()
                file_contents[txt_file.name] = content
                shortest_length = min(shortest_length, len(content))
                print(f"Read {txt_file.name}: {len(content)} characters")
        except Exception as e:
            print(f"Error reading {txt_file.name}: {e}", file=sys.stderr)
    
    if shortest_length == float('inf'):
        print("No files could be read successfully")
        return 0
    
    print(f"Shortest file length: {shortest_length} characters")
    
    # Truncate each file's content and save to the target directory
    for file_name, content in file_contents.items():
        try:
            truncated_content = content[:shortest_length]
            target_file_path = target_path / file_name
            
            with open(target_file_path, 'w', encoding='utf-8') as file:
                file.write(truncated_content)
            
            print(f"Truncated and saved: {file_name}")
            
        except Exception as e:
            print(f"Error processing {file_name}: {e}", file=sys.stderr)
    
    print(f"Files have been truncated to {shortest_length} characters and saved in {target_dir}")
    return shortest_length


def process_txt_files(input_dir: str, output_dir: str, tokenizer_func):
    """
    Process all .txt files from input directory with tokenizer function.
    
    Reads all .txt files from an input directory, applies a tokenizer function,
    and saves the tokenized text to an output directory with '_tokenized' added
    to the file name.
    
    Args:
        input_dir (str): Path to the directory containing input .txt files
        output_dir (str): Path to the directory where tokenized files will be saved
        tokenizer_func (function): A function that takes a string and returns a tokenized string
        
    Returns:
        None
        
    Raises:
        FileNotFoundError: If input directory doesn't exist
        PermissionError: If unable to create output directory or write files
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Check if input directory exists
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory '{input_dir}' does not exist")
    
    if not input_path.is_dir():
        raise NotADirectoryError(f"'{input_dir}' is not a directory")
    
    # Ensure the output directory exists
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise PermissionError(f"Unable to create output directory '{output_dir}'")
    
    # Find all .txt files in the input directory
    txt_files = list(input_path.glob("*.txt"))
    
    if not txt_files:
        print(f"No .txt files found in '{input_dir}'")
        return
    
    print(f"Found {len(txt_files)} .txt files to tokenize")
    
    # Process each file
    for txt_file in txt_files:
        try:
            output_file_name = f"{txt_file.stem}_tokenized.txt"
            output_file_path = output_path / output_file_name
            
            # Read the input file
            with open(txt_file, "r", encoding="utf-8") as file:
                text = file.read()
            
            # Apply the tokenizer function
            tokenized_text = tokenizer_func(text)
            
            # Save the tokenized text to the output file
            with open(output_file_path, "w", encoding="utf-8") as file:
                file.write(tokenized_text)
            
            print(f"Processed {txt_file.name} -> {output_file_name}")
            
        except Exception as e:
            print(f"Error processing {txt_file.name}: {e}", file=sys.stderr)


def run_full_pipeline(source_dir: str = "text_files", 
                      truncated_dir: str = "truncated_text_files",
                      tokenized_dir: str = "tokenized_truncated_text_files"):
    """
    Run the complete text processing pipeline.
    
    Pipeline steps:
    1. Truncate all files to shortest length
    2. Tokenize the truncated files at character level
    
    Args:
        source_dir (str): Directory containing original text files
        truncated_dir (str): Directory for truncated files
        tokenized_dir (str): Directory for final tokenized files
    """
    print("=== Text Processing Pipeline ===")
    print(f"Source: {source_dir}")
    print(f"Truncated: {truncated_dir}")
    print(f"Tokenized: {tokenized_dir}")
    print()
    
    try:
        # Step 1: Truncate files
        print("Step 1: Truncating files...")
        shortest_length = truncate_files(source_dir, truncated_dir)
        
        if shortest_length == 0:
            print("No files to process. Pipeline stopped.")
            return
        
        print()
        
        # Step 2: Tokenize truncated files
        print("Step 2: Tokenizing truncated files...")
        process_txt_files(truncated_dir, tokenized_dir, tokenizer_char)
        
        print()
        print("=== Pipeline Complete ===")
        print(f"Final tokenized files are in: {tokenized_dir}")
        
    except Exception as e:
        print(f"Pipeline error: {e}", file=sys.stderr)


def main():
    """Main function to run the text processing pipeline."""
    # Configuration - modify these paths as needed
    source_directory = "text_files"
    truncated_directory = "truncated_text_files"
    tokenized_directory = "tokenized_truncated_text_files"
    
    # Check current working directory
    current_dir = Path.cwd()
    source_path = current_dir / source_directory
    
    print(f"Current working directory: {current_dir}")
    print(f"Looking for source files in: {source_path}")
    print()
    
    try:
        run_full_pipeline(source_directory, truncated_directory, tokenized_directory)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Please ensure your text files are in the '{source_directory}' directory")
        print("Or modify the directory variables in this script")
        
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
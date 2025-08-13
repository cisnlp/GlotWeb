import os
import sys
import subprocess
import shutil
from pathlib import Path
from tqdm import tqdm


# Language codes to process
DEFAULT_CODE_LIST = [
    'swg_Latn', 'orv_Cyrl', 'ast_Latn', 'srn_Latn', 'pmf_Latn', 'gor_Latn', 
    'yli_Latn', 'mnw_Mymr', 'mvp_Latn', 'cos_Latn', 'bre_Latn', 'crs_Latn', 
    'ceb_Latn', 'bbc_Latn', 'mag_Deva', 'shi_Latn', 'hsb_Latn', 'rad_Latn', 
    'blk_Mymr', 'nbl_Latn', 'cak_Latn', 'pwn_Latn', 'dag_Latn', 'chv_Cyrl', 
    'trv_Latn', 'lez_Cyrl', 'syc_Syrc', 'ace_Latn', 'ami_Latn', 'tyv_Cyrl', 
    'vol_Latn', 'mni_Mtei', 'alt_Cyrl', 'nso_Latn', 'sid_Latn', 'ctd_Latn', 
    'bxr_Cyrl', 'tll_Latn', 'djr_Latn', 'gos_Latn', 'rue_Cyrl', 'nah_Latn', 
    'lij_Latn', 'gag_Latn', 'guw_Latn', 'kri_Latn', 'szy_Latn', 'pma_Latn', 
    'fur_Latn', 'non_Latn', 'bcl_Latn', 'lmo_Latn', 'fuv_Latn', 'glk_Arab', 
    'mdf_Cyrl', 'myv_Cyrl', 'krc_Cyrl', 'koi_Cyrl', 'stq_Latn', 'tat_Latn'
]


def run_command(command: str, cwd: str = None, check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a shell command safely with proper error handling.
    
    Args:
        command (str): Command to execute
        cwd (str, optional): Working directory for the command
        check (bool): Whether to raise exception on non-zero exit code
        
    Returns:
        subprocess.CompletedProcess: Result of the command execution
        
    Raises:
        subprocess.CalledProcessError: If command fails and check=True
    """
    print(f"Running: {command}")
    if cwd:
        print(f"Working directory: {cwd}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            check=check,
            capture_output=True, 
            text=True
        )
        
        if result.stdout:
            print("STDOUT:", result.stdout.strip())
        if result.stderr and result.returncode != 0:
            print("STDERR:", result.stderr.strip(), file=sys.stderr)
            
        return result
        
    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}", file=sys.stderr)
        if e.stderr:
            print(f"Error output: {e.stderr}", file=sys.stderr)
        raise


def check_dependencies():
    """
    Check if required system dependencies are available.
    
    Returns:
        bool: True if all dependencies are available
    """
    dependencies = ['wget', 'tar', 'cmake', 'make', 'g++']
    missing = []
    
    for dep in dependencies:
        if not shutil.which(dep):
            missing.append(dep)
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Please install them using your package manager:")
        print("Ubuntu/Debian: sudo apt-get install wget tar cmake build-essential")
        print("macOS: brew install cmake (wget and tar should be pre-installed)")
        return False
    
    print("All dependencies are available.")
    return True


def install_kenlm(install_dir: str = "kenlm") -> Path:
    """
    Download, extract, and build KenLM toolkit.
    
    Args:
        install_dir (str): Directory where KenLM will be installed
        
    Returns:
        Path: Path to the KenLM build directory
        
    Raises:
        RuntimeError: If installation fails
    """
    install_path = Path(install_dir).resolve()
    build_path = install_path / "build"
    
    print(f"Installing KenLM to: {install_path}")
    
    # Check if already installed
    lmplz_path = build_path / "bin" / "lmplz"
    build_binary_path = build_path / "bin" / "build_binary"
    
    if lmplz_path.exists() and build_binary_path.exists():
        print("KenLM is already installed and built.")
        return build_path
    
    try:
        # Remove existing directory if it exists
        if install_path.exists():
            print("Removing existing KenLM directory...")
            shutil.rmtree(install_path)
        
        # Download and extract KenLM
        print("Downloading and extracting KenLM...")
        run_command("wget -O - https://kheafield.com/code/kenlm.tar.gz | tar xz")
        
        # Create build directory
        build_path.mkdir(parents=True, exist_ok=True)
        
        # Configure with cmake
        print("Configuring with cmake...")
        run_command("cmake ..", cwd=str(build_path))
        
        # Build with make
        print("Building with make...")
        run_command("make -j2", cwd=str(build_path))
        
        # Make executables executable (redundant on most systems, but safe)
        if lmplz_path.exists():
            lmplz_path.chmod(0o755)
        if build_binary_path.exists():
            build_binary_path.chmod(0o755)
        
        print("KenLM installation completed successfully!")
        return build_path
        
    except Exception as e:
        print(f"KenLM installation failed: {e}", file=sys.stderr)
        raise RuntimeError(f"Failed to install KenLM: {e}")


def create_language_model(input_file: Path, output_file: Path, n_gram: int, 
                         kenlm_build_dir: Path) -> bool:
    """
    Create an ARPA format language model from a text file.
    
    Args:
        input_file (Path): Input tokenized text file
        output_file (Path): Output ARPA file
        n_gram (int): N-gram order for the language model
        kenlm_build_dir (Path): Path to KenLM build directory
        
    Returns:
        bool: True if successful, False otherwise
    """
    lmplz_path = kenlm_build_dir / "bin" / "lmplz"
    
    if not lmplz_path.exists():
        print(f"Error: lmplz not found at {lmplz_path}", file=sys.stderr)
        return False
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        return False
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Build the command
    command = f"{lmplz_path} -o {n_gram} --discount_fallback --skip_symbols < {input_file} > {output_file}"
    
    try:
        run_command(command)
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to create language model for {input_file.name}", file=sys.stderr)
        return False


def convert_to_binary(arpa_file: Path, binary_file: Path, kenlm_build_dir: Path) -> bool:
    """
    Convert ARPA format language model to binary format.
    
    Args:
        arpa_file (Path): Input ARPA file
        binary_file (Path): Output binary file
        kenlm_build_dir (Path): Path to KenLM build directory
        
    Returns:
        bool: True if successful, False otherwise
    """
    build_binary_path = kenlm_build_dir / "bin" / "build_binary"
    
    if not build_binary_path.exists():
        print(f"Error: build_binary not found at {build_binary_path}", file=sys.stderr)
        return False
    
    if not arpa_file.exists():
        print(f"Error: ARPA file not found: {arpa_file}", file=sys.stderr)
        return False
    
    # Ensure output directory exists
    binary_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Build the command
    command = f"{build_binary_path} -s {arpa_file} {binary_file}"
    
    try:
        run_command(command)
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to convert {arpa_file.name} to binary", file=sys.stderr)
        return False


def language_modeling(input_dir: str, output_dir: str, bin_output_dir: str, 
                     code_list: list, n_gram_param: int, kenlm_build_dir: str = None):
    """
    Create language models for a list of language codes.
    
    Args:
        input_dir (str): Path to directory containing tokenized text files
        output_dir (str): Path to directory for ARPA language models
        bin_output_dir (str): Path to directory for binary language models
        code_list (list): List of language codes to process
        n_gram_param (int): N-gram parameter for the language models
        kenlm_build_dir (str, optional): Path to KenLM build directory
        
    Returns:
        None
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    bin_output_path = Path(bin_output_dir)
    
    # Setup KenLM
    if kenlm_build_dir:
        kenlm_build = Path(kenlm_build_dir)
    else:
        kenlm_build = install_kenlm()
    
    # Ensure output directories exist
    output_path.mkdir(parents=True, exist_ok=True)
    bin_output_path.mkdir(parents=True, exist_ok=True)
    
    # Process each language code
    successful = 0
    failed = 0
    
    print(f"Processing {len(code_list)} language codes with {n_gram_param}-gram models...")
    
    for code in tqdm(code_list, desc="Creating language models"):
        input_file = input_path / f"{code}_tokenized.txt"
        arpa_file = output_path / f"{code}.arpa"
        bin_file = bin_output_path / f"{code}.bin"
        
        print(f"\nProcessing {code}...")
        
        # Create ARPA model
        if create_language_model(input_file, arpa_file, n_gram_param, kenlm_build):
            print(f"Created ARPA model: {arpa_file.name}")
            
            # Convert to binary
            if convert_to_binary(arpa_file, bin_file, kenlm_build):
                print(f"Created binary model: {bin_file.name}")
                successful += 1
            else:
                print(f"Failed to create binary model for {code}")
                failed += 1
        else:
            print(f"Failed to create ARPA model for {code}")
            failed += 1
    
    print(f"\nLanguage modeling completed!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")


def main():
    """Main function to run language modeling."""
    # Configuration
    n_gram_param = 5
    input_dir = "tokenized_truncated_text_files"
    output_dir = f"truncated_{n_gram_param}_gram_models"
    bin_output_dir = f"truncated_{n_gram_param}_gram_bin_models"
    
    print("=== Language Modeling with KenLM ===")
    print(f"N-gram parameter: {n_gram_param}")
    print(f"Input directory: {input_dir}")
    print(f"ARPA output directory: {output_dir}")
    print(f"Binary output directory: {bin_output_dir}")
    print()
    
    # Check dependencies
    if not check_dependencies():
        print("Please install missing dependencies and try again.")
        sys.exit(1)
    
    try:
        # Run language modeling
        language_modeling(
            input_dir=input_dir,
            output_dir=output_dir, 
            bin_output_dir=bin_output_dir,
            code_list=DEFAULT_CODE_LIST,
            n_gram_param=n_gram_param
        )
        
        print(f"\nResults saved to:")
        print(f"ARPA models: {output_dir}")
        print(f"Binary models: {bin_output_dir}")
        
    except Exception as e:
        print(f"Language modeling failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
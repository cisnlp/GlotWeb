#!/bin/bash

# Setup script for KenLM language modeling environment
# This script installs system dependencies and builds KenLM

set -e  # Exit on any error

echo "=== KenLM Language Modeling Setup ==="
echo "This script will install system dependencies and build KenLM"
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "Unsupported operating system: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"

# Install system dependencies
echo ""
echo "Installing system dependencies..."

if [[ "$OS" == "linux" ]]; then
    # Check if we have sudo access
    if command -v apt-get >/dev/null 2>&1; then
        echo "Installing dependencies with apt-get..."
        sudo apt-get update
        sudo apt-get install -y wget tar cmake build-essential g++ zlib1g-dev libbz2-dev liblzma-dev
    elif command -v yum >/dev/null 2>&1; then
        echo "Installing dependencies with yum..."
        sudo yum install -y wget tar cmake gcc-c++ make zlib-devel bzip2-devel xz-devel
    elif command -v pacman >/dev/null 2>&1; then
        echo "Installing dependencies with pacman..."
        sudo pacman -S --needed wget tar cmake base-devel zlib bzip2 xz
    else
        echo "Could not detect package manager. Please install manually:"
        echo "- wget, tar, cmake, g++, make"
        echo "- zlib development headers"
        echo "- bzip2 development headers"
        echo "- lzma development headers"
        exit 1
    fi
elif [[ "$OS" == "macos" ]]; then
    if command -v brew >/dev/null 2>&1; then
        echo "Installing dependencies with Homebrew..."
        brew install wget cmake
        # Other tools should be available via Xcode command line tools
        if ! command -v g++ >/dev/null 2>&1; then
            echo "Installing Xcode command line tools..."
            xcode-select --install
        fi
    else
        echo "Homebrew not found. Please install Homebrew first:"
        echo "https://brew.sh"
        exit 1
    fi
fi

# Check if dependencies are now available
echo ""
echo "Checking dependencies..."
MISSING=()

for dep in wget tar cmake make; do
    if ! command -v "$dep" >/dev/null 2>&1; then
        MISSING+=("$dep")
    fi
done

if ! command -v g++ >/dev/null 2>&1 && ! command -v clang++ >/dev/null 2>&1; then
    MISSING+=("g++/clang++")
fi

if [ ${#MISSING[@]} -ne 0 ]; then
    echo "Missing dependencies: ${MISSING[*]}"
    echo "Please install them manually and run this script again."
    exit 1
fi

echo "All dependencies are available!"

# Download and build KenLM
echo ""
echo "Setting up KenLM..."

# Remove existing KenLM if it exists
if [ -d "kenlm" ]; then
    echo "Removing existing KenLM directory..."
    rm -rf kenlm
fi

# Download and extract KenLM
echo "Downloading KenLM..."
wget -O - https://kheafield.com/code/kenlm.tar.gz | tar xz

# Create build directory
echo "Creating build directory..."
mkdir -p kenlm/build
cd kenlm/build

# Configure with cmake
echo "Configuring with cmake..."
cmake ..

# Build with make
echo "Building KenLM (this may take a few minutes)..."
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)

# Make executables executable
chmod +x bin/lmplz bin/build_binary

# Go back to original directory
cd ../..

echo ""
echo "=== Setup Complete ==="
echo "KenLM has been installed and built successfully!"
echo ""
echo "You can now run the language modeling:"
echo "  python language_modeling.py"
echo ""
echo "KenLM binaries are located at:"
echo "  $(pwd)/kenlm/build/bin/lmplz"
echo "  $(pwd)/kenlm/build/bin/build_binary"
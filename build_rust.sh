#!/bin/bash
# Build script for Rust fping extension

set -e

echo "Building Rust fping extension..."

# Check if Rust is installed
if ! command -v rustc &> /dev/null; then
    echo "Rust is not installed. Please install Rust first:"
    echo "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

# Check if maturin is installed
if ! command -v maturin &> /dev/null; then
    echo "Installing maturin..."
    pip install maturin
fi

# Build the Rust extension
echo "Compiling Rust extension..."
maturin build --release

echo "Installing built wheel..."
pip install target/wheels/*.whl --force-reinstall

echo "Rust fping extension built and installed successfully!"
echo "You can now use vaping with the Rust fping implementation."
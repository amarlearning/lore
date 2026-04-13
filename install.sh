#!/bin/bash
set -e

REPO="amarlearning/lore"
INSTALL_DIR="$HOME/.local/bin"

# Create INSTALL_DIR if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Determine OS
OS="linux-latest"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos-latest"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="windows-latest"
fi

echo "Installing Lore for $OS..."

# Download binaries
echo "Downloading lore..."
curl -L "https://github.com/$REPO/releases/latest/download/lore-$OS" -o lore
echo "Downloading lore-daemon..."
curl -L "https://github.com/$REPO/releases/latest/download/lore-daemon-$OS" -o lore-daemon

# Make executable
chmod +x lore lore-daemon

# Move to install directory
mv lore lore-daemon "$INSTALL_DIR/"

echo "Lore installed successfully in $INSTALL_DIR!"

# Add to PATH if not already there
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "Warning: $INSTALL_DIR is not in your PATH."
    echo "Add it to your shell profile (e.g., ~/.zshrc or ~/.bashrc):"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
fi

echo "Run 'lore start' to begin."

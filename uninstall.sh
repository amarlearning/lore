#!/bin/bash
set -e

INSTALL_DIR="$HOME/.local/bin"

echo "Uninstalling Lore..."

# Check if binaries exist
if [ -f "$INSTALL_DIR/lore" ]; then
    rm "$INSTALL_DIR/lore"
    echo "Removed $INSTALL_DIR/lore"
fi

if [ -f "$INSTALL_DIR/lore-daemon" ]; then
    rm "$INSTALL_DIR/lore-daemon"
    echo "Removed $INSTALL_DIR/lore-daemon"
fi

echo "Lore uninstalled successfully!"
echo
echo "Note: This does not remove .lore directories from your projects."
echo "To remove Lore data from a project, delete the .lore directory manually."

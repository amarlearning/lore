#!/bin/bash
set -e
INSTALL_DIR="$HOME/.local/bin"
BUILD_INFO_DIR="$HOME/.local/share/lore"
BUILD_INFO_FILE="$BUILD_INFO_DIR/lore-build-info.json"

echo "Uninstalling Lore..."

# Remove binaries
if [ -f "$INSTALL_DIR/lore" ]; then
    rm "$INSTALL_DIR/lore"
    echo "Removed $INSTALL_DIR/lore"
fi
if [ -f "$INSTALL_DIR/lore-daemon" ]; then
    rm "$INSTALL_DIR/lore-daemon"
    echo "Removed $INSTALL_DIR/lore-daemon"
fi

# Remove build info file
if [ -f "$BUILD_INFO_FILE" ]; then
    rm "$BUILD_INFO_FILE"
    echo "Removed $BUILD_INFO_FILE"
fi

# Remove build info dir if empty
if [ -d "$BUILD_INFO_DIR" ] && [ -z "$(ls -A "$BUILD_INFO_DIR")" ]; then
    rmdir "$BUILD_INFO_DIR"
    echo "Removed $BUILD_INFO_DIR"
fi

echo "Lore uninstalled successfully!"
echo
echo "Note: This does not remove .lore directories from your projects."
echo "To remove Lore data from a project, delete the .lore directory manually."

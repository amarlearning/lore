#!/bin/bash
set -e

REPO="amarlearning/lore"
INSTALL_DIR="$HOME/.local/bin"
BUILD_INFO_DIR="$HOME/.local/share/lore"
BUILD_INFO_FILE="$BUILD_INFO_DIR/lore-build-info.json"

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

# Write installed build metadata for `lore version`
mkdir -p "$BUILD_INFO_DIR"

SHORT_SHA="unknown"
COMMIT_DATE="unknown-date"

RELEASE_JSON=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" || true)
if [[ -n "$RELEASE_JSON" ]]; then
    TARGET_COMMITISH=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("target_commitish",""))' <<<"$RELEASE_JSON")
    if [[ -n "$TARGET_COMMITISH" ]]; then
        COMMIT_JSON=$(curl -fsSL "https://api.github.com/repos/$REPO/commits/$TARGET_COMMITISH" || true)
        if [[ -n "$COMMIT_JSON" ]]; then
            SHORT_SHA=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("sha","unknown")[:7])' <<<"$COMMIT_JSON")
            COMMIT_DATE=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("commit",{}).get("committer",{}).get("date","unknown-date")[:10])' <<<"$COMMIT_JSON")
        fi
    fi
fi

cat > "$BUILD_INFO_FILE" <<EOF
{
  "short_sha": "$SHORT_SHA",
  "date": "$COMMIT_DATE"
}
EOF

# Also keep a copy next to the executable for portable lookup.
cp "$BUILD_INFO_FILE" "$INSTALL_DIR/lore-build-info.json"

echo "Lore installed successfully in $INSTALL_DIR!"

# Add to PATH if not already there
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "Warning: $INSTALL_DIR is not in your PATH."
    echo "Add it to your shell profile (e.g., ~/.zshrc or ~/.bashrc):"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
fi

echo "Run 'lore start' to begin."

#!/bin/bash
# Discover app signatures from installed macOS applications
# Outputs YAML format ready for the app registry

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

discover_app() {
    local app_path="$1"
    local app_name=$(basename "$app_path" .app)
    local info_plist="$app_path/Contents/Info.plist"

    if [[ ! -f "$info_plist" ]]; then
        echo "# Skipping $app_name - no Info.plist" >&2
        return
    fi

    # Extract bundle ID
    local bundle_id=$(/usr/libexec/PlistBuddy -c "Print :CFBundleIdentifier" "$info_plist" 2>/dev/null || echo "")
    if [[ -z "$bundle_id" ]]; then
        echo "# Skipping $app_name - no bundle ID" >&2
        return
    fi

    # Extract version
    local version=$(/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "$info_plist" 2>/dev/null || echo "unknown")

    # Extract executable name
    local executable=$(/usr/libexec/PlistBuddy -c "Print :CFBundleExecutable" "$info_plist" 2>/dev/null || echo "")

    # Get code signature info
    local team_id=""
    local signer=""
    local codesign_output=$(codesign -dv "$app_path" 2>&1 || true)

    if echo "$codesign_output" | grep -q "TeamIdentifier="; then
        team_id=$(echo "$codesign_output" | grep "TeamIdentifier=" | cut -d= -f2)
    fi

    if echo "$codesign_output" | grep -q "Authority="; then
        signer=$(echo "$codesign_output" | grep "Authority=" | head -1 | cut -d= -f2)
    fi

    # Try to get vendor from copyright
    local vendor=$(/usr/libexec/PlistBuddy -c "Print :NSHumanReadableCopyright" "$info_plist" 2>/dev/null | grep -oE "©.*" | sed 's/© [0-9]* //' || echo "")

    # Generate app_id from bundle_id or name
    local app_id=$(echo "$app_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')

    # Output YAML
    echo "# $app_name"
    echo "# Discovered from: $app_path"
    echo ""
    echo "app_id: $app_id"
    echo "name: \"$app_name\""
    [[ -n "$vendor" ]] && echo "vendor: \"$vendor\""
    echo "category: other  # TODO: categorize manually"
    echo ""
    echo "signatures:"
    echo "  macos:"
    echo "    bundle_id: \"$bundle_id\""
    [[ -n "$team_id" && "$team_id" != "not set" ]] && echo "    team_id: \"$team_id\""
    echo "    paths:"
    echo "      - \"$app_path\""
    [[ -n "$executable" ]] && echo "    executable_name: \"$executable\""
    echo ""
    echo "metadata:"
    echo "  version_discovered: \"$version\""
    echo "  discovered_at: \"$(date +%Y-%m-%d)\""
    echo ""
    echo "---"
    echo ""
}

discover_all_apps() {
    local search_dirs=(
        "/Applications"
        "$HOME/Applications"
    )

    echo "# OISP App Registry - macOS App Discovery"
    echo "# Generated: $(date)"
    echo "# Machine: $(hostname)"
    echo ""
    echo "---"
    echo ""

    for dir in "${search_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            find "$dir" -maxdepth 2 -name "*.app" -type d 2>/dev/null | while read -r app; do
                discover_app "$app"
            done
        fi
    done
}

discover_single_app() {
    local app_path="$1"

    if [[ ! -d "$app_path" ]]; then
        echo "Error: $app_path is not a directory" >&2
        exit 1
    fi

    discover_app "$app_path"
}

# Main
case "${1:-all}" in
    all)
        discover_all_apps
        ;;
    *)
        if [[ -d "$1" ]]; then
            discover_single_app "$1"
        else
            echo "Usage: $0 [all | /path/to/App.app]"
            exit 1
        fi
        ;;
esac

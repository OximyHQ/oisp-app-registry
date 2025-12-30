#!/bin/bash
# OISP App Registry Scanner
# Scans your installed apps and opens a web UI for contribution
#
# Usage (remote):
#   curl -fsSL https://raw.githubusercontent.com/oximyhq/oisp-app-registry/main/scan.sh | bash
#
# Usage (local):
#   ./scan.sh

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}OISP App Registry Scanner${NC}"
echo ""

# Detect if running locally or via curl
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" 2>/dev/null)" 2>/dev/null && pwd)"
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/scripts/discover-apps.py" ]]; then
    DISCOVER_SCRIPT="$SCRIPT_DIR/scripts/discover-apps.py"
    VIEWER_HTML="$SCRIPT_DIR/scripts/viewer.html"
    echo "Running locally from $SCRIPT_DIR"
else
    TMPDIR=$(mktemp -d)
    trap "rm -rf $TMPDIR" EXIT

    BASE_URL="https://raw.githubusercontent.com/oximyhq/oisp-app-registry/main"
    echo "Downloading scanner..."
    curl -fsSL "$BASE_URL/scripts/discover-apps.py" -o "$TMPDIR/discover-apps.py"
    curl -fsSL "$BASE_URL/scripts/viewer.html" -o "$TMPDIR/viewer.html"

    DISCOVER_SCRIPT="$TMPDIR/discover-apps.py"
    VIEWER_HTML="$TMPDIR/viewer.html"
fi

OUTPUT_DIR=$(mktemp -d)

echo "Scanning ALL installed applications..."
# Scan all apps (not just AI), with icons
python3 "$DISCOVER_SCRIPT" --with-icons --json > "$OUTPUT_DIR/apps.json" 2>/dev/null

TOTAL=$(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/apps.json')); print(d.get('total_apps', 0))")
AI_COUNT=$(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/apps.json')); print(d.get('ai_apps', 0))")

echo -e "${GREEN}Found $TOTAL apps ($AI_COUNT identified as AI-related)${NC}"
echo ""

# Inject apps data into HTML
python3 << EOF
html = open('$VIEWER_HTML').read()
apps_json = open('$OUTPUT_DIR/apps.json').read()
html = html.replace('__APPS_DATA__', apps_json)
open('$OUTPUT_DIR/scanner.html', 'w').write(html)
EOF

echo "Opening scanner in 3..."
sleep 1
echo "2..."
sleep 1
echo "1..."
sleep 1
case "$(uname -s)" in
    Darwin)  open "$OUTPUT_DIR/scanner.html" ;;
    Linux)   xdg-open "$OUTPUT_DIR/scanner.html" 2>/dev/null || sensible-browser "$OUTPUT_DIR/scanner.html" ;;
    MINGW*|MSYS*|CYGWIN*) start "$OUTPUT_DIR/scanner.html" ;;
esac

echo ""
echo -e "${GREEN}Scanner opened in your browser!${NC}"
echo ""
echo "How to contribute:"
echo "  1. Review apps and set their AI status"
echo "  2. Skip any apps you don't want to include"
echo "  3. Click 'Export ZIP' to download"
echo "  4. Click 'Upload to GitHub' to submit your PR"
echo ""
echo -e "${BLUE}Press Ctrl+C when done.${NC}"

while true; do sleep 60; done

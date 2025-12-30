# OISP App Registry

Community-driven registry of AI-enabled applications.

## Contribute Your Apps

**One command:**

```bash
curl -fsSL https://raw.githubusercontent.com/oximyhq/oisp-app-registry/main/scan.sh | bash
```

This will:
1. Scan all installed apps on your machine
2. Open a web UI in your browser
3. Let you mark apps as AI-native, AI-enabled, etc.
4. Export a single ZIP file with all apps + icons
5. Upload the ZIP to GitHub → bot extracts and creates PR

## Structure

```
oisp-app-registry/
├── apps/              # App profiles (YAML)
├── icons/             # App icons (PNG)
├── contributions/     # Drop ZIP files here for auto-processing
├── apps.json          # Combined JSON (auto-generated)
├── scan.sh            # Scanner entry point
└── scripts/
    ├── discover-apps.py  # App discovery
    ├── viewer.html       # Web UI
    └── build.py          # Generate apps.json
```

## App Format

```yaml
id: cursor
name: Cursor
vendor: Anysphere Inc.
ai: native

signatures:
  macos:
    bundle_id: com.todesktop.230313mzl4w4u92
    team_id: VDXQ22DGB9
  windows:
    exe: Cursor.exe
  linux:
    exe: cursor

providers:
  - openai
  - anthropic
```

## AI Status

| Status | Description |
|--------|-------------|
| `native` | Built for AI (Cursor, ChatGPT, Claude) |
| `enabled` | Has AI features (Notion AI, Raycast) |
| `host` | Hosts AI extensions (VS Code, browsers) |
| `none` | No AI features |

## Sensor Integration

The sensor fetches `apps.json` on startup:

```
https://raw.githubusercontent.com/oximyhq/oisp-app-registry/main/apps.json
```

Process matching:
- **macOS**: `bundle_id` + `team_id`
- **Windows**: `exe` + `publisher`
- **Linux**: `exe`

## GitHub Actions

- **On ZIP upload**: Extracts apps + icons, validates, commits to PR
- **On PR**: Validates YAML structure and checks for duplicate IDs
- **On merge**: Auto-regenerates `apps.json`

## License

MIT

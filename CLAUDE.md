# OISP App Registry

Community-driven registry of AI-enabled applications for OISP Sensor process matching.

## Quick Reference

```bash
# Run the contribution scanner
./scan.sh                   # Scans installed apps, opens web UI

# Build combined JSON
python scripts/build.py     # Regenerates apps.json from apps/*.yaml

# Validate app definitions
python scripts/validate.py  # Check YAML structure
```

## Repository Structure

```
apps/                       # App profiles (one YAML per app)
├── cursor.yaml
├── chatgpt.yaml
└── ...

icons/                      # App icons (PNG, named by app ID)

contributions/              # Drop ZIP files here for auto-processing

scripts/
├── discover-apps.py        # App discovery for scanner
├── viewer.html             # Web UI for marking apps
├── build.py                # Generate apps.json
└── validate.py             # YAML validation

apps.json                   # Combined registry (auto-generated, DO NOT EDIT)
scan.sh                     # Entry point for contributors
```

## App YAML Format

```yaml
id: cursor                  # Unique identifier (lowercase, hyphens)
name: Cursor
vendor: Anysphere Inc.
ai: native                  # native | enabled | host | none

signatures:
  macos:
    bundle_id: com.todesktop.230313mzl4w4u92
    team_id: VDXQ22DGB9
  windows:
    exe: Cursor.exe
  linux:
    exe: cursor

providers:                  # Which AI providers this app uses
  - openai
  - anthropic
```

## AI Status Values

| Status | Description | Examples |
|--------|-------------|----------|
| `native` | Built for AI | Cursor, ChatGPT, Claude |
| `enabled` | Has AI features | Notion AI, Raycast |
| `host` | Hosts AI extensions | VS Code, browsers |
| `none` | No AI features | - |

## Common Tasks

**Add new app:**
1. Create `apps/<app-id>.yaml`
2. Add icon to `icons/<app-id>.png`
3. Run `python scripts/build.py`
4. Submit PR

**Process contribution ZIP:**
1. Drop ZIP in `contributions/`
2. GitHub Action extracts and creates PR
3. Review and merge

**Update app.json:**
```bash
python scripts/build.py
# Commit the updated apps.json
```

## Sensor Integration

The sensor fetches `apps.json` on startup from:
```
https://raw.githubusercontent.com/oximyhq/oisp-app-registry/main/apps.json
```

Process matching by platform:
- **macOS**: `bundle_id` + `team_id`
- **Windows**: `exe` + `publisher`
- **Linux**: `exe`

## Validation Rules

- `id` must be unique, lowercase, hyphens only
- `ai` must be one of: `native`, `enabled`, `host`, `none`
- At least one platform signature required
- Icon file must exist if referenced

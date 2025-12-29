# OISP App Registry

The official registry of AI-enabled applications for the OISP ecosystem.

## Purpose

This registry enables the OISP Sensor to identify which application is making AI requests. Without app identification, you only see "OpenAI traffic." With it, you see "Cursor made 47 requests, GitHub Copilot made 23."

## Structure

```
oisp-app-registry/
├── apps/                    # Individual app profiles (YAML)
│   ├── cursor.yaml
│   ├── github-copilot.yaml
│   └── ...
├── schema/                  # JSON Schema for validation
│   └── app-profile.schema.json
├── scripts/                 # Build and validation scripts
│   └── build-bundle.py
├── generated/               # Generated bundle for sensor consumption
│   └── apps-bundle.json
└── registry.yaml            # Master index of all apps
```

## App Profile Schema

Each app profile contains:

- **Identification**: App ID, name, vendor, category
- **Signatures**: Platform-specific identifiers (bundle ID, paths, code signatures)
- **Traffic Patterns**: Expected AI providers, direct vs backend patterns
- **Metadata**: Website, documentation, icon

## Three-Tier Classification

| Tier | Name | Description |
|------|------|-------------|
| 0 | Unknown | Process found, no app match. Suspicious by default. |
| 1 | Identified | Matched by signature. Basic metadata available. |
| 2 | Profiled | Full profile with expected behavior. Baseline for anomaly detection. |

## Categories

- `dev_tools` - IDEs, code editors, coding assistants
- `productivity` - Note-taking, writing, office tools
- `chat` - Conversational AI interfaces
- `creative` - Image, video, audio generation
- `cli` - Command-line tools
- `browser` - Browser extensions
- `enterprise` - Business/enterprise applications

## Contributing

To add a new app:

1. Create `apps/<app-id>.yaml` following the schema
2. Run `scripts/validate.py` to check your profile
3. Submit a pull request

## License

Apache 2.0

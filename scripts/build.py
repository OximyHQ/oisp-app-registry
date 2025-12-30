#!/usr/bin/env python3
"""
Build apps.json from individual YAML files.
Run this after adding/modifying app profiles.

Usage:
    python scripts/build.py
"""

import json
import yaml
from pathlib import Path

def main():
    apps_dir = Path(__file__).parent.parent / "apps"
    output_file = Path(__file__).parent.parent / "apps.json"

    apps = []

    for yaml_file in sorted(apps_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            app = yaml.safe_load(f)
            apps.append(app)

    output = {
        "version": "1.0.0",
        "apps": apps
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {output_file} with {len(apps)} apps")

if __name__ == "__main__":
    main()

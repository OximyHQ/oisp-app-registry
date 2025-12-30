#!/usr/bin/env python3
"""
OISP App Discovery Script
Discovers installed applications and their signatures.
Run on sensor startup to build/update the app registry.

Usage:
    python discover-apps.py                    # Discover all apps, output JSON
    python discover-apps.py --yaml             # Output as YAML files
    python discover-apps.py --yaml-dir ./apps  # Write YAML files to directory
    python discover-apps.py --submit URL       # Submit to registry endpoint
    python discover-apps.py --ai-only          # Only apps likely to use AI
    python discover-apps.py --with-icons       # Extract app icons as PNG
"""

import json
import os
import platform
import plistlib
import re
import subprocess
import sys
import base64
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import hashlib

# Known AI-related apps and keywords
AI_APP_KEYWORDS = [
    'cursor', 'copilot', 'cody', 'claude', 'chatgpt', 'openai', 'anthropic',
    'gpt', 'gemini', 'bard', 'perplexity', 'phind', 'tabnine', 'kite',
    'windsurf', 'continue', 'aider', 'codeium', 'sourcegraph', 'pieces',
    'notion', 'obsidian', 'grammarly', 'jasper', 'copy.ai', 'writesonic',
    'midjourney', 'dall-e', 'stable-diffusion', 'runway', 'luma',
    'whisper', 'otter', 'descript', 'krisp',
    'raycast', 'alfred',  # Have AI features
    'warp',  # AI terminal
    'fig',   # Now part of AWS, had AI
    'zed',   # AI code editor
]

# Apps that host AI extensions (not AI themselves but important)
AI_HOST_APPS = [
    'visual studio code', 'vscode', 'intellij', 'pycharm', 'webstorm',
    'goland', 'rider', 'clion', 'datagrip', 'rubymine', 'phpstorm',
    'android studio', 'xcode', 'sublime text', 'atom', 'vim', 'neovim',
    'emacs', 'nova', 'bbedit', 'textmate',
]

@dataclass
class AppSignature:
    """Platform-specific app signature"""
    bundle_id: Optional[str] = None
    team_id: Optional[str] = None
    paths: List[str] = field(default_factory=list)
    executable_name: Optional[str] = None
    publisher: Optional[str] = None
    version: Optional[str] = None

@dataclass
class DiscoveredApp:
    """Discovered application with all metadata"""
    app_id: str
    name: str
    vendor: Optional[str] = None
    category: str = "other"
    path: str = ""

    # Platform signatures
    macos: Optional[AppSignature] = None
    windows: Optional[AppSignature] = None
    linux: Optional[AppSignature] = None

    # Icon
    icon_path: Optional[str] = None
    icon_base64: Optional[str] = None

    # Metadata
    is_ai_app: bool = False
    is_ai_host: bool = False
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    machine_id: str = field(default_factory=lambda: hashlib.sha256(platform.node().encode()).hexdigest()[:12])

    def to_dict(self, include_icon: bool = True) -> Dict[str, Any]:
        """Convert to dictionary, removing None values"""
        d = asdict(self)
        # Clean up None values and empty signatures
        if d.get('macos') and not any(v for v in d['macos'].values() if v):
            d['macos'] = None
        if d.get('windows') and not any(v for v in d['windows'].values() if v):
            d['windows'] = None
        if d.get('linux') and not any(v for v in d['linux'].values() if v):
            d['linux'] = None
        # Remove icon if not requested (for smaller JSON in apps.json)
        if not include_icon:
            d.pop('icon_base64', None)
        return {k: v for k, v in d.items() if v is not None}


def is_ai_related(name: str, bundle_id: str = "") -> tuple[bool, bool]:
    """Check if app is AI-related or hosts AI extensions"""
    name_lower = name.lower()
    bundle_lower = bundle_id.lower() if bundle_id else ""

    # Check if it's an AI app
    for keyword in AI_APP_KEYWORDS:
        if keyword in name_lower or keyword in bundle_lower:
            return True, False

    # Check if it hosts AI extensions
    for host in AI_HOST_APPS:
        if host in name_lower:
            return False, True

    return False, False


def generate_app_id(name: str) -> str:
    """Generate a valid app_id from name"""
    app_id = name.lower()
    app_id = re.sub(r'[^a-z0-9]+', '-', app_id)
    app_id = app_id.strip('-')
    return app_id


def run_command(cmd: List[str], timeout: int = 10) -> Optional[str]:
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def run_command_binary(cmd: List[str], timeout: int = 30) -> Optional[bytes]:
    """Run a shell command and return binary output"""
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return result.stdout if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


class MacOSDiscoverer:
    """Discover apps on macOS"""

    def __init__(self, extract_icons: bool = False, icons_dir: Optional[Path] = None):
        self.extract_icons = extract_icons
        self.icons_dir = icons_dir
        self.search_paths = [
            Path("/Applications"),
            Path.home() / "Applications",
            Path("/System/Applications"),
        ]

    def discover_all(self) -> List[DiscoveredApp]:
        """Discover all installed applications"""
        apps = []
        seen_bundle_ids = set()

        for search_path in self.search_paths:
            if not search_path.exists():
                continue

            # Find all .app bundles (but not too deep)
            for app_path in search_path.glob("*.app"):
                app = self._discover_app(app_path)
                if app and app.macos and app.macos.bundle_id:
                    if app.macos.bundle_id not in seen_bundle_ids:
                        seen_bundle_ids.add(app.macos.bundle_id)
                        apps.append(app)

            # Also check one level deep (for folders like "Utilities")
            for subdir in search_path.iterdir():
                if subdir.is_dir() and not subdir.suffix == '.app':
                    for app_path in subdir.glob("*.app"):
                        app = self._discover_app(app_path)
                        if app and app.macos and app.macos.bundle_id:
                            if app.macos.bundle_id not in seen_bundle_ids:
                                seen_bundle_ids.add(app.macos.bundle_id)
                                apps.append(app)

        return apps

    def _discover_app(self, app_path: Path) -> Optional[DiscoveredApp]:
        """Extract information from a single .app bundle"""
        info_plist = app_path / "Contents" / "Info.plist"
        if not info_plist.exists():
            return None

        try:
            with open(info_plist, 'rb') as f:
                plist = plistlib.load(f)
        except Exception:
            return None

        bundle_id = plist.get('CFBundleIdentifier', '')
        if not bundle_id:
            return None

        name = plist.get('CFBundleName') or plist.get('CFBundleDisplayName') or app_path.stem
        version = plist.get('CFBundleShortVersionString', '')
        executable = plist.get('CFBundleExecutable', '')

        # Get vendor from copyright
        vendor = None
        copyright_str = plist.get('NSHumanReadableCopyright', '')
        if copyright_str:
            match = re.search(r'©\s*\d*\s*(.+?)(?:\.|All rights|$)', copyright_str)
            if match:
                vendor = match.group(1).strip()

        # Get code signature info
        team_id = self._get_team_id(app_path)

        # Check if AI-related
        is_ai, is_host = is_ai_related(name, bundle_id)

        # Determine category
        category = "other"
        if is_ai:
            if any(kw in name.lower() for kw in ['code', 'ide', 'cursor', 'copilot', 'cody', 'studio', 'zed']):
                category = "dev_tools"
            elif any(kw in name.lower() for kw in ['chat', 'claude', 'gpt', 'gemini', 'perplexity']):
                category = "chat"
            elif any(kw in name.lower() for kw in ['notion', 'obsidian', 'grammarly']):
                category = "productivity"
            elif any(kw in name.lower() for kw in ['midjourney', 'dall', 'stable', 'runway']):
                category = "creative"
        elif is_host:
            category = "dev_tools"

        signature = AppSignature(
            bundle_id=bundle_id,
            team_id=team_id,
            paths=[str(app_path)],
            executable_name=executable,
            version=version,
        )

        app = DiscoveredApp(
            app_id=generate_app_id(name),
            name=name,
            vendor=vendor,
            category=category,
            path=str(app_path),
            macos=signature,
            is_ai_app=is_ai,
            is_ai_host=is_host,
        )

        # Extract icon if requested
        if self.extract_icons:
            icon_data = self._extract_icon(app_path, plist)
            if icon_data:
                if self.icons_dir:
                    icon_path = self.icons_dir / f"{app.app_id}.png"
                    icon_path.write_bytes(icon_data)
                    app.icon_path = str(icon_path)
                else:
                    app.icon_base64 = base64.b64encode(icon_data).decode('utf-8')

        return app

    def _get_team_id(self, app_path: Path) -> Optional[str]:
        """Get Apple Developer Team ID from code signature"""
        result = subprocess.run(
            ['codesign', '-dv', str(app_path)],
            capture_output=True, text=True, timeout=10
        )
        output = result.stderr  # codesign outputs to stderr
        if output:
            for line in output.split('\n'):
                if 'TeamIdentifier=' in line:
                    team_id = line.split('=')[1].strip()
                    if team_id and team_id != 'not set':
                        return team_id
        return None

    def _extract_icon(self, app_path: Path, plist: dict) -> Optional[bytes]:
        """Extract app icon as PNG"""
        # Get icon file name from plist
        icon_file = plist.get('CFBundleIconFile', '')
        if not icon_file:
            icon_file = plist.get('CFBundleIconName', '')
        if not icon_file:
            return None

        # Add .icns extension if missing
        if not icon_file.endswith('.icns'):
            icon_file += '.icns'

        # Find the icon file
        resources_path = app_path / "Contents" / "Resources"
        icon_path = resources_path / icon_file

        if not icon_path.exists():
            # Try without extension modification
            icon_file = plist.get('CFBundleIconFile', '')
            if icon_file:
                icon_path = resources_path / icon_file
                if not icon_path.exists():
                    # List resources to find any icns file
                    icns_files = list(resources_path.glob("*.icns"))
                    if icns_files:
                        icon_path = icns_files[0]
                    else:
                        return None

        if not icon_path.exists():
            return None

        # Convert icns to png using sips (macOS built-in)
        try:
            # Create a temp file for output
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name

            result = subprocess.run(
                ['sips', '-s', 'format', 'png', '-z', '128', '128', str(icon_path), '--out', tmp_path],
                capture_output=True, timeout=10
            )

            if result.returncode == 0 and Path(tmp_path).exists():
                png_data = Path(tmp_path).read_bytes()
                os.unlink(tmp_path)
                return png_data
            else:
                if Path(tmp_path).exists():
                    os.unlink(tmp_path)
        except Exception as e:
            print(f"Failed to extract icon for {app_path.name}: {e}", file=sys.stderr)

        return None


class WindowsDiscoverer:
    """Discover apps on Windows"""

    def __init__(self, extract_icons: bool = False, icons_dir: Optional[Path] = None):
        self.extract_icons = extract_icons
        self.icons_dir = icons_dir

    def discover_all(self) -> List[DiscoveredApp]:
        """Discover installed applications on Windows"""
        apps = []

        search_paths = [
            Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')),
            Path(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')),
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs',
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for exe_path in search_path.rglob("*.exe"):
                if any(skip in exe_path.name.lower() for skip in ['uninstall', 'update', 'setup', 'installer']):
                    continue

                app = self._discover_app(exe_path)
                if app:
                    apps.append(app)

        return apps

    def _discover_app(self, exe_path: Path) -> Optional[DiscoveredApp]:
        """Extract information from a Windows executable"""
        name = exe_path.stem

        is_ai, is_host = is_ai_related(name)
        if not is_ai and not is_host:
            return None

        signature = AppSignature(
            paths=[str(exe_path)],
            executable_name=exe_path.name,
        )

        return DiscoveredApp(
            app_id=generate_app_id(name),
            name=name,
            category="other",
            path=str(exe_path),
            windows=signature,
            is_ai_app=is_ai,
            is_ai_host=is_host,
        )


class LinuxDiscoverer:
    """Discover apps on Linux"""

    def __init__(self, extract_icons: bool = False, icons_dir: Optional[Path] = None):
        self.extract_icons = extract_icons
        self.icons_dir = icons_dir

    def discover_all(self) -> List[DiscoveredApp]:
        """Discover installed applications on Linux"""
        apps = []

        desktop_dirs = [
            Path('/usr/share/applications'),
            Path('/usr/local/share/applications'),
            Path.home() / '.local/share/applications',
        ]

        for desktop_dir in desktop_dirs:
            if not desktop_dir.exists():
                continue

            for desktop_file in desktop_dir.glob('*.desktop'):
                app = self._parse_desktop_file(desktop_file)
                if app:
                    apps.append(app)

        return apps

    def _parse_desktop_file(self, desktop_file: Path) -> Optional[DiscoveredApp]:
        """Parse a .desktop file"""
        try:
            content = desktop_file.read_text()
        except Exception:
            return None

        name = None
        exec_path = None

        for line in content.split('\n'):
            if line.startswith('Name='):
                name = line.split('=', 1)[1].strip()
            elif line.startswith('Exec='):
                exec_path = line.split('=', 1)[1].split()[0].strip()

        if not name:
            return None

        is_ai, is_host = is_ai_related(name)

        signature = AppSignature(
            paths=[exec_path] if exec_path else [],
            executable_name=Path(exec_path).name if exec_path else None,
        )

        return DiscoveredApp(
            app_id=generate_app_id(name),
            name=name,
            category="other",
            path=exec_path or "",
            linux=signature,
            is_ai_app=is_ai,
            is_ai_host=is_host,
        )


def discover_apps(ai_only: bool = False, extract_icons: bool = False, icons_dir: Optional[Path] = None) -> List[DiscoveredApp]:
    """Discover apps on the current platform"""
    system = platform.system()

    if system == 'Darwin':
        discoverer = MacOSDiscoverer(extract_icons=extract_icons, icons_dir=icons_dir)
    elif system == 'Windows':
        discoverer = WindowsDiscoverer(extract_icons=extract_icons, icons_dir=icons_dir)
    elif system == 'Linux':
        discoverer = LinuxDiscoverer(extract_icons=extract_icons, icons_dir=icons_dir)
    else:
        print(f"Unsupported platform: {system}", file=sys.stderr)
        return []

    apps = discoverer.discover_all()

    if ai_only:
        apps = [a for a in apps if a.is_ai_app or a.is_ai_host]

    # Sort: AI apps first, then by name
    apps.sort(key=lambda a: (not a.is_ai_app, not a.is_ai_host, a.name.lower()))

    return apps


def to_yaml(app: DiscoveredApp) -> str:
    """Convert app to YAML format"""
    lines = [
        f"# {app.name}",
        f"# Discovered from: {app.path}",
        "",
        f"app_id: {app.app_id}",
        f"name: \"{app.name}\"",
    ]

    if app.vendor:
        lines.append(f"vendor: \"{app.vendor}\"")

    lines.append(f"category: {app.category}")
    lines.append("")
    lines.append("signatures:")

    if app.macos:
        lines.append("  macos:")
        if app.macos.bundle_id:
            lines.append(f"    bundle_id: \"{app.macos.bundle_id}\"")
        if app.macos.team_id:
            lines.append(f"    team_id: \"{app.macos.team_id}\"")
        if app.macos.paths:
            lines.append("    paths:")
            for path in app.macos.paths:
                lines.append(f"      - \"{path}\"")
        if app.macos.executable_name:
            lines.append(f"    executable_name: \"{app.macos.executable_name}\"")

    if app.windows:
        lines.append("  windows:")
        if app.windows.paths:
            lines.append("    paths:")
            for path in app.windows.paths:
                lines.append(f"      - \"{path}\"")
        if app.windows.executable_name:
            lines.append(f"    executable_name: \"{app.windows.executable_name}\"")

    if app.linux:
        lines.append("  linux:")
        if app.linux.paths:
            lines.append("    paths:")
            for path in app.linux.paths:
                lines.append(f"      - \"{path}\"")
        if app.linux.executable_name:
            lines.append(f"    executable_name: \"{app.linux.executable_name}\"")

    lines.extend([
        "",
        "metadata:",
        f"  discovered_at: \"{app.discovered_at}\"",
    ])

    if app.macos and app.macos.version:
        lines.append(f"  version_discovered: \"{app.macos.version}\"")

    if app.is_ai_app:
        lines.append("  is_ai_app: true")
    if app.is_ai_host:
        lines.append("  is_ai_host: true")

    if app.icon_path:
        lines.append(f"  icon: \"{Path(app.icon_path).name}\"")

    lines.append("")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Discover installed applications')
    parser.add_argument('--yaml', action='store_true', help='Output as YAML')
    parser.add_argument('--yaml-dir', type=str, help='Write YAML files to directory')
    parser.add_argument('--ai-only', action='store_true', help='Only AI-related apps')
    parser.add_argument('--with-icons', action='store_true', help='Extract app icons as PNG')
    parser.add_argument('--icons-dir', type=str, help='Directory to save icons')
    parser.add_argument('--submit', type=str, metavar='URL', help='Submit to registry endpoint')
    parser.add_argument('--json', action='store_true', help='Output as JSON (default)')
    args = parser.parse_args()

    icons_dir = None
    if args.icons_dir:
        icons_dir = Path(args.icons_dir)
        icons_dir.mkdir(parents=True, exist_ok=True)
    elif args.yaml_dir and args.with_icons:
        icons_dir = Path(args.yaml_dir) / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)

    print(f"Discovering apps on {platform.system()}...", file=sys.stderr)
    apps = discover_apps(
        ai_only=args.ai_only,
        extract_icons=args.with_icons,
        icons_dir=icons_dir
    )
    print(f"Found {len(apps)} apps", file=sys.stderr)

    ai_apps = [a for a in apps if a.is_ai_app]
    host_apps = [a for a in apps if a.is_ai_host]
    print(f"  - AI apps: {len(ai_apps)}", file=sys.stderr)
    print(f"  - AI host apps: {len(host_apps)}", file=sys.stderr)

    if args.yaml_dir:
        output_dir = Path(args.yaml_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for app in apps:
            yaml_path = output_dir / f"{app.app_id}.yaml"
            yaml_path.write_text(to_yaml(app))
            print(f"Wrote {yaml_path}", file=sys.stderr)

    elif args.yaml:
        for app in apps:
            print(to_yaml(app))
            print("---")

    elif args.submit:
        import urllib.request
        data = json.dumps([a.to_dict() for a in apps]).encode('utf-8')
        req = urllib.request.Request(
            args.submit,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                print(f"Submitted to {args.submit}: {response.status}", file=sys.stderr)
        except Exception as e:
            print(f"Failed to submit: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        # Default: JSON output
        output = {
            "platform": platform.system(),
            "hostname": platform.node(),
            "discovered_at": datetime.now().isoformat(),
            "total_apps": len(apps),
            "ai_apps": len(ai_apps),
            "ai_host_apps": len(host_apps),
            "apps": [a.to_dict() for a in apps]
        }
        print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()

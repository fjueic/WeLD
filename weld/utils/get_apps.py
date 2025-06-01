import os
from configparser import ConfigParser
from pathlib import Path


def get_applications():
    desktop_dirs = [
        Path("/usr/share/applications"),
        Path.home() / ".local/share/applications",
    ]
    _all_icons_cache = []

    def resolve_icon(icon_name: str) -> str:
        """Recursively find icons by name and common extension."""
        directories = ["/usr/share/icons/", "/usr/share/pixmaps/"]
        extensions = [".svg", ".png", ".xpm"]

        # Only populate cache if it's empty
        if not _all_icons_cache:
            for directory in directories:
                for root, _, files in os.walk(directory):
                    for file in files:
                        _all_icons_cache.append(os.path.join(root, file))

        # Search in cache
        for ext in extensions:
            target_name = icon_name + ext
            for path in _all_icons_cache:
                if path.endswith("/" + target_name):  # safer match
                    return path

        return ""

    apps = []
    for directory in desktop_dirs:
        if not directory.exists():
            continue
        for file in directory.glob("*.desktop"):
            parser = ConfigParser(strict=False, interpolation=None)
            parser.read(file, encoding="utf-8")
            if "Desktop Entry" in parser:
                entry = parser["Desktop Entry"]
                if entry.get("NoDisplay", "false").lower() == "true":
                    continue
                name = entry.get("Name")
                exec_cmd = entry.get("Exec")
                icon = entry.get("Icon")
                if name and exec_cmd:
                    exec_clean = exec_cmd.split(" ")[0]  # remove % placeholders
                    icon_path = resolve_icon(icon) if icon else ""
                    apps.append(
                        {
                            "name": name,
                            "exec": exec_clean,
                            "icon": icon_path,
                        }
                    )

    return sorted(apps, key=lambda x: x["name"].lower())


if __name__ == "__main__":
    # Example usage
    import json

    apps = get_applications()
    print(json.dumps(apps))

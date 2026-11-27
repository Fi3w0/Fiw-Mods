#!/usr/bin/env python3
"""Update the FIW Mods README from Modrinth."""

import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODS = ROOT / "mods.json"
README = ROOT / "README.md"
START = "<!-- stats:start -->"
END = "<!-- stats:end -->"
USER_AGENT = "fiw-mods/1.0 (https://github.com/Fi3w0/fiw-mods)"
TOKEN = os.environ.get("MODRINTH_TOKEN")

LOADERS = {
    "fabric": "Fabric",
    "neoforge": "NeoForge",
    "forge": "Forge",
    "quilt": "Quilt",
}


def get_json(url):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def minecraft_key(version):
    return tuple(int(part) for part in re.findall(r"\d+", version))


def format_versions(versions):
    chunks = [", ".join(versions[index:index + 3]) for index in range(0, len(versions), 3)]
    return "<br>".join(chunks) or "—"


def main():
    mods = json.loads(MODS.read_text())
    results = []
    total = 0

    for mod in mods:
        name = mod["name"]
        slug = mod["slug"]
        repo = mod["repo"]
        summary = mod.get("summary", "—")
        modrinth = f"https://modrinth.com/mod/{slug}"
        github = f"https://github.com/{repo}"

        try:
            project = get_json(f"https://api.modrinth.com/v2/project/{slug}")
            versions = get_json(f"https://api.modrinth.com/v2/project/{slug}/version")
        except Exception as error:
            print(f"{slug}: {error}")
            results.append({
                "downloads": -1,
                "name": name,
                "row": f"| [{name}]({github}) | {summary} | — | — | — | — |",
            })
            continue

        downloads = project.get("downloads", 0)
        total += downloads
        latest = max(versions, key=lambda v: v.get("date_published", "")) if versions else None
        latest_version = latest.get("version_number", "—") if latest else "—"
        latest_url = (
            f"https://modrinth.com/mod/{slug}/version/{latest['id']}"
            if latest and latest.get("id")
            else f"https://modrinth.com/mod/{slug}/versions"
        )
        loaders = sorted(
            {loader for version in versions for loader in version.get("loaders", [])},
            key=str.lower,
        )
        game_versions = sorted(
            {game for version in versions for game in version.get("game_versions", [])},
            key=minecraft_key,
            reverse=True,
        )

        results.append({
            "downloads": downloads,
            "name": name,
            "row": (
                f"| [{name}]({github}) | {summary} | [{latest_version}]({latest_url}) | "
                f"{format_versions(game_versions)} | "
                f"{', '.join(LOADERS.get(loader, loader.title()) for loader in loaders) or '—'} | "
                f"[{downloads:,}]({modrinth}) |"
            ),
        })

    results.sort(key=lambda item: (-item["downloads"], item["name"].lower()))
    rows = [item["row"] for item in results]
    checked = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = "\n".join(
        [
            f"**{total:,} downloads** across {len(mods)} mods. "
            "[![Update mod stats](https://github.com/Fi3w0/fiw-mods/actions/workflows/update.yml/badge.svg)]"
            "(https://github.com/Fi3w0/fiw-mods/actions/workflows/update.yml)",
            "",
            "| Mod | Summary | Latest | Minecraft | Loaders | Downloads |",
            "| --- | --- | --- | --- | --- | ---: |",
            *rows,
            "",
            f"_Checked {checked}. Generated from [`mods.json`](mods.json) by [`scripts/update.py`](scripts/update.py)._",
        ]
    )

    text = README.read_text()
    if START not in text or END not in text:
        raise SystemExit("README markers missing")

    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    README.write_text(f"{before}{START}\n{block}\n{END}{after}")
    print(f"updated {len(mods)} mods, {total:,} downloads")


if __name__ == "__main__":
    main()

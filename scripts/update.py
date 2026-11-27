#!/usr/bin/env python3
"""Update the FIW Mods README and dashboard from Modrinth."""

import html
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODS = ROOT / "mods.json"
README = ROOT / "README.md"
HERO = ROOT / "assets" / "hero.svg"
START = "<!-- stats:start -->"
END = "<!-- stats:end -->"
USER_AGENT = "Fiw-Mods/1.0 (https://github.com/Fi3w0/Fiw-Mods)"
TOKEN = os.environ.get("MODRINTH_TOKEN")

LOADERS = {
    "fabric": "Fabric",
    "neoforge": "NeoForge",
    "forge": "Forge",
    "quilt": "Quilt",
}

COLORS = ["#3fb950", "#2f81f7", "#a371f7", "#d29922", "#f778ba", "#79c0ff", "#8b949e"]
FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def esc(value):
    return html.escape(str(value), quote=True)


def get_json(url):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def minecraft_key(version):
    return tuple(int(part) for part in re.findall(r"\d+", version))


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def relative_date(value):
    date = parse_date(value)
    if not date:
        return "—"
    days = (datetime.now(timezone.utc) - date).days
    if days <= 0:
        return "today"
    if days == 1:
        return "1d ago"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def short_name(name):
    return name[4:] if name.startswith("FIW ") else name


def mc_range(versions):
    if not versions:
        return "—"
    ordered = sorted(versions, key=minecraft_key)
    if len(ordered) == 1:
        return f"{ordered[0]} (1 version)"
    return f"{ordered[0]} to {ordered[-1]} ({len(ordered)} versions)"


def loaders_text(loaders):
    return " · ".join(LOADERS.get(loader, loader.title()) for loader in loaders) or "—"


def build_hero(results, total, loaders_union, latest_mc, version_count, checked):
    successful = [mod for mod in results if mod["downloads"] >= 0]
    by_downloads = sorted(successful, key=lambda mod: mod["downloads"], reverse=True)
    top2 = sum(mod["downloads"] for mod in by_downloads[:2])
    top2_pct = round(100 * top2 / total) if total else 0

    latest_release = max(
        (mod for mod in successful if mod["latest_date_parsed"]),
        key=lambda mod: mod["latest_date_parsed"],
        default=None,
    )
    if latest_release:
        release_name = short_name(latest_release["name"])
        release_version = latest_release["latest_version"]
        release_date = (latest_release["latest_date"] or "")[:10]
        release_sub = f"v{release_version} · {release_date}"
    else:
        release_name = "—"
        release_sub = "no release data"

    tiles = [
        ("TOTAL DOWNLOADS", f"{total:,}", f"{top2_pct}% in top 2 mods", "#3fb950"),
        ("CATALOG", f"{len(results)} mods", loaders_union, "#8b949e"),
        ("LATEST MINECRAFT", latest_mc, f"{version_count} versions covered", "#8b949e"),
        ("LATEST RELEASE", release_name, release_sub, "#8b949e"),
    ]
    tile_markup = []
    for index, (label, value, subtext, subcolor) in enumerate(tiles):
        x = 32 + index * 288
        value_size = 26 if index == 3 else 34
        tile_markup.append(
            f'<rect x="{x}" y="94" width="272" height="104" rx="10" fill="#151c27" stroke="#263040"/>'
            f'<text x="{x + 18}" y="120" fill="#8b949e" font-size="14" font-family="{MONO}" letter-spacing="0.8">{esc(label)}</text>'
            f'<text x="{x + 18}" y="160" fill="#f0f6fc" font-size="{value_size}" font-weight="700" font-family="{MONO}">{esc(value)}</text>'
            f'<text x="{x + 18}" y="184" fill="{subcolor}" font-size="15" font-family="{FONT}">{esc(subtext)}</text>'
        )

    share_mods = [mod for mod in by_downloads if mod["downloads"] > 0]
    segments = []
    legend = []
    if share_mods and total:
        widths = [round(1136 * mod["downloads"] / total) for mod in share_mods]
        widths[-1] += 1136 - sum(widths)
        x = 32
        slot = 1136 / len(share_mods)
        for index, (mod, width) in enumerate(zip(share_mods, widths)):
            color = COLORS[index % len(COLORS)]
            segments.append(f'<rect x="{x}" y="244" width="{width}" height="18" fill="{color}"/>')
            percent = round(100 * mod["downloads"] / total)
            lx = 32 + index * slot
            legend.append(
                f'<rect x="{lx:.1f}" y="276" width="8" height="8" rx="2" fill="{color}"/>'
                f'<text x="{lx + 14:.1f}" y="284" fill="#c9d1d9" font-size="15" font-family="{FONT}">'
                f'{esc(short_name(mod["name"]))} {percent}%</text>'
            )
            x += width
    else:
        segments.append('<rect x="32" y="244" width="1136" height="18" rx="5" fill="#263040"/>')

    total_text = f"{total:,}"
    aria = (
        f"FIW Mods dashboard: {total_text} downloads across {len(results)} mods, "
        f"latest Minecraft {latest_mc}, checked {checked}."
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="320" viewBox="0 0 1200 320" role="img" aria-label="{esc(aria)}">
<title>FIW Mods dashboard</title>
<desc>{esc(aria)}</desc>
<defs>
<clipPath id="card"><rect x="1" y="1" width="1198" height="318" rx="14"/></clipPath>
<clipPath id="share-bar"><rect x="32" y="244" width="1136" height="18" rx="5"/></clipPath>
<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#3fb950"/>
<stop offset="1" stop-color="#2f81f7"/>
</linearGradient>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
<path d="M 32 0 L 0 0 0 32" fill="none" stroke="#192230" stroke-width="1"/>
</pattern>
</defs>
<rect x="1" y="1" width="1198" height="318" rx="14" fill="#0f141c"/>
<g clip-path="url(#card)">
<rect x="1" y="1" width="1198" height="318" fill="url(#grid)" opacity="0.35"/>
<circle cx="1100" cy="30" r="220" fill="#3fb950" opacity="0.06"/>
<circle cx="980" cy="320" r="260" fill="#2f81f7" opacity="0.05"/>
<rect x="1" y="1" width="1198" height="3" fill="url(#accent)" opacity="0.9"/>
</g>
<rect x="1" y="1" width="1198" height="318" rx="14" fill="none" stroke="#263040" stroke-width="1.5"/>
<text x="32" y="48" fill="#f0f6fc" font-size="32" font-weight="700" font-family="{FONT}">FIW MODS</text>
<text x="212" y="48" fill="#8b949e" font-size="18" font-family="{FONT}">Mostly server-side, multi-loader. By Fi3w0.</text>
<rect x="900" y="26" width="268" height="30" rx="15" fill="#151c27" stroke="#263040"/>
<circle cx="918" cy="41" r="4.5" fill="#3fb950"/>
<text x="932" y="46" fill="#c9d1d9" font-size="14" font-family="{MONO}">SYNCED {esc(checked)}</text>
<line x1="32" y1="76" x2="1168" y2="76" stroke="#1e2736"/>
{''.join(tile_markup)}
<text x="32" y="232" fill="#8b949e" font-size="14" font-family="{MONO}" letter-spacing="0.8">DOWNLOAD SHARE BY MOD</text>
<text x="1168" y="232" text-anchor="end" fill="#6e7681" font-size="14" font-family="{MONO}">Modrinth lifetime totals</text>
<g clip-path="url(#share-bar)">
{''.join(segments)}
</g>
{''.join(legend)}
</svg>
'''


def build_card(mod):
    name = esc(mod["name"])
    summary = esc(mod["summary"])
    modrinth = f"https://modrinth.com/mod/{mod['slug']}"
    github = f"https://github.com/{mod['repo']}"
    icon = ""
    if mod.get("icon_url"):
        icon = (
            f'<a href="{esc(modrinth)}"><img src="{esc(mod["icon_url"])}" width="40" height="40" '
            f'align="left" alt="{name} icon"></a>'
        )

    downloads = f"{mod['downloads']:,}" if mod["downloads"] >= 0 else "—"
    if mod["latest_version"]:
        latest = (
            f'<a href="{esc(mod["latest_url"])}"><code>v{esc(mod["latest_version"])}</code></a>'
        )
    else:
        latest = "—"

    updated = f"Updated {relative_date(mod['latest_date'])}" if mod["latest_date"] else "No release data"
    mc = mc_range(mod["game_versions"])
    loaders = loaders_text(mod["loaders"])

    return f'''<td width="50%" valign="top">
{icon}<strong><a href="{esc(modrinth)}">{name}</a></strong><br>
<sub><a href="{esc(modrinth)}"><strong>{downloads}</strong></a> downloads · {latest}</sub>
<br><br>
{summary}<br>
<sub>{esc(updated)} · MC {esc(mc)}</sub><br>
<sub>{esc(loaders)}</sub><br>
<sub><a href="{esc(modrinth)}">Modrinth</a> · <a href="{esc(github)}">GitHub</a></sub>
</td>'''


def build_utility_card(results, total, version_count):
    return f'''<td width="50%" valign="top">
<strong>All {len(results)} projects</strong><br>
<sub>Daily snapshot from Modrinth</sub>
<br><br>
Each mod has its own GitHub repo and Modrinth page.<br>
<sub>{total:,} downloads · {version_count} Minecraft versions</sub><br>
<sub><a href="https://github.com/Fi3w0">GitHub profile</a> · <a href="https://modrinth.com/user/Fi3w0">Modrinth profile</a> · <a href="mods.json">mods.json</a> · <a href="https://github.com/Fi3w0/Fiw-Mods/actions/workflows/update.yml">Sync status</a></sub>
</td>'''


def build_cards(results, total, version_count):
    cards = [build_card(mod) for mod in results]
    if len(cards) % 2:
        cards.append(build_utility_card(results, total, version_count))

    rows = []
    for index in range(0, len(cards), 2):
        rows.append("<tr>\n" + "\n".join(cards[index:index + 2]) + "\n</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def build_matrix(results):
    lines = [
        "<details>",
        "<summary><strong>Full Minecraft version and loader matrix</strong></summary>",
        "",
        "| Mod | Latest | Released | Minecraft | Loaders | Downloads |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    for mod in results:
        name = esc(mod["name"])
        modrinth = f"https://modrinth.com/mod/{mod['slug']}"
        latest = (
            f'[v{mod["latest_version"]}]({mod["latest_url"]})'
            if mod["latest_version"]
            else "—"
        )
        released = (mod["latest_date"] or "")[:10] or "—"
        versions = ", ".join(mod["game_versions"]) or "—"
        loaders = ", ".join(LOADERS.get(loader, loader.title()) for loader in mod["loaders"]) or "—"
        downloads = f"{mod['downloads']:,}" if mod["downloads"] >= 0 else "—"
        lines.append(
            f"| [{name}]({modrinth}) | {latest} | {released} | {versions} | {loaders} | {downloads} |"
        )

    lines += ["", "</details>"]
    return "\n".join(lines)


def build_block(results, total, loaders_union, latest_mc, version_count, checked):
    alt = (
        f"FIW Mods dashboard: {total:,} downloads across {len(results)} mods, "
        f"supporting {loaders_union.replace(' / ', ', ')}; latest Minecraft {latest_mc}."
    )
    return "\n".join(
        [
            f'<p><a href="https://modrinth.com/user/Fi3w0"><img src="assets/hero.svg" alt="{esc(alt)}"></a></p>',
            "",
            "## Mods",
            "",
            f"**{total:,} downloads** · **{len(results)} mods** · {esc(loaders_union)} · latest **Minecraft {esc(latest_mc)}**",
            "",
            build_cards(results, total, version_count),
            "",
            build_matrix(results),
            "",
            f'<sub>Checked {esc(checked)} · stats from Modrinth · generated by <a href="scripts/update.py">scripts/update.py</a> from <a href="mods.json">mods.json</a>.</sub>',
        ]
    )


def main():
    mods = json.loads(MODS.read_text(encoding="utf-8"))
    results = []
    total = 0

    for mod in mods:
        name = mod["name"]
        slug = mod["slug"]
        repo = mod["repo"]
        summary = mod.get("summary", "—")
        modrinth = f"https://modrinth.com/mod/{slug}"

        try:
            project = get_json(f"https://api.modrinth.com/v2/project/{slug}")
            versions = get_json(f"https://api.modrinth.com/v2/project/{slug}/version")
        except Exception as error:
            print(f"{slug}: {error}")
            results.append({
                "name": name,
                "slug": slug,
                "repo": repo,
                "summary": summary,
                "icon_url": None,
                "downloads": -1,
                "latest_version": "",
                "latest_url": modrinth,
                "latest_date": None,
                "latest_date_parsed": None,
                "game_versions": [],
                "loaders": [],
            })
            continue

        downloads = project.get("downloads", 0)
        total += downloads
        latest = max(versions, key=lambda version: version.get("date_published", "")) if versions else None
        latest_date = latest.get("date_published") if latest else None
        latest_url = (
            f"https://modrinth.com/mod/{slug}/version/{latest['id']}"
            if latest and latest.get("id")
            else f"https://modrinth.com/mod/{slug}/versions"
        )

        results.append({
            "name": name,
            "slug": slug,
            "repo": repo,
            "summary": summary,
            "icon_url": project.get("icon_url"),
            "downloads": downloads,
            "latest_version": latest.get("version_number", "") if latest else "",
            "latest_url": latest_url,
            "latest_date": latest_date,
            "latest_date_parsed": parse_date(latest_date),
            "game_versions": sorted(
                {game for version in versions for game in version.get("game_versions", [])},
                key=minecraft_key,
                reverse=True,
            ),
            "loaders": sorted(
                {loader for version in versions for loader in version.get("loaders", [])},
                key=str.lower,
            ),
        })

    if not any(mod["downloads"] >= 0 for mod in results):
        raise SystemExit("all Modrinth requests failed")

    results.sort(key=lambda mod: (-mod["downloads"], mod["name"].lower()))
    game_versions = sorted(
        {game for mod in results for game in mod["game_versions"]},
        key=minecraft_key,
        reverse=True,
    )
    latest_mc = game_versions[0] if game_versions else "—"
    loader_names = sorted(
        {LOADERS.get(loader, loader.title()) for mod in results for loader in mod["loaders"]},
        key=str.lower,
    )
    loaders_union = " / ".join(loader_names) or "—"
    checked = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    HERO.parent.mkdir(parents=True, exist_ok=True)
    HERO.write_text(
        build_hero(results, total, loaders_union, latest_mc, len(game_versions), checked),
        encoding="utf-8",
    )

    block = build_block(results, total, loaders_union, latest_mc, len(game_versions), checked)
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit("README markers missing")

    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    README.write_text(f"{before}{START}\n{block}\n{END}{after}", encoding="utf-8")
    print(f"updated {len(results)} mods, {total:,} downloads")


if __name__ == "__main__":
    main()

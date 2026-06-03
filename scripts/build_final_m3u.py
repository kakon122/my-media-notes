#!/usr/bin/env python3
"""Build cleaned allchannelking.m3u8 from reference playlist + fixes."""
from __future__ import annotations

import re
from urllib.parse import urlparse

ROOT = "/home/kakonzone/Documents/my-media-notes"
CURRENT = f"{ROOT}/my-media-notes.m3u8"
REFERENCE = f"{ROOT}/scripts/reference_user.m3u"
TRANSCRIPT = (
    "/home/kakonzone/.cursor/projects/home-kakonzone-Documents-my-media-notes/"
    "agent-transcripts/70b70e20-9849-4a80-b3ed-0f7892411b19/"
    "70b70e20-9849-4a80-b3ed-0f7892411b19.jsonl"
)
OUTPUT = CURRENT


def ensure_reference() -> None:
    import json
    import os

    if os.path.isfile(REFERENCE):
        return
    os.makedirs(os.path.dirname(REFERENCE), exist_ok=True)
    with open(TRANSCRIPT) as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("role") != "user":
                continue
            text = obj["message"]["content"][0]["text"]
            if "#EXTM3U" not in text:
                continue
            ref = text[text.find("#EXTM3U") :]
            with open(REFERENCE, "w") as out:
                out.write(ref)
            return
    raise SystemExit(f"Reference playlist not found: {REFERENCE}")

SPORTS_KEYWORDS = re.compile(
    r"\b(sport|sports|ten\s*\d|willow|fancode|eurosport|star sports|"
    r"sony sports|t sports|ptv|bein|espn|cricket|football|arenasport)\b",
    re.I,
)

BANGLADESH_GROUPS = re.compile(
    r"bangladesh|bdix|bangla|bengali|indian bangla|in ➾ bangla",
    re.I,
)

# Path segment on 198.195.239.50:8095 -> canonical name
PATH_NAMES = {
    "tsports": ("T Sports HD", "Sports"),
    "t-sports": ("T Sports HD", "Sports"),
    "willow": ("Willow TV HD", "Sports"),
    "ptv-kutta": ("PTV Sports HD", "Sports"),
    "nagorik": ("Nagorik TV", "Bangladesh"),
    "willow": ("Willow TV HD", "Sports"),
    "news24": ("News 24 HD", "Bangladesh"),
    "btv": ("BTV HD", "Bangladesh"),
    "sonyaath": ("Sony Aath", "Bangladesh"),
    "sonytensports2": ("Sony Ten 2 HD", "Sports"),
    "sonytensports5": ("Sony Ten 5 HD", "Sports"),
    "sonytensports": ("Sony Ten 1 HD", "Sports"),
    "starsports2": ("Star Sports 2 HD", "Sports"),
    "starsportsselect1": ("Star Sports Select 1 HD", "Sports"),
    "starsportsselect2": ("Star Sports Select 2 HD", "Sports"),
    "starsports1": ("Star Sports 1 HD", "Sports"),
    "eurosport": ("Eurosport HD", "Sports"),
    "jalshamovies": ("Jalsha Movies HD", "Bangladesh"),
    "zeebanglacinema": ("Zee Bangla Cinema", "Bangladesh"),
    "colorsbanglacinema": ("Colors Bangla Cinema", "Bangladesh"),
    "sonymax": ("Sony MAX HD", "Live TV"),
    "sonytv": ("Sony TV HD", "Live TV"),
    "starplus": ("Star Plus HD", "Live TV"),
    "stargold": ("Star Gold HD", "Live TV"),
    "starmovies": ("Star Movies HD", "Live TV"),
    "zeetv": ("Zee TV HD", "Live TV"),
    "discovery": ("Discovery HD", "Live TV"),
    "nationalgeographic": ("National Geographic HD", "Live TV"),
    "cartoonnetwork": ("Cartoon Network", "Live TV"),
    "discoverykids": ("Discovery Kids", "Live TV"),
}

PLAYOUT_NAMES = {
    "209627": ("Kolkata Movies", "Live TV"),
    "209617": ("Bangla Waz", "Bangladesh"),
}

# BDIX display overrides (reference uses ALL CAPS)
BDIX_DISPLAY = {
    "T SPORTS": ("T Sports", "T Sports HD", "Sports"),
    "SONY SPORTS TEN 1 HD": ("Sony Sports Ten 1", "Sony Sports Ten 1 HD", "Sports"),
    "STAR SPORTS 1": ("Star Sports 1", "Star Sports 1 HD", "Sports"),
    "STAR SPORTS 2": ("Star Sports 2", "Star Sports 2 HD", "Sports"),
    "WILLOW TV": ("Willow TV", "Willow TV HD", "Sports"),
}

PLACEHOLDER_URL_RE = re.compile(
    r"(x\.test|your-stream|cdn\.example|\.\.\.|example\.com|placeholder)",
    re.I,
)

INVALID_NAME_RE = re.compile(
    r"^(https?://|#ext|jei jei channle|\.\.\.|like gecko|exoplayer|safari/537)",
    re.I,
)


def parse_m3u(path: str) -> list[dict]:
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [l.rstrip("\n") for l in f]
    entries: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            extinf = line
            i += 1
            url = ""
            while i < len(lines):
                nxt = lines[i].strip()
                if nxt.startswith("#EXTINF"):
                    break
                if nxt.startswith("#"):
                    i += 1
                    continue
                if nxt.startswith("http") or nxt.startswith("rtmp"):
                    url = extract_url(nxt)
                    i += 1
                    break
                i += 1
            m = re.search(r",(.+)$", extinf)
            display = m.group(1).strip() if m else ""
            tvg = re.search(r'tvg-name="([^"]*)"', extinf)
            grp = re.search(r'group-title="([^"]*)"', extinf)
            logo = re.search(r'tvg-logo="([^"]*)"', extinf)
            entries.append(
                {
                    "extinf": extinf,
                    "url": url,
                    "display": display,
                    "tvg": tvg.group(1) if tvg else "",
                    "group": grp.group(1) if grp else "",
                    "logo": logo.group(1) if logo else "",
                }
            )
        elif line.startswith("http"):
            # Unstructured URLs in reference: no reliable name; path hints used later.
            for url in split_urls_from_line(line):
                entries.append(
                    {
                        "extinf": "",
                        "url": url,
                        "display": "",
                        "tvg": "",
                        "group": "",
                        "logo": "",
                    }
                )
            i += 1
        else:
            i += 1
    return [e for e in entries if e.get("url") and is_valid_url(e["url"])]


def extract_url(line: str) -> str:
    m = re.search(r"https?://[^\s\[\]]+", line)
    return m.group(0) if m else line.split()[0]


def split_urls_from_line(line: str) -> list[str]:
    return re.findall(r"https?://[^\s\[\]]+", line) or [extract_url(line)]


def is_valid_url(url: str) -> bool:
    return bool(url) and not PLACEHOLDER_URL_RE.search(url)


def is_valid_display(name: str) -> bool:
    if not name or len(name) > 120:
        return False
    if INVALID_NAME_RE.search(name.strip()):
        return False
    if "m3u8" in name.lower() and "://" in name:
        return False
    if re.search(r"#EXTVLCOPT|ExoPlayerLib", name, re.I):
        return False
    return True


def norm_url(u: str) -> str:
    return u.strip().split("?")[0].rstrip("/").lower() if u else ""


def url_keys(u: str) -> set[str]:
    keys: set[str] = set()
    if not u:
        return keys
    keys.add(norm_url(u))
    p = urlparse(u)
    keys.add((p.netloc + p.path).lower())
    m = re.search(r"/play/([^/]+)/", p.path, re.I)
    if m:
        keys.add("play:" + m.group(1).lower())
    m = re.search(r"/live/(\d+)\.m3u8", p.path, re.I)
    if m:
        keys.add("live:" + m.group(1))
    seg = p.path.rstrip("/").split("/")[-1]
    if seg and "." in seg:
        seg = seg.rsplit(".", 1)[0]
    if seg and len(seg) > 2:
        keys.add("seg:" + seg.lower())
    return keys


def title_case_name(name: str) -> str:
    if not name:
        return name
    # Already mixed case with HD suffix — normalize spacing
    name = re.sub(r"\s+", " ", name.strip())
    if name.isupper() and len(name) > 3:
        # T SPORTS -> T Sports; STAR SPORTS 1 -> Star Sports 1
        parts = name.split()
        out = []
        for p in parts:
            if p in ("HD", "SD", "4K", "FHD", "TV"):
                out.append(p if p == "TV" else p)
            elif len(p) <= 3 and p.isalpha():
                out.append(p.upper() if p in ("TV",) else p.capitalize())
            else:
                out.append(p.capitalize())
        name = " ".join(out)
        name = re.sub(r"\bHd\b", "HD", name)
        name = re.sub(r"\bSd\b", "SD", name)
        name = re.sub(r"\b4k\b", "4K", name, flags=re.I)
    return name


def tvg_from_display(display: str) -> str:
    t = re.sub(r"\s+(HD|SD|4K|FHD)\s*$", "", display, flags=re.I).strip()
    return t or display


def infer_group(display: str, ref_group: str = "") -> str:
    """Fallback when reference has no group-title."""
    if ref_group:
        rg = ref_group.strip()
        if BANGLADESH_GROUPS.search(rg):
            return "Bangladesh"
        if re.search(r"sport", rg, re.I):
            return "Sports"
        low = rg.lower()
        if low in ("bangladesh", "sports"):
            return rg if rg in ("Sports", "Bangladesh") else rg.title()
        if low in ("live tv", "live"):
            return "Live TV"
    if SPORTS_KEYWORDS.search(display):
        return "Sports"
    if BANGLADESH_GROUPS.search(display):
        return "Bangladesh"
    return "Live TV"


def resolve_group(display: str, ref_group: str) -> str:
    """Keep rich reference categories (IN ➾ PUNJABI, BOLLYWOOD 24/7, …)."""
    if ref_group and ref_group.strip():
        return ref_group.strip()
    return infer_group(display)


def lookup_path_name(url: str) -> tuple[str, str] | None:
    m = re.search(r"playout/(\d+)/", url)
    if m and m.group(1) in PLAYOUT_NAMES:
        return PLAYOUT_NAMES[m.group(1)]
    p = urlparse(url)
    parts = [x.lower() for x in p.path.split("/") if x]
    for part in parts:
        key = re.sub(r"[^a-z0-9]", "", part)
        if key in PATH_NAMES:
            return PATH_NAMES[key]
    return None


def ref_index_keys(url: str) -> list[str]:
    """Host-specific keys only — avoids play/a01b collisions across servers."""
    if not url:
        return []
    p = urlparse(url)
    keys = [norm_url(url), (p.netloc + p.path).lower()]
    m = re.search(r"/live/(\d+)\.m3u8", p.path, re.I)
    if m and "103.159.180.34" in p.netloc:
        keys.append(f"{p.netloc}:live:{m.group(1)}")
    return keys


def build_ref_index(ref_entries: list[dict]) -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for e in ref_entries:
        if not e["url"]:
            continue
        if not e.get("extinf", "").startswith("#EXTINF"):
            continue
        if not is_valid_display(e.get("display", "")):
            continue
        for k in ref_index_keys(e["url"]):
            if k not in idx:
                idx[k] = e
    return idx


def lookup_ref(url: str, idx: dict[str, dict]) -> dict | None:
    for k in ref_index_keys(url):
        if k in idx:
            return idx[k]
    return None


def format_extinf(display: str, group: str, tvg: str = "", logo: str = "") -> str:
    display = title_case_name(display)
    tvg = tvg or tvg_from_display(display)
    group = resolve_group(display, group)
    parts = ["#EXTINF:-1"]
    if tvg:
        parts.append(f' tvg-name="{tvg}"')
    if logo:
        parts.append(f' tvg-logo="{logo}"')
    parts.append(f' group-title="{group}"')
    parts.append(f",{display}")
    return "".join(parts)


def is_junk(entry: dict) -> bool:
    url = entry.get("url", "")
    name = entry.get("display", "")
    if not is_valid_url(url):
        return True
    if name and not is_valid_display(name):
        return True
    if name in ("...", "Your-Stream-Url", "Liv"):
        return True
    if re.fullmatch(r"[AB]", name) and "x.test" in url:
        return True
    return False


def merge_entry(entry: dict, idx: dict[str, dict]) -> dict | None:
    url = entry["url"]
    if is_junk(entry):
        return None

    ref = lookup_ref(url, idx)
    path_hint = lookup_path_name(url)

    display = entry["display"]
    group = entry["group"]
    logo = entry["logo"]
    tvg = entry["tvg"]

    if path_hint:
        display, g = path_hint
        if g:
            group = g
    elif ref and ref.get("display") and is_valid_display(ref["display"]):
        display = ref["display"]
        if ref.get("group"):
            group = ref["group"]
        logo = ref.get("logo") or logo
        tvg = ref.get("tvg") or tvg

    # BDIX name normalization
    key = display.upper().strip()
    if key in BDIX_DISPLAY:
        tvg, display, group = BDIX_DISPLAY[key]

    if not display or re.fullmatch(r"[\d\s]{1,4}", display) or not is_valid_display(display):
        if path_hint:
            display = path_hint[0]
        elif ref and is_valid_display(ref.get("display", "")):
            display = ref["display"]

    if not display or not is_valid_display(display):
        if path_hint:
            display = path_hint[0]
        else:
            return None

    display = title_case_name(display)
    group = resolve_group(display, group)
    tvg = tvg or tvg_from_display(display)

    return {
        "url": url,
        "display": display,
        "group": group,
        "tvg": tvg,
        "logo": logo,
    }


def main() -> None:
    ensure_reference()
    cur = parse_m3u(CURRENT)
    ref = parse_m3u(REFERENCE)
    idx = build_ref_index(ref)

    seen_urls: set[str] = set()
    out_entries: list[dict] = []

    def add_entry(raw: dict) -> None:
        merged = merge_entry(raw, idx)
        if not merged or not is_valid_display(merged["display"]):
            return
        key = norm_url(merged["url"])
        if key in seen_urls:
            return
        seen_urls.add(key)
        out_entries.append(merged)

    # 1) Full reference playlist (~4000 channels)
    for e in ref:
        if not e.get("extinf", "").startswith("#EXTINF"):
            continue
        if not e.get("url"):
            continue
        add_entry(e)

    # 2) Extra streams only in current file (not in reference)
    for e in cur:
        if not e.get("url"):
            continue
        if norm_url(e["url"]) in seen_urls:
            continue
        add_entry(e)

    lines = ["#EXTM3U"]
    for e in out_entries:
        lines.append(format_extinf(e["display"], e["group"], e["tvg"], e["logo"]))
        lines.append(e["url"])

    text = "\n".join(lines).rstrip() + "\n"
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Wrote {len(out_entries)} channels to {OUTPUT}")
    print(f"Lines: {len(text.splitlines())}")


if __name__ == "__main__":
    main()

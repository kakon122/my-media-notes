import os
import re
import sys
import time

import requests
from appwrite.client import Client
from appwrite.id import ID
from appwrite.services.databases import Databases

APPWRITE_ENDPOINT = "https://nyc.cloud.appwrite.io/v1"
DATABASE_ID = "iptv_main"
COLLECTION_ID = "channels"
M3U_FILE = os.environ.get("M3U_FILE", "my-media-notes.m3u8")
M3U_URL = os.environ.get(
    "M3U_URL",
    "https://raw.githubusercontent.com/kakon122/my-media-notes/main/my-media-notes.m3u8",
)
IMPORT_DELAY_SEC = float(os.environ.get("IMPORT_DELAY_SEC", "0.2"))


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: missing required environment variable {name}", file=sys.stderr)
        sys.exit(1)
    return value


def load_m3u() -> str:
    if os.path.isfile(M3U_FILE):
        with open(M3U_FILE, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        print(f"Loaded playlist from {M3U_FILE} ({len(content)} bytes)")
        return content

    print(f"Local file {M3U_FILE} not found, fetching from GitHub...")
    headers = {}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"token {token}"
    response = requests.get(M3U_URL, headers=headers, timeout=60)
    response.raise_for_status()
    print(f"Fetched remote playlist ({len(response.text)} bytes)")
    return response.text


def parse_m3u(content: str) -> list[dict]:
    channels = []
    lines = content.split("\n")
    current = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            name_match = re.search(r",(.+)$", line)
            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            group_match = re.search(r'group-title="([^"]*)"', line)
            country_match = re.search(r'tvg-country="([^"]*)"', line)
            current = {
                "name": name_match.group(1).strip() if name_match else "Unknown",
                "logo_url": logo_match.group(1) if logo_match else "",
                "group_title": group_match.group(1) if group_match else "General",
                "category": group_match.group(1) if group_match else "General",
                "country": country_match.group(1) if country_match else "XX",
            }
        elif line.startswith(("http://", "https://", "rtmp://")) and current is not None:
            current["stream_url"] = line
            current["is_active"] = True
            current["quality"] = (
                "HD" if ("1080" in line or "fhd" in line.lower()) else "SD"
            )
            channels.append(current)
            current = None
    return channels


def get_docs(result):
    return getattr(result, "documents", [])


def get_id(doc):
    return getattr(doc, "id", None)


def main() -> None:
    project_id = require_env("APPWRITE_PROJECT_ID")
    api_key = require_env("APPWRITE_API_KEY")

    client = Client()
    client.set_endpoint(APPWRITE_ENDPOINT)
    client.set_project(project_id)
    client.set_key(api_key)
    databases = Databases(client)

    print("Deleting old data...")
    while True:
        result = databases.list_documents(
            database_id=DATABASE_ID, collection_id=COLLECTION_ID
        )
        docs = get_docs(result)
        if not docs:
            break
        for doc in docs:
            databases.delete_document(DATABASE_ID, COLLECTION_ID, get_id(doc))
        print(f"Deleted {len(docs)} docs...")
    print("Old data cleared!")

    channels = parse_m3u(load_m3u())
    print(f"Parsed {len(channels)} channels")
    if not channels:
        print("ERROR: no channels found in playlist", file=sys.stderr)
        sys.exit(1)

    success = 0
    failed = 0

    for i, ch in enumerate(channels):
        try:
            databases.create_document(
                database_id=DATABASE_ID,
                collection_id=COLLECTION_ID,
                document_id=ID.unique(),
                data={
                    "name": ch["name"][:255],
                    "stream_url": ch["stream_url"][:2000],
                    "category": ch["category"][:50],
                    "country": ch["country"][:10],
                    "logo_url": ch["logo_url"][:500],
                    "is_active": ch["is_active"],
                    "quality": ch["quality"][:10],
                    "group_title": ch["group_title"][:100],
                },
            )
            success += 1
            time.sleep(IMPORT_DELAY_SEC)
            if (i + 1) % 100 == 0:
                print(f"Imported {i + 1}/{len(channels)} ... ok={success} fail={failed}")
        except Exception as exc:
            failed += 1
            err = str(exc)[:120]
            print(f"Failed [{ch.get('name')}]: {err}")
            if "429" in err or "rate" in err.lower():
                print("Rate limit hit, sleeping 10s...")
                time.sleep(10)

    print(f"\nSuccess: {success}")
    print(f"Failed: {failed}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

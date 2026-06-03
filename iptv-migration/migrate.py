from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.id import ID
import requests
import re
import time

APPWRITE_ENDPOINT = "https://nyc.cloud.appwrite.io/v1"
APPWRITE_PROJECT_ID = "191876000995145"
APPWRITE_API_KEY = "standard_c994c2bc1cee7708fe5a52ec1c6b24bf7a03a2ace26c4c3171034aa7c13c31c28e48c4bc96cc00024bc46c146294ed87d275ea267a41ffa5f6ba17d2a900e5affe533515ab6072c11580bcba693dccaa49615de2e3d4d1f3ce0e547a187ee4066c2462760027c6fb7a6ffb73501d4a4e8acdb777ede588f9f465cb2cd915e216"
DATABASE_ID = "iptv_main"
COLLECTION_ID = "channels"

GITHUB_TOKEN = "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"
M3U_URL = "https://raw.githubusercontent.com/kakon122/my-media-notes/main/my-media-notes.m3u8"

client = Client()
client.set_endpoint(APPWRITE_ENDPOINT)
client.set_project(APPWRITE_PROJECT_ID)
client.set_key(APPWRITE_API_KEY)
databases = Databases(client)

print("Fetching M3U file...")
response = requests.get(M3U_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=30)
response.raise_for_status()
m3u_content = response.text
print(f"Got {len(m3u_content)} bytes")

def parse_m3u(content):
    channels = []
    lines = content.split("\n")
    current = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            name_match = re.search(r',(.+)$', line)
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
            current["quality"] = "HD" if ("1080" in line or "fhd" in line.lower()) else "SD"
            channels.append(current)
            current = None
    return channels

channels = parse_m3u(m3u_content)
print(f"Parsed {len(channels)} channels")

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
            }
        )
        success += 1
        time.sleep(0.3)
        if (i + 1) % 100 == 0:
            print(f"Imported {i+1}/{len(channels)} ... ✅{success} ❌{failed}")
    except Exception as e:
        failed += 1
        err = str(e)[:120]
        print(f"Failed [{ch.get('name')}]: {err}")
        if "429" in err or "rate" in err.lower():
            print("⏳ Rate limit, sleeping 10s...")
            time.sleep(10)

print(f"\n✅ Success: {success}")
print(f"❌ Failed: {failed}")
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.id import ID
import requests, re, time, os

APPWRITE_ENDPOINT = "https://nyc.cloud.appwrite.io/v1"
APPWRITE_PROJECT_ID = os.environ["APPWRITE_PROJECT_ID"]
APPWRITE_API_KEY = os.environ["APPWRITE_API_KEY"]
DATABASE_ID = "iptv_main"
COLLECTION_ID = "channels"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
M3U_URL = "https://raw.githubusercontent.com/kakon122/my-media-notes/main/my-media-notes.m3u8"

client = Client()
client.set_endpoint(APPWRITE_ENDPOINT)
client.set_project(APPWRITE_PROJECT_ID)
client.set_key(APPWRITE_API_KEY)
databases = Databases(client)

def extract_docs(result):
    if isinstance(result, dict):
        return result.get("documents", [])
    return getattr(result, "documents", []) or []

def extract_id(doc):
    if isinstance(doc, dict):
        return doc.get("$id") or doc.get("id")
    return getattr(doc, "id", None) or getattr(doc, "$id", None)

print("Deleting old data...")
while True:
    result = databases.list_documents(
        database_id=DATABASE_ID,
        collection_id=COLLECTION_ID,
    )
    docs = extract_docs(result)
    if not docs:
        break
    for doc in docs:
        did = extract_id(doc)
        if did:
            databases.delete_document(DATABASE_ID, COLLECTION_ID, did)
    print(f"Deleted {len(docs)} docs...")
print("Old data cleared!")

print("Fetching M3U file...")
headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
response = requests.get(M3U_URL, headers=headers, timeout=30)
response.raise_for_status()
m3u_content = response.text
print(f"Got {len(m3u_content)} bytes")

def parse_m3u(content):
    channels, current = [], None
    for line in content.split("\n"):
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
        elif line.startswith(("http://", "https://", "rtmp://")) and current:
            current["stream_url"] = line
            current["is_active"] = True
            current["quality"] = "HD" if ("1080" in line or "fhd" in line.lower()) else "SD"
            channels.append(current)
            current = None
    return channels

channels = parse_m3u(m3u_content)
print(f"Parsed {len(channels)} channels")

success = failed = 0
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
        time.sleep(0.2)
        if (i + 1) % 100 == 0:
            print(f"Imported {i+1}/{len(channels)} ... ✅{success} ❌{failed}")
    except Exception as e:
        failed += 1
        print(f"Failed [{ch.get('name')}]: {str(e)[:80]}")

print(f"\n✅ Success: {success}")
print(f"❌ Failed: {failed}")
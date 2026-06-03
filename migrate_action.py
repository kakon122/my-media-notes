import os
import requests
from appwrite.client import Client
from appwrite.services.databases import Databases

# --- Config ---
APPWRITE_ENDPOINT = "https://cloud.appwrite.io/v1"
APPWRITE_PROJECT_ID = os.environ["APPWRITE_PROJECT_ID"]
APPWRITE_API_KEY = os.environ["APPWRITE_API_KEY"]
DATABASE_ID = "YOUR_DATABASE_ID"      # <-- replace
COLLECTION_ID = "YOUR_COLLECTION_ID"  # <-- replace
M3U_URL = "https://iptv-org.github.io/iptv/index.m3u"

# --- Client ---
client = Client()
client.set_endpoint(APPWRITE_ENDPOINT).set_project(APPWRITE_PROJECT_ID).set_key(APPWRITE_API_KEY)
databases = Databases(client)

# --- Helpers to handle both dict and object responses ---
def extract_docs(result):
    if isinstance(result, dict):
        return result.get("documents", [])
    return getattr(result, "documents", [])

def extract_id(doc):
    if isinstance(doc, dict):
        return doc.get("$id") or doc.get("id")
    return getattr(doc, "$id", None) or getattr(doc, "id", None)

# --- Delete old documents ---
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
        doc_id = extract_id(doc)
        if doc_id:
            databases.delete_document(
                database_id=DATABASE_ID,
                collection_id=COLLECTION_ID,
                document_id=doc_id,
            )
    print(f"Deleted batch of {len(docs)}")

# --- Fetch M3U ---
print("Fetching M3U...")
r = requests.get(M3U_URL, timeout=60)
r.raise_for_status()
lines = r.text.splitlines()

# --- Parse + Import ---
print("Importing new data...")
count = 0
i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith("#EXTINF"):
        name = line.split(",", 1)[-1].strip() if "," in line else "Unknown"
        url = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if url and not url.startswith("#"):
            try:
                databases.create_document(
                    database_id=DATABASE_ID,
                    collection_id=COLLECTION_ID,
                    document_id="unique()",
                    data={"name": name[:255], "url": url[:2000]},
                )
                count += 1
            except Exception as e:
                print(f"Skip: {name[:40]} — {e}")
        i += 2
    else:
        i += 1

print(f"Done. Imported {count} channels.")
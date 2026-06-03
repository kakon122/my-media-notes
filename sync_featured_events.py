#!/usr/bin/env python3
"""Upload featured_live_events.json to Appwrite (single config document)."""
from __future__ import annotations

import appwrite_env  # noqa: F401 — loads .env when present

import json
import os
import sys
from datetime import datetime, timezone

from appwrite.client import Client
from appwrite.exception import AppwriteException
from appwrite.services.databases import Databases

APPWRITE_ENDPOINT = os.environ.get("APPWRITE_ENDPOINT", "https://nyc.cloud.appwrite.io/v1")
DATABASE_ID = os.environ.get("APPWRITE_DATABASE_ID", "iptv_main")
COLLECTION_ID = os.environ.get("APPWRITE_CONFIG_COLLECTION_ID", "app_config")
DOCUMENT_ID = os.environ.get("APPWRITE_FEATURED_EVENTS_DOC_ID", "featured_live_events")
JSON_FILE = os.environ.get("FEATURED_EVENTS_FILE", "featured_live_events.json")


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: missing required environment variable {name}", file=sys.stderr)
        sys.exit(1)
    return value


def load_json_file(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def main() -> None:
    project_id = require_env("APPWRITE_PROJECT_ID")
    api_key = require_env("APPWRITE_API_KEY")

    if not os.path.isfile(JSON_FILE):
        print(f"ERROR: file not found: {JSON_FILE}", file=sys.stderr)
        sys.exit(1)

    payload = load_json_file(JSON_FILE)
    json_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    now = datetime.now(timezone.utc).isoformat()

    client = Client()
    client.set_endpoint(APPWRITE_ENDPOINT)
    client.set_project(project_id)
    client.set_key(api_key)
    databases = Databases(client)

    data = {
        "key": "featured_live_events",
        "json_payload": json_text,
        "updated_at": now,
    }

    try:
        databases.update_document(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ID,
            document_id=DOCUMENT_ID,
            data=data,
        )
        print(f"Updated document {DOCUMENT_ID} in {DATABASE_ID}/{COLLECTION_ID}")
    except AppwriteException as exc:
        if exc.code != 404:
            raise
        databases.create_document(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ID,
            document_id=DOCUMENT_ID,
            data=data,
        )
        print(f"Created document {DOCUMENT_ID} in {DATABASE_ID}/{COLLECTION_ID}")

    print(f"Synced {JSON_FILE} ({len(json_text)} bytes) at {now}")


if __name__ == "__main__":
    main()

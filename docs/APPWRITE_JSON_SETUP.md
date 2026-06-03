# Appwrite-এ JSON রাখা (featured live events)

GitHub private করলেও app আপডেট পাবে — JSON Appwrite থেকে পড়বে।

## ১) Appwrite Console সেটআপ

1. https://cloud.appwrite.io → আপনার project
2. **Databases** → `iptv_main` (আগে থেকে আছে)
3. **Create collection** → ID: `app_config`, Name: `App Config`
4. **Attributes** যোগ করুন:

| Key | Type | Size | Required |
|-----|------|------|----------|
| `key` | String | 64 | Yes |
| `json_payload` | String | 100000 | Yes |
| `updated_at` | String | 64 | No |

5. **Indexes** (optional): `key` unique

6. **Settings → Permissions** (collection):
   - Role **Any** → **Read** ✅ (app বিনা secret-এ পড়তে পারবে)
   - **Create/Update/Delete** শুধু API key / server (workflow) — Any-তে দেবেন না

7. GitHub repo → **Settings → Secrets → Actions** (আগে থাকলে ঠিক আছে):
   - `APPWRITE_PROJECT_ID`
   - `APPWRITE_API_KEY` (scopes: `databases.write` + `collections.read`)

## ২) GitHub থেকে sync

`featured_live_events.json` বদলে push করলে workflow JSON-ও Appwrite-এ আপলোড করবে।

লোকাল টেস্ট:

```bash
cd /home/kakonzone/Documents/my-media-notes
export APPWRITE_PROJECT_ID="your_project_id"
export APPWRITE_API_KEY="your_api_key"
python3 sync_featured_events.py
```

## ৩) Lumio app (Flutter) — কোথা থেকে পড়বে

GitHub raw URL সরিয়ে Appwrite document পড়ুন।

**REST URL (সরল):**

```
GET https://nyc.cloud.appwrite.io/v1/databases/iptv_main/collections/app_config/documents/featured_live_events
Header: X-Appwrite-Project: <APPWRITE_PROJECT_ID>
```

Response-এর `json_payload` ফিল্ড string — `jsonDecode()` করুন।

**উদাহরণ (Dart):**

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

const _endpoint = 'https://nyc.cloud.appwrite.io/v1';
const _projectId = String.fromEnvironment('APPWRITE_PROJECT_ID');
const _databaseId = 'iptv_main';
const _collectionId = 'app_config';
const _documentId = 'featured_live_events';

Future<Map<String, dynamic>> fetchFeaturedLiveEvents() async {
  final uri = Uri.parse(
    '$_endpoint/databases/$_databaseId/collections/$_collectionId/documents/$_documentId',
  );
  final res = await http.get(uri, headers: {
    'X-Appwrite-Project': _projectId,
  });
  if (res.statusCode != 200) {
    throw Exception('Appwrite config failed: ${res.statusCode}');
  }
  final doc = jsonDecode(res.body) as Map<String, dynamic>;
  final raw = doc['json_payload'] as String;
  return jsonDecode(raw) as Map<String, dynamic>;
}
```

পুরনো GitHub URL (যেমন `raw.githubusercontent.com/.../featured_live_events.json`) কোডে খুঁজে মুছে উপরের function ব্যবহার করুন।

## ৪) দৈনন্দিন কাজ

```bash
# JSON এডিট
nano featured_live_events.json

git add featured_live_events.json
git commit -m "update featured live events"
git push origin main
```

অথবা Actions → **Update IPTV Channels** → **Run workflow**

## ৫) চেকলিস্ট

- [ ] Collection `app_config` তৈরি
- [ ] Any → Read permission
- [ ] Workflow সবুজ ✅
- [ ] Appwrite-এ document `featured_live_events` দেখা যায়
- [ ] App-এ GitHub JSON URL নেই

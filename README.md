# allchannelking.m3u8 (`my-media-notes.m3u8`)

IPTV playlist for Lumio / GitHub Pages. Channel names use:

```m3u
#EXTINF:-1 tvg-name="T Sports" group-title="Sports",T Sports HD
https://stream-url/playlist.m3u8
```

Rebuild after edits:

```bash
python3 scripts/build_final_m3u.py
```

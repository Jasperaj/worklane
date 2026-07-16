#!/usr/bin/env python3
"""
Fetch a Pexels image for a blog post.

Usage:
  python _fetch_image.py "<search query>" <slug>

Downloads a landscape image to ../uploads/blog/<slug>.jpg
and prints a JSON blob with:  { path, photographer, photographer_url, source_url, alt }
"""
import json
import os
import sys
import urllib.parse
import urllib.request

PEXELS_KEY = os.environ.get("PEXELS_API_KEY")
PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "blog")

def pexels(query):
    if not PEXELS_KEY:
        return None
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode({
        "query": query, "per_page": 5, "orientation": "landscape", "size": "large"
    })
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_KEY})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except Exception as e:
        print(f"pexels error: {e}", file=sys.stderr)
        return None
    if not data.get("photos"):
        return None
    p = data["photos"][0]
    return {
        "download": p["src"]["large2x"],
        "photographer": p["photographer"],
        "photographer_url": p["photographer_url"],
        "source_url": p["url"],
        "alt": p.get("alt") or query,
        "provider": "Pexels",
    }

def pixabay(query):
    if not PIXABAY_KEY:
        return None
    url = "https://pixabay.com/api/?" + urllib.parse.urlencode({
        "key": PIXABAY_KEY, "q": query, "image_type": "photo",
        "orientation": "horizontal", "per_page": 5, "safesearch": "true"
    })
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.load(r)
    except Exception as e:
        print(f"pixabay error: {e}", file=sys.stderr)
        return None
    if not data.get("hits"):
        return None
    h = data["hits"][0]
    return {
        "download": h["largeImageURL"],
        "photographer": h["user"],
        "photographer_url": f"https://pixabay.com/users/{h['user']}-{h['user_id']}/",
        "source_url": h["pageURL"],
        "alt": h.get("tags") or query,
        "provider": "Pixabay",
    }

def main():
    if len(sys.argv) < 3:
        print("usage: _fetch_image.py '<query>' <slug>", file=sys.stderr)
        sys.exit(2)
    query, slug = sys.argv[1], sys.argv[2]
    os.makedirs(OUT_DIR, exist_ok=True)
    meta = pexels(query) or pixabay(query)
    if not meta:
        print(json.dumps({"error": "no image found"}))
        sys.exit(1)
    out_path = os.path.join(OUT_DIR, f"{slug}.jpg")
    req = urllib.request.Request(meta["download"], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(out_path, "wb") as f:
        f.write(r.read())
    meta["path"] = f"../../uploads/blog/{slug}.jpg"
    del meta["download"]
    print(json.dumps(meta))

if __name__ == "__main__":
    main()

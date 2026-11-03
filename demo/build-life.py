#!/usr/bin/env python3
"""Seed a life file from the photo archive on alstonwang.com.

Reads photos.json (the photography page's index) and emits the parts of a life
record that can be derived mechanically: dated photographs, and chapters formed
from clusters of them.

It deliberately does NOT write any `why` strings. Reasoning is derived at
runtime by the model (docs/TRADEOFFS.md T-13, T-16); authoring it here would be
putting words in the system's mouth.

Everything a person has to supply themselves — letters, traditions, what they
actually said — stays in the hand-written section of the output file and is
merged over whatever this produces.

    ./demo/build-life.py photos.json demo/alston.json [scaffold.json]
"""
import json
import sys
import urllib.parse
from collections import defaultdict

# Absolute, so the record renders the same whether it is served from the site,
# from a local dev server, or from someone else's machine.
IMG_BASE = "https://alstonwang.com/images/"

# Caption prefixes that belong to one trip, and the chapter they form.
# Everything not claimed here stays a standalone dated photograph.
# Caption → real-world place. Chapter maps are built from this, so adding a
# coordinate here is all it takes for a trip to appear on the life map.
PLACES = {
    "Santa Cruz, Guatemala": (14.7333, -91.2000),
    "San Pedro, Guatemala": (14.6919, -91.2722),
    "Volcan de Fuego, Guatemala": (14.4747, -90.8806),
    "Acatenango, Guatemala": (14.5008, -90.8761),
    "Antigua, Guatemala": (14.5586, -90.7295),
    "Pistol River": (42.2787, -124.3976),
    "Secret Beach": (42.1830, -124.3730),
    "Samuel H. Boardman": (42.1500, -124.3500),
    "Samuel H. Boardman Scenic": (42.1500, -124.3500),
    "Devil's Punchbowl": (44.7457, -124.0618),
    "Thor's Well, Oregon Coast": (44.2780, -124.1130),
    "Shingle Mills, Oregon Coast": (42.2000, -124.3500),
    "Cannon Beach": (45.8918, -123.9615),
    "Crater Lake": (42.9446, -122.1090),
    "Glacier National Park": (48.7596, -113.7870),
    "Grinnell Glacier, Glacier": (48.7563, -113.7236),
    "Japan": (35.6762, 139.6503),
    "Taipei": (25.0330, 121.5654),
    "Costa Rica": (9.7489, -83.7534),
    "Arenal Volcano, Costa Rica": (10.4630, -84.7033),
    "La Fortuna, Costa Rica": (10.4678, -84.6427),
    "La Paz Waterfall, Costa Rica": (10.2167, -84.1667),
}

CHAPTERS = [
    ("guatemala", "Guatemala", 2025,
     ["Santa Cruz, Guatemala", "San Pedro, Guatemala", "Volcan de Fuego, Guatemala",
      "Acatenango, Guatemala", "Antigua, Guatemala"]),
    ("oregon-coast", "The Oregon Coast", 2026,
     ["Pistol River", "Secret Beach", "Samuel H. Boardman", "Samuel H. Boardman Scenic",
      "Devil's Punchbowl", "Thor's Well, Oregon Coast", "Shingle Mills, Oregon Coast",
      "Cannon Beach", "Crater Lake", "Moonlight"]),
    ("glacier", "Glacier National Park", 2024,
     ["Glacier National Park", "Grinnell Glacier, Glacier"]),
    ("asia", "Japan and Taiwan", 2025,
     ["Japan", "Taipei"]),
    ("costa-rica", "Costa Rica", 2025,
     ["Costa Rica", "Arenal Volcano, Costa Rica", "La Fortuna, Costa Rica",
      "La Paz Waterfall, Costa Rica"]),
]


def youtube_id(url):
    if "youtu.be/" in url:
        return url.rsplit("/", 1)[-1].split("?")[0]
    q = urllib.parse.urlparse(url).query
    return urllib.parse.parse_qs(q).get("v", [""])[0]


def media_for(item):
    """A still becomes a src; a drone video becomes a poster plus a link out."""
    if item.get("type") == "video" and item.get("url"):
        vid = youtube_id(item["url"])
        return {"video": item["url"],
                "src": "https://img.youtube.com/vi/%s/hqdefault.jpg" % vid}
    section = item.get("section") or "camera"
    return {"src": IMG_BASE + section + "/" + urllib.parse.quote(item["file"])}


def main():
    src_path, out_path = sys.argv[1], sys.argv[2]
    photos = json.load(open(src_path))

    claimed = {cap for _, _, _, caps in CHAPTERS for cap in caps}
    by_caption = defaultdict(list)
    for p in photos:
        by_caption[p.get("caption") or ""].append(p)

    chapters = []
    for cid, title, year, caps in CHAPTERS:
        shots = [p for cap in caps for p in by_caption.get(cap, [])]
        shots = [p for p in shots if p.get("date")]
        # Videos last — they read as a coda rather than an opening frame.
        shots.sort(key=lambda p: (p.get("type") == "video", p["date"]))
        if not shots:
            continue
        chapters.append({
            "id": cid,
            "year": year,
            "title": title,
            "eyebrow": "Chapter · %s" % year,
            "narrative": "",          # written by curation, not here
            "curationWhy": "",        # derived, not authored
            "candidates": len(shots),
            "locations": [
                {"name": cap, "lat": PLACES[cap][0], "lng": PLACES[cap][1]}
                for cap in caps if cap in PLACES
            ],
            "slides": [
                dict(media_for(p), caption=p.get("caption", ""), why="")
                for p in shots
            ],
        })

    # Dated photographs that aren't part of a chapter become timeline moments.
    loose = []
    for p in photos:
        cap = p.get("caption") or ""
        if cap in claimed or not p.get("date"):
            continue
        loose.append(p)
    loose.sort(key=lambda p: p["date"])

    seen = set()
    events = []
    for p in loose:
        cap = p.get("caption") or ""
        if cap in seen:
            continue
        seen.add(cap)
        events.append(dict({
            "year": int(p["date"][:4]),
            "kind": "video" if p.get("type") == "video" else "photo",
            "title": cap,
            "detail": "",
        }, **media_for(p)))
    for cid, _, year, _ in CHAPTERS:
        if any(c["id"] == cid for c in chapters):
            events.append({"year": year, "kind": "chapter", "ref": cid})

    out = {
        "_generated": "demo/build-life.py — chapters and photo moments from photos.json",
        "chapters": chapters,
        "events": events,
    }

    # Merge the hand-written half over the generated one. The scaffold owns the
    # person, achievements, letters and quotes; this script owns anything that
    # can be read out of the photo archive.
    if len(sys.argv) > 3:
        scaffold = json.load(open(sys.argv[3]))
        events = events + scaffold.pop("scaffoldEvents", [])
        scaffold.pop("chapters", None)
        # Learnings are keyed by id so they survive regeneration — the photos
        # can change without losing what the experience taught.
        learnings = scaffold.pop("learnings", {})
        out.update(scaffold)
        for ch in out["chapters"]:
            if learnings.get(ch["id"], {}).get("text"):
                ch["learning"] = learnings[ch["id"]]
        for a in out.get("achievements", []):
            if learnings.get(a["id"], {}).get("text"):
                a["learning"] = learnings[a["id"]]
        out["events"] = events

    out["events"] = sorted(out["events"], key=lambda e: e["year"])
    json.dump(out, open(out_path, "w"), indent=2, ensure_ascii=False)
    print("%s: %d chapters, %d photo moments" % (out_path, len(chapters), len(events)))


if __name__ == "__main__":
    main()

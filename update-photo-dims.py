#!/usr/bin/env python3
"""Populate image dimensions (w/h) in photos.json for the photography gallery.

photography.html uses these stored dimensions to lay out photos WITHOUT
downloading every full-resolution image first (which is what made the page
slow). Run this whenever you add new photos:

    python3 update-photo-dims.py        # fill in dimensions for new photos only
    python3 update-photo-dims.py --all  # recompute dimensions for every photo

Dimensions are the photo's *displayed* size — EXIF rotation is respected, so a
phone photo shot in portrait is stored as portrait (matching what the browser
shows). Uses Pillow if available, otherwise falls back to macOS `sips` (which
reads RAW pixels and does NOT account for rotation — install Pillow for
correct results: `pip install Pillow`). Your image files are never modified.
After running, commit the updated photos.json and push.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PHOTOS_JSON = os.path.join(ROOT, 'photos.json')
EXIF_ORIENTATION_TAG = 274  # 0x0112; values 5-8 mean the image is rotated 90/270
refresh_all = '--all' in sys.argv

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


def dims_pil(path):
    im = Image.open(path)
    w, h = im.size
    orient = None
    try:
        orient = (im._getexif() or {}).get(EXIF_ORIENTATION_TAG)
    except Exception:
        pass
    return (h, w) if orient in (5, 6, 7, 8) else (w, h)  # swap if rotated


def dims_sips(path):
    out = subprocess.check_output(
        ['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', path],
        universal_newlines=True, stderr=subprocess.DEVNULL)
    w = h = None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith('pixelWidth:'):
            w = int(s.split(':')[1])
        elif s.startswith('pixelHeight:'):
            h = int(s.split(':')[1])
    return w, h


def main():
    if not HAVE_PIL:
        print("WARNING: Pillow not found — using sips, which ignores EXIF "
              "rotation. Rotated photos may be misclassified. `pip install Pillow`.")
    photos = json.load(open(PHOTOS_JSON))
    updated = skipped = problems = 0

    for p in photos:
        if p.get('type') == 'video':
            continue
        if not refresh_all and p.get('w') and p.get('h'):
            skipped += 1
            continue
        path = os.path.join(ROOT, 'images', p.get('section', ''), p.get('file', ''))
        if not os.path.isfile(path):
            print('MISSING FILE:', path)
            problems += 1
            continue
        try:
            w, h = dims_pil(path) if HAVE_PIL else dims_sips(path)
            if w and h:
                p['w'], p['h'] = w, h
                updated += 1
            else:
                print('NO DIMENSIONS:', path)
                problems += 1
        except Exception as e:
            print('ERROR:', path, e)
            problems += 1

    json.dump(photos, open(PHOTOS_JSON, 'w'), indent=2, ensure_ascii=False)
    print(f"updated: {updated}, already had dimensions: {skipped}, "
          f"missing/errors: {problems}, total: {len(photos)}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Populate image dimensions (w/h) in photos.json for the photography gallery.

photography.html uses these stored dimensions to lay out photos WITHOUT
downloading every full-resolution image first (which is what made the page
slow). Run this whenever you add new photos:

    python3 update-photo-dims.py        # fill in dimensions for new photos only
    python3 update-photo-dims.py --all  # recompute dimensions for every photo

Dimensions are read with macOS `sips` (read-only — your image files are never
modified). After running, commit the updated photos.json and push.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PHOTOS_JSON = os.path.join(ROOT, 'photos.json')
refresh_all = '--all' in sys.argv


def read_dims(path):
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
            w, h = read_dims(path)
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

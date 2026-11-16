"""Step 1: collect the photos into a working folder.

Two sources:
  --folder PATH    any folder on the computer: photos copied from an iPhone or Android over a cable, an iCloud Photos
                   folder on Windows, a backup drive. Also Google Takeout zip files, as downloaded, without unzipping:
                   point at the folder they sit in (or at a single zip file), and the script extracts only the photos.
  --mac-photos     the Mac Photos library (an iPhone with iCloud photos). Requires: pip install osxphotos

For each photo only two small copies are saved (384px for classification, 160px for the studio). The original is not moved or changed.

  python scripts/gather.py --folder ~/Pictures/phone --n 1000 --out ~/.gallery-sorter/runs/run1
  python scripts/gather.py --mac-photos --n 1000 --out ~/.gallery-sorter/runs/run1
"""
import argparse
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

import common  # noqa: F401  (safe output encoding on Windows)

register_heif_opener()
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
# iOS names a screenshot "Screenshot" in English. The escaped form is the same filename on a Hebrew-language phone.
SHOT_RE = re.compile(r"screenshot|screen shot|scr_|screenshot_|\u05e6\u05d9\u05dc\u05d5\u05dd \u05de\u05e1\u05da", re.I)


def exif_info(im):
    """Capture date and GPS from EXIF, when present."""
    date = lat = lon = None
    camera = False
    try:
        ex = im.getexif()
        camera = bool(ex.get(271) or ex.get(272))  # camera make/model: separates a real photo from a screenshot
        sub = ex.get_ifd(0x8769)
        raw = sub.get(36867) or sub.get(36868) or ex.get(306)
        if raw:
            date = datetime.strptime(str(raw)[:19], "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
        gps = ex.get_ifd(0x8825)
        if gps and 2 in gps and 4 in gps:
            def deg(v):
                d, m, s = [float(x) for x in v]
                return d + m / 60 + s / 3600
            lat, lon = deg(gps[2]), deg(gps[4])
            if gps.get(1) == "S":
                lat = -lat
            if gps.get(3) == "W":
                lon = -lon
            if abs(lat) < 1e-6 and abs(lon) < 1e-6:
                lat = lon = None
    except Exception:
        pass
    return date, lat, lon, camera


_JSON_INDEX = {}


def _jsons_in(d):
    if d not in _JSON_INDEX:
        _JSON_INDEX[d] = [f for f in os.listdir(d) if f.lower().endswith(".json")]
    return _JSON_INDEX[d]


def sidecar_for(path):
    """Google Takeout places a json file with the date and location next to each photo. The name changes between
    versions, and is truncated at 51 characters:
    IMG_1.jpg.json, IMG_1.jpg.supplemental-metadata.json, IMG_1.jpg.supplemental-me.json,
    and for duplicates: IMG_1(1).jpg <- IMG_1.jpg(1).json or IMG_1.jpg.supplemental-metadata(1).json."""
    name, d = path.name, str(path.parent)
    files = _jsons_in(d)
    m = re.match(r"^(.*)\((\d+)\)(\.[^.]+)$", name)
    if m:
        base, n = m.group(1) + m.group(3), m.group(2)
        for f in (f"{base}({n}).json", f"{base}.supplemental-metadata({n}).json"):
            if f in files:
                return path.with_name(f)
    full = name + ".supplemental-metadata"
    best = None
    for f in files:
        stem = f[:-5]
        if stem == name or (full.startswith(stem) and len(stem) >= min(len(name), 40)):
            if best is None or len(f) > len(best):
                best = f
    if best:
        return path.with_name(best)
    alt = path.with_suffix(".json")
    return alt if alt.name in files else None


def takeout_sidecar(path):
    cand = sidecar_for(path)
    if cand:
        try:
            j = json.loads(cand.read_text(encoding="utf-8"))
            ts = int(j.get("photoTakenTime", {}).get("timestamp", 0))
            geo = j.get("geoData") or {}
            lat, lon = geo.get("latitude"), geo.get("longitude")
            if not lat and not lon:
                lat = lon = None
            return (datetime.fromtimestamp(ts, timezone.utc) if ts else None), lat, lon
        except Exception:
            pass
    return None, None, None


def unzip_takeout(zips, dest):
    """Extract only photos and json files from each zip (not videos), into the run folder. A second run does not extract again."""
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for info in zf.infolist():
                ext = Path(info.filename).suffix.lower()
                if info.is_dir() or (ext not in IMAGE_EXT and ext != ".json"):
                    continue
                target = dest / z.stem / info.filename
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, open(target, "wb") as out:
                        out.write(src.read())
                    try:  # file date from the zip, as a fallback when the photo has no json
                        ts = datetime(*info.date_time).timestamp()
                        os.utime(target, (ts, ts))
                    except (ValueError, OSError):
                        pass
                n += ext in IMAGE_EXT
        print(f"unzipped {z.name}", flush=True)
    print(f"{n} images from {len(zips)} zip file(s)", flush=True)
    return dest


def scan(root, skip):
    return [p for p in root.rglob("*")
            if p.suffix.lower() in IMAGE_EXT and p.is_file()
            and not any(part.startswith(".") for part in p.relative_to(root).parts)
            and not any(s == q for s in skip for q in p.resolve().parents)]


def from_folder(root, n, skip, out):
    root = Path(root).expanduser().resolve()
    if not root.exists():
        sys.exit(f"Not found: {root}")
    skip = [Path(s).expanduser().resolve() for s in skip]
    zips = [root] if root.suffix.lower() == ".zip" else (sorted(root.glob("*.zip")) if root.is_dir() else [])
    files = scan(root, skip) if root.is_dir() else []
    if zips:
        files += scan(unzip_takeout(zips, out / "unzipped"), [])
    print(f"found {len(files)} images in {root}", flush=True)
    if not files:
        sys.exit("No photos found. Check that the folder is correct (and that the zip files finished downloading).")
    items = []
    for p in files:
        try:
            im = Image.open(p)
            date, lat, lon, camera = exif_info(im)
            tdate, tlat, tlon = takeout_sidecar(p)
            date = date or tdate or datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
            if lat is None and tlat is not None:
                lat, lon = tlat, tlon
            shot = bool(SHOT_RE.search(p.name)) or (p.suffix.lower() == ".png" and not camera)
            items.append({"src": str(p), "date": date, "lat": lat, "lon": lon, "screenshot": shot,
                          "bytes": p.stat().st_size, "filename": p.name})
        except Exception as e:
            print("skip", p.name, e)
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:n]


def from_mac_photos(n, library):
    try:
        import osxphotos
    except ImportError:
        sys.exit("osxphotos is missing. Install it with: pip install osxphotos")
    lib = Path(library or "~/Pictures/Photos Library.photoslibrary").expanduser()
    # An explicit database path: without it, osxphotos tries to read a protected Photos preference and stalls on permissions
    db = osxphotos.PhotosDB(dbfile=str(lib / "database" / "Photos.sqlite"))
    photos = [p for p in db.photos(images=True, movies=False) if p.date and not p.hidden]
    photos.sort(key=lambda p: p.date, reverse=True)
    items, cloud_only = [], 0
    for p in photos:
        if len(items) >= n * 1.1:
            break
        cands = [d for d in (p.path_derivatives or []) if d and os.path.exists(d)]
        src = max(cands, key=os.path.getsize) if cands else (p.path if p.path and os.path.exists(p.path) else None)
        if not src:
            cloud_only += 1  # the photo lives only in iCloud and has no preview on this Mac
            continue
        lat, lon = p.location if p.location else (None, None)
        items.append({"src": src, "date": p.date.astimezone(timezone.utc), "lat": lat, "lon": lon,
                      "screenshot": bool(p.screenshot), "bytes": p.original_filesize,
                      "filename": p.original_filename, "uuid": p.uuid})
    print(f"Photos library: {len(photos)} photos, using the newest {min(n, len(items))}"
          + (f" ({cloud_only} skipped: only in iCloud, no copy on this Mac)" if cloud_only else ""), flush=True)
    return items[:n]


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--folder")
    g.add_argument("--mac-photos", action="store_true")
    ap.add_argument("--library", help="path to a different Photos library on the Mac")
    ap.add_argument("--n", type=int, default=1000, help="how many photos (newest first)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out).expanduser()
    (out / "cls").mkdir(parents=True, exist_ok=True)
    (out / "thumbs").mkdir(parents=True, exist_ok=True)

    items = from_mac_photos(args.n, args.library) if args.mac_photos else from_folder(args.folder, args.n, [out], out)
    meta = []
    for it in items:
        try:
            im = ImageOps.exif_transpose(Image.open(it["src"])).convert("RGB")
        except Exception as e:
            print("skip", it["filename"], e)
            continue
        i = len(meta)
        c = im.copy(); c.thumbnail((384, 384)); c.save(out / "cls" / f"{i:05d}.jpg", quality=82)
        ImageOps.fit(im, (160, 160)).save(out / "thumbs" / f"{i:05d}.jpg", quality=80)
        meta.append({**it, "i": i, "date": it["date"].isoformat(), "w": im.width, "h": im.height})
        if i % 100 == 0:
            print(i, it["date"].date(), flush=True)
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"done: {len(meta)} images -> {out}")


if __name__ == "__main__":
    main()

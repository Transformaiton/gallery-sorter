"""Step 4: sort the photos into folders. Copy only: the originals are not moved, changed, or deleted.

  python scripts/organize.py --run RUN                       # a plan: how many land in each folder, nothing is touched
  python scripts/organize.py --run RUN --dest "~/Pictures/Gallery Sorter" --apply

The result:
  <dest>/Trips/...  <dest>/Family/...  <dest>/Receipts and documents/...
  <dest>/Review before deleting/Duplicates/...   <dest>/Review before deleting/Blurry/...
Deleting, if you choose to, is done by hand on the phone or in the gallery, after you look through the review folder.
"""
import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from common import REVIEW_FOLDER, album_name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--dest", default=str(Path.home() / "Pictures" / "Gallery Sorter"))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    run, dest = Path(args.run).expanduser(), Path(args.dest).expanduser()
    meta = json.loads((run / "sorted.json").read_text(encoding="utf-8"))

    def folder(m):
        if m["album"] in ("dupes", "blurry"):
            return Path(REVIEW_FOLDER) / album_name(m["album"])
        return Path(album_name(m["album"]))

    plan = Counter(str(folder(m)) for m in meta)
    print(f"{'Will place' if not args.apply else 'Copying'} {len(meta)} photos into {dest}:")
    for k, v in sorted(plan.items(), key=lambda kv: (kv[0].startswith(REVIEW_FOLDER), -kv[1])):
        print(f"  {v:6d}  {k}")
    if not args.apply:
        print("\nThis is a plan only. To copy the files, run the same command with --apply")
        return

    copied = 0
    for m in meta:
        src = Path(m["src"])
        if not src.exists():
            print("missing", src)
            continue
        d = dest / folder(m)
        d.mkdir(parents=True, exist_ok=True)
        target = d / (m.get("filename") or src.name)
        k = 1
        while target.exists():  # identical names from different folders: add a number, do not overwrite
            target = d / f"{Path(m.get('filename') or src.name).stem} ({k}){src.suffix}"
            k += 1
        shutil.copy2(src, target)
        copied += 1
        if copied % 200 == 0:
            print(f"  {copied}/{len(meta)}", flush=True)
    (run / "organized.json").write_text(json.dumps({"dest": str(dest), "copied": copied}, ensure_ascii=False))
    print(f"\nCopied {copied} photos to {dest}. The originals were not touched.")


if __name__ == "__main__":
    main()

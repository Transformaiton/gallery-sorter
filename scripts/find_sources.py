"""Step 0: where are the photos? Scan the usual places and suggest a source, so the user does not have to search.

  python scripts/find_sources.py

Finds: the Mac Photos library (an iPhone with iCloud), the iCloud Photos folder on Windows, Google Takeout
zip files in Downloads, and DCIM folders on a connected phone or memory card. Prints the matching command for each source.
"""
import os
import platform
import string
from pathlib import Path

import common  # noqa: F401  (safe output encoding on Windows)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
H = Path.home()


def count_images(d, cap=20000):
    n = 0
    for _, _, files in os.walk(d):
        n += sum(1 for f in files if Path(f).suffix.lower() in IMAGE_EXT)
        if n >= cap:
            return f"{cap:,}+"
    return f"{n:,}"


def main():
    found = []
    lib = H / "Pictures" / "Photos Library.photoslibrary"
    if platform.system() == "Darwin" and lib.exists():
        found.append(("Mac Photos library (iPhone photos in iCloud)", "--mac-photos", "requires: pip install osxphotos"))
    for d in (H / "Pictures" / "iCloud Photos" / "Photos", H / "Pictures" / "iCloud Photos",
              H / "iCloudPhotos", H / "Pictures" / "iCloudPhotos"):
        if d.is_dir():
            found.append((f"iCloud Photos folder ({count_images(d)} photos)", f'--folder "{d}"', ""))
            break
    for d in (H / "Downloads", H / "Desktop"):
        zips = sorted(d.glob("takeout-*.zip")) if d.is_dir() else []
        if zips:
            size = sum(z.stat().st_size for z in zips)
            human = f"{size / 1e9:.1f}GB" if size >= 1e9 else f"{size / 1e6:.0f}MB"
            found.append((f"Google Takeout: {len(zips)} zip files in {d.name} ({human})", f'--folder "{d}"',
                          f"Do not unzip them. Leave about {human} free, because the tool extracts only the photos"))
        for t in (d / "Takeout",) if d.is_dir() else ():
            if t.is_dir():
                found.append((f"Extracted Takeout folder ({count_images(t)} photos)", f'--folder "{t}"', ""))
    roots = [Path("/Volumes")] if platform.system() == "Darwin" else [Path(f"{c}:/") for c in string.ascii_uppercase if Path(f"{c}:/").exists()]
    for r in roots:
        try:
            vols = [r] if platform.system() != "Darwin" else [v for v in r.iterdir() if v.is_dir()]
        except OSError:
            continue
        for v in vols:
            dcim = v / "DCIM"
            if dcim.is_dir():
                found.append((f"DCIM folder on {v} ({count_images(dcim)} photos)", f'--folder "{dcim}"', ""))
    if not found:
        print("No photo source found in the usual places.")
        print("iPhone or Android over a cable: copy the photos into a folder. Google Photos: takeout.google.com. Then pass --folder <the-folder>")
        return
    print("Sources I found:")
    for k, (what, arg, note) in enumerate(found, 1):
        print(f"  {k}. {what}\n     gather.py {arg}" + (f"\n     ({note})" if note else ""))


if __name__ == "__main__":
    main()

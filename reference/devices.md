# How to get the photos onto the computer, by device

Every path ends the same way: a folder on the computer (or the Photos library on a Mac), and then `gather.py`.

## iPhone + Mac, with iCloud photos (or photos synced to the Photos app)
This is the simplest path. The photos are already on the Mac.
- `gather.py --mac-photos --n 1000 --out ...` (requires `pip install osxphotos`)
- macOS may ask for permission for the terminal to access photos. Allow it.
- It also works with "Optimize Mac Storage". The Mac keeps a preview of almost every photo, and that is enough to classify. Anything with no copy at all is skipped, and the script prints how many.
- If it fails: in Photos, select the photos (Command-A), then File, Export, Export Unmodified Originals, into a folder, and then use `--folder`.

## iPhone + Mac, without iCloud
- Connect a cable, open the Image Capture app, choose a folder, and click Import All.
- Then: `gather.py --folder <the-folder>`

## iPhone + Windows, with iCloud
- Install iCloud for Windows from the Microsoft Store, sign in, and turn Photos on.
- The photos download to `Pictures\iCloud Photos` (find_sources locates that folder on its own).
- Then: `gather.py --folder <the-folder>`

## iPhone, with only a browser
- Open icloud.com/photos, select photos, and download. A download can include up to 1,000 photos, so this path fits a trial run.

## iPhone + Windows, over a cable
- Connect a cable and tap Trust This Computer on the iPhone.
- The Windows Photos app: Import, From a connected device. Or in File Explorer: This PC, Apple iPhone, Internal Storage, DCIM, and copy that to a folder.
- HEIC from the iPhone is fine. The tool reads HEIC.
- Then: `gather.py --folder <the-folder>`

## Android + any computer (copy over a cable)
- Connect a cable, and on the phone notification choose File transfer (MTP).
- On a Mac you need Android File Transfer or OpenMTP (free). On Windows the phone shows up in File Explorer.
- Copy the DCIM/Camera folder (and Pictures/Screenshots, if you want those too) to a folder on the computer.
- Then: `gather.py --folder <the-folder>`

## Android, or anyone who backs up to Google Photos (no cable)
- Open https://takeout.google.com, click Deselect all, check only Google Photos, then Next, then Create export.
- Google emails a link to zip files. That can take from a few minutes to a few hours. Download them to Downloads. **Do not unzip them.**
- `gather.py --folder ~/Downloads` (or whichever folder they are in). The tool extracts only the photos, and reads Google's json files for the original date and location, including truncated names and duplicates.

## How the studio looks on each path
The same. The phone does not matter. What matters is a folder of photos.

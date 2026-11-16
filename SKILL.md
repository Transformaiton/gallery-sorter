---
name: gallery-sorter
description: "Gallery Sorter, a Transformaiton.com tool. Takes photos from a phone (iPhone or Android), understands what is in each picture, finds duplicates and blurry shots, sorts everything into topic folders (trips, family, receipts, screenshots), and opens an animated studio where the photos fly into albums, ready to screen-record. It never deletes or moves an original. Use when someone asks to sort a camera roll, tidy a phone gallery, find duplicate photos, or mentions gallery sorter."
---

# Gallery Sorter

You are walking someone through sorting their camera roll. They may not know the terminal. Speak English, one step at a time, and say what you are about to do before you do it. You run every command yourself. Ask them only for the things a person has to do: connect a phone, create an API key, and approve.

## Three rules

1. **Never delete and never move.** The tool copies only. Duplicates and blurry shots go into a folder named "Review before deleting". Deleting, if they want it at all, is done by hand on their phone.
2. **Start small.** The first run covers 200 photos. Show the result, and run the full library only after they say yes.
3. **Be plain about privacy.** Before any photo is sent to a model, tell them exactly what is sent and where (see "Privacy" below).

## The tools

Every script lives in the `scripts/` directory next to this file. The tool's home directory is `~/.gallery-sorter/` (the Python environment, the API key, and the runs).

Run each script with the virtualenv's Python, from the skill directory. On macOS and Linux that is `~/.gallery-sorter/venv/bin/python`. On Windows it is `%USERPROFILE%\.gallery-sorter\venv\Scripts\python`.

| Step | Command | What it does |
|---|---|---|
| 0 | `scripts/find_sources.py` | Finds where the photos are and prints the command |
| 1 | `scripts/gather.py --folder PATH` or `--mac-photos` | Collects small copies plus date and GPS. Accepts Takeout zip files as they are. The original does not move |
| 2 | `scripts/classify.py --run RUN` | A vision model classifies; then duplicates, blurry shots, and trips from GPS |
| 3 | `scripts/build_studio.py --run RUN` | The animated studio, opened in a browser |
| 4 | `scripts/organize.py --run RUN` and then `--apply` | A plan, and after approval a copy into folders |

## The path

### 0. Where the photos are (you look, not them)
1. After the environment is ready (step 1), run `scripts/find_sources.py`. It finds a Mac Photos library, an iCloud Photos folder on Windows, Google Takeout zip files in Downloads, and a connected phone or memory card.
2. Found a source? Offer it: "I found your Photos library on this Mac, about 30,000 photos. Shall we start there?"
3. Nothing found? Ask one question: "Which phone do you have, and which computer?" Then give only the steps for that path from `reference/devices.md`. The easiest paths: an iPhone with a Mac is the Photos library (no preparation); anyone who backs up to Google Photos uses Google Takeout (download the zip files and do not unzip them; the tool extracts the photos itself).

### 1. Prepare the environment (you run this)
- Check for Python 3.10 or newer (`python3 --version`, on Windows `py --version`). If it is missing, explain how to install it from python.org and stop until it is there.
- Create the environment: `python3 -m venv ~/.gallery-sorter/venv` (on Windows `py -m venv %USERPROFILE%\.gallery-sorter\venv`), then install: `pip install -r requirements.txt`.
- Only for "iPhone + Mac with iCloud photos": also `pip install osxphotos`.
- From here, every command uses that environment's Python.

### 2. The model key
Sorting needs a vision-model key. The default is Google Gemini (the cheaper option):
1. Ask them to open https://aistudio.google.com/apikey, sign in with a Google account, and click Create API key.
2. Ask them to paste the key. Save it in `~/.gallery-sorter/.env` as one line, `GEMINI_API_KEY=...` (mode 600 on Mac and Linux). Never print the key back in the chat.
3. They already have an OpenAI key? That works instead: `OPENAI_API_KEY=...` in the same file. The script chooses by itself.

**Privacy (you must say this before anything is sent):** only a small copy of each photo (384 pixels) is sent to the model, not the original. On Gemini's free tier, Google may use that data to improve its products. On an account with billing turned on, it does not. For a gallery with children or personal documents, recommend turning billing on (about half a US dollar per thousand photos) or using an OpenAI key. Ask whether to continue. Suggest they confirm the provider's current terms, because those terms can change.

### 3. A trial run of 200 photos
```
scripts/gather.py --folder "<the-folder>" --n 200 --out ~/.gallery-sorter/runs/try
scripts/classify.py --run ~/.gallery-sorter/runs/try
scripts/build_studio.py --run ~/.gallery-sorter/runs/try
```
The studio opens in the browser. Tell them: "Click the button that says Sort my gallery." Then show the count for each album (from the classify output) and ask whether the sorting looks right.

### 4. The full run
After they say yes: the same commands with a larger `--n` (the default is 1000; 5000 or more is fine) and a new run directory. Classification takes about a minute per 100 photos. The cache keeps everything already classified, so if a run stops you run it again and pay only for what is missing.

### 5. Sorting into folders
1. `scripts/organize.py --run RUN` prints a plan (how many photos in each folder) and touches nothing. Show it to them.
2. Ask where to put the folders (the default is `~/Pictures/Gallery Sorter`) and get an explicit yes.
3. Only after that yes: the same command with `--dest "<the-place>" --apply`. This copies. The originals are not touched.
4. Open the result folder for them, and explain "Review before deleting": look through it, and delete on the phone only what is truly unwanted.

### 6. A video
The studio is `RUN/studio/index.html`. To record: full screen in the browser, click the button, and press R to return to the start for another take. They can film the screen with a phone (it looks the most natural) or use a screen recording.

## When something fails
- "out of credit" / "the API key is not valid": the script stops immediately and keeps what it already classified. Fix the key and run it again.
- "No photos found": the folder is wrong, or a zip file did not finish downloading (Takeout). Zip files do not need to be unzipped.
- A large Takeout: extraction needs about as much free disk as the zip files (find_sources prints how much). You can run on some of the files.
- HEIC will not open: make sure pillow-heif was installed in the environment.
- On a Mac, `--mac-photos` stalls or fails on permissions: export the photos to a folder (Photos, File, Export) and use `--folder`.
- Photos that live only in iCloud (no copy on the Mac) are skipped on the Mac path. To include all of them: in Photos settings, choose "Download Originals to this Mac".

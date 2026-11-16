# Use Gallery Sorter

This guide is what a sort looks like after the skill is [installed](install.md). Claude can run every command. The scripts are also listed here if you want to run them yourself.

## What a session looks like

Ask Claude to sort your gallery. It should do the following, in order, and tell you before each step.

1. **Find the photos.** It runs `scripts/find_sources.py`, which looks for a Mac Photos library, an iCloud Photos folder on Windows, Google Takeout zips in Downloads or on the Desktop, and a DCIM folder on a connected phone or card. If it finds nothing, it asks which phone and which computer you have, and gives you only that path from [devices](../reference/devices.md).
2. **Prepare Python**, if the virtualenv from the install guide is not there yet.
3. **Ask for a model key**, and explain what is sent off the machine before it sends anything. Say no if you want to stop. Nothing has been labeled yet.
4. **Trial of 200 photos.** It gathers, labels, and opens the studio.
5. **Wait for you.** It shows the count per album and asks whether the labels look right.
6. **The rest of the roll**, only after you say yes. A new run directory is used. The cache means a second pass does not pay again for photos already labeled.
7. **A folder plan**, with no files copied yet.
8. **The copy**, only after you name a folder and say yes. The default destination is `~/Pictures/Gallery Sorter`.

## The studio

`build_studio.py` writes `RUN/studio/index.html` and opens it in your browser. No server is required.

- The button says **Sort my gallery**.
- Counters along the top read Scanned, Albums, To review, and Space to free.
- When it finishes, the center reads **Gallery sorted**.
- Press **R** to play it again from the start. Space or Enter also starts it.
- Up to 1,200 photos are drawn. Past that, the studio samples the roll. The counters still describe the whole run: each tile stands for more than one photo.
- Photos flagged as sensitive are blurred in the studio so a screen recording does not reveal them.

To record a clip: full screen, click the button, and crop to the browser. Press R for another take.

## The folders

`organize.py` copies each photo into one folder. The original path is not changed.

| Folder | What lands here |
|---|---|
| `Trip · Month Year` | A run of days away from the place you take the most photos, named from the date in the middle of the trip |
| `Trips` | Travel photos that did not form a long enough trip to name |
| `Family` | Family, children, home |
| `Friends and events` | Friends, parties, weddings, birthdays |
| `Food` | Meals, cafes, drinks |
| `Pets` | Dogs, cats, other pets |
| `Nature and scenery` | Nearby outdoors: a park, the sea, a sunset |
| `Work` | Office, slides, whiteboards, a computer on a desk |
| `Receipts and documents` | Receipts, invoices, and photos of paper documents |
| `Things I saved` | Screenshots you kept to come back to: a recipe, a product, a note |
| `Screenshots` | Other screenshots: chats, settings, maps, app screens |
| `Memes` | Jokes and pictures saved from the internet |
| `Shopping` | Products and price comparisons |
| `Miscellaneous` | Anything that did not fit |
| `Review before deleting/Duplicates` | Extra frames from the same moment. The sharpest one stays in its topic folder |
| `Review before deleting/Blurry` | Shots that are clearly out of focus, or pocket and accidental frames |

Deleting is not part of the tool. Open `Review before deleting`, look at it, and remove the copies you do not want. If you also want them gone from the phone, delete them there yourself.

A sample run looks like this:

```
Gallery Sorter/
├── Family/                              6
├── Food/                                6
├── Friends and events/                  6
├── Memes/                               1
├── Nature and scenery/                  6
├── Pets/                                6
├── Receipts and documents/              7
├── Screenshots/                         6
├── Shopping/                            6
├── Things I saved/                      1
├── Trip · June 2024/                   10
├── Work/                                6
└── Review before deleting/
    ├── Blurry/                          4
    └── Duplicates/                      2
```

Those counts are from [`examples/demo-roll`](../examples/demo-roll), which is a generated roll, not a person's photos. Duplicate grouping, blur, and the June 2024 trip were computed by the tool from the files. The topic labels on that roll were filled in locally so the figure did not need an API key. On your photos, Gemini or OpenAI chooses the topic.

## Run the scripts yourself

From the skill directory, with the virtualenv's Python. On Windows, use `%USERPROFILE%\.gallery-sorter\venv\Scripts\python` in place of the path below.

```bash
PY=~/.gallery-sorter/venv/bin/python

# Where are the photos?
$PY scripts/find_sources.py

# Trial. Originals are not moved.
$PY scripts/gather.py --folder "$HOME/Pictures/From-My-Phone" --n 200 \
  --out ~/.gallery-sorter/runs/try

$PY scripts/classify.py --run ~/.gallery-sorter/runs/try
$PY scripts/build_studio.py --run ~/.gallery-sorter/runs/try --title "My gallery"

# Plan only. Read it before you copy.
$PY scripts/organize.py --run ~/.gallery-sorter/runs/try

# Copy, after the plan looks right.
$PY scripts/organize.py --run ~/.gallery-sorter/runs/try \
  --dest "$HOME/Pictures/Gallery Sorter" --apply
```

Useful options:

| Option | Where | What it does |
|---|---|---|
| `--n 200` | gather | How many photos, newest first. The default is 1000 |
| `--mac-photos` | gather | Read the Mac Photos library instead of a folder. Needs `osxphotos` |
| `--library PATH` | gather | A Photos library that is not the default one |
| `--folder DIR` | gather | A folder of photos, or a folder of Takeout zip files, or one zip |
| `--model NAME` | classify | Override the model. The default is `gemini-3-flash-preview`, or `gpt-5.4-mini` with an OpenAI key |
| `--title "..."` | build_studio | The small line above the photo count in the studio |
| `--no-open` | build_studio | Write the studio but do not launch a browser |
| `--dest PATH` | organize | Where the folders are created. Default `~/Pictures/Gallery Sorter` |
| `--apply` | organize | Actually copy. Without it, you only get the plan |

A full library is the same commands with a larger `--n` and a new `--out` directory, for example `~/.gallery-sorter/runs/all`. Labeling takes about a minute per 100 photos. If it stops, run `classify.py` again on the same run. The cache file `gemini.json` inside the run holds every label already paid for.

### Mac Photos

```bash
$PY scripts/gather.py --mac-photos --n 1000 --out ~/.gallery-sorter/runs/try
```

macOS may ask the terminal for permission to read photos. Allow it. Photos that exist only in iCloud, with no preview on the Mac, are skipped, and the script prints how many. To include them, in Photos settings choose **Download Originals to this Mac** and wait for the download.

If `--mac-photos` stalls or fails on permissions, export from Photos (File, Export, Export Unmodified Originals) and use `--folder` on that export.

### Google Takeout

Do not unzip the download. Point `--folder` at the directory that contains the `takeout-*.zip` files, or at a single zip. The script extracts photos and the json sidecars (date and location) and skips video. Extraction needs roughly as much free disk as the zip files. `find_sources.py` prints the size.

## How a trip is decided

"Home" is the map cell, about 50 kilometers across, that contains the most photos. A photo more than 80 kilometers from that cell is "away". Away photos are grouped into trips, and a gap of more than three days starts a new trip. A group of at least eight photos is named with the month and year of the photo in the middle, for example `Trip · June 2024`. A shorter group is filed under `Trips`.

This uses the location stored in the photo. A picture with no GPS stays in its topic folder.

## How a duplicate is decided

Two photos are treated as the same moment when their visual signatures are close and they were taken within ten minutes. The sharpest one keeps its topic folder. The others are copied to `Review before deleting/Duplicates`. Screenshots of the same app are compared more strictly, so two similar settings screens are not collapsed unless they really match.

Blur is a local sharpness score, and only when the model also calls the photo blurry. Pocket shots and black frames are filed with the blurry photos. Both wait for you. Neither is deleted.

## The sample roll

[`examples/demo-roll`](../examples/demo-roll) is a set of generated pictures: food, a desk, pets, a coastline, receipts marked as samples, and so on. It is there so you can see the kind of output the tool produces, and so `gather.py` can be tried with no API key.

```bash
$PY scripts/gather.py --folder examples/demo-roll --n 80 \
  --out ~/.gallery-sorter/runs/sample
```

Labeling that roll, like labeling yours, calls Gemini or OpenAI.

## Privacy, again

- Originals stay where they are. `gather.py` writes small JPEGs under `~/.gallery-sorter/runs/`.
- The model sees the 384-pixel copy only.
- Free-tier Gemini may use submissions to improve Google's products. A billed account does not. Read the current terms.
- Sensitive photos are blurred in the studio and nowhere else. The copy in your folders is the original file.
- The API key lives in `~/.gallery-sorter/.env`. It is not written into the run folder.

## Troubleshooting

**"The API key is not valid. Create a new key and save it again."**
The key was rejected. Create a new one at https://aistudio.google.com/apikey (or replace the OpenAI key) and update `~/.gallery-sorter/.env`. Run `classify.py` again on the same `--run`. Labels already saved are kept.

**"The model provider account is out of credit."**
Add credit, or switch keys, then run `classify.py` again. You pay only for photos that are not in the cache yet.

**"No photos found."**
The folder does not contain images the tool can read (jpg, jpeg, png, heic, heif, webp), or a Takeout zip did not finish downloading. Zip files do not need to be unzipped first. Hidden files and folders are skipped.

**"Not found: ..."**
The `--folder` path is wrong. Quote paths that contain spaces.

**"osxphotos is missing."**
You used `--mac-photos` without the extra package. `pip install osxphotos` inside the virtualenv, or export to a folder and use `--folder`.

**HEIC files are skipped.**
`pillow-heif` is not installed in the virtualenv. Re-run `pip install -r requirements.txt` with that environment's Python.

**Takeout needs more disk than you have.**
Extract only some of the zip files: pass `--folder` a directory that contains the ones you want, or pass a single zip. `find_sources.py` prints how much space the full set wants.

**`--mac-photos` hangs or errors on permissions.**
Export the photos to a folder from the Photos app and use `--folder`. To classify photos that have no local copy, turn on Download Originals to this Mac.

**The same photo was copied twice under a name like `IMG_1 (1).jpg`.**
Two source files had the same name. The copy adds a number rather than overwriting. Both originals are still untouched.

**The studio is empty or will not open.**
`classify.py` has to finish before `build_studio.py`. The file to open is `RUN/studio/index.html`. If the browser did not launch, open that file yourself. `--no-open` is how you build it without launching.

**A label is wrong.**
The folders are a copy. Move that copy where you like. The original is still in the camera roll, unchanged. A later run does not rewrite a destination folder you have already edited, but `--apply` will add files. It will not delete ones you removed from the destination.

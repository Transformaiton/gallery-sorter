# Install Gallery Sorter

Gallery Sorter is a Claude Code skill. Claude runs it for you. This guide is the full install, including the manual path if you would rather not start from a pasted prompt.

## What you need

- A Mac or a Windows PC. Linux works for the scripts as well.
- [Claude Code](https://claude.com/claude-code), installed and signed in.
- Python 3.10 or newer. Check with `python3 --version` (on Windows, `py --version`). If Python is missing, install it from [python.org](https://www.python.org/downloads/) and come back.
- The photos, or a way to get them onto this computer. Paths for each phone are in [devices](../reference/devices.md).
- A Google account for a Gemini API key, or an existing OpenAI API key.

You do not install a separate app. The skill is a folder of instructions and scripts that Claude Code reads.

## 1. Install the skill

### With Claude Code

Open Claude Code, paste the following, and send it.

> Install the "Gallery Sorter" skill from https://github.com/Transformaiton/gallery-sorter : clone the repo into my skills folder, ~/.claude/skills/gallery-sorter (if git is not available, download the zip of the repo and extract it there). Then start the skill, tell me what you are doing, and walk me through sorting my gallery one step at a time. Talk to me in English.

Claude should clone the repo to:

- macOS and Linux: `~/.claude/skills/gallery-sorter`
- Windows: `%USERPROFILE%\.claude\skills\gallery-sorter`

Then it should explain the next step in English before it does anything.

### By hand

From a terminal:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Transformaiton/gallery-sorter.git ~/.claude/skills/gallery-sorter
```

On Windows, in PowerShell:

```powershell
git clone https://github.com/Transformaiton/gallery-sorter.git "$env:USERPROFILE\.claude\skills\gallery-sorter"
```

If git is not installed, download the zip from https://github.com/Transformaiton/gallery-sorter and extract it so that `SKILL.md` sits directly inside the `gallery-sorter` folder above. The folder name matters. Claude Code looks for skills by that directory name.

Start a new Claude Code session in any folder and ask it to sort your gallery. The skill's description is what makes Claude pick it up.

## 2. Let Claude prepare Python

You can leave this to Claude. If you want to do it yourself, from the skill folder:

```bash
python3 -m venv ~/.gallery-sorter/venv
~/.gallery-sorter/venv/bin/python -m pip install -r requirements.txt
```

On Windows:

```powershell
py -m venv "$env:USERPROFILE\.gallery-sorter\venv"
& "$env:USERPROFILE\.gallery-sorter\venv\Scripts\python" -m pip install -r requirements.txt
```

That environment is shared by every run. The skill does not install packages into the rest of your system.

iPhone photos in the Mac Photos app also need one extra package, and only on that path:

```bash
~/.gallery-sorter/venv/bin/python -m pip install osxphotos
```

## 3. Create a model key

Labeling needs a vision model. Gemini is the default because it costs less.

1. Open https://aistudio.google.com/apikey and sign in.
2. Click **Create API key**.
3. Paste the key into Claude when it asks. Claude saves it as one line in `~/.gallery-sorter/.env`:

```
GEMINI_API_KEY=your-key-here
```

On Mac and Linux the file should be readable only by you (`chmod 600 ~/.gallery-sorter/.env`). Do not commit this file, and do not paste the key into a ticket or a chat you do not control. Claude is instructed not to print the key back.

An OpenAI key works in the same file, as `OPENAI_API_KEY=...`. If both are present, the scripts use Gemini.

### What gets sent

Before the first photo is labeled, Claude should tell you this in plain language:

- The model receives a 384-pixel copy. The original file is not uploaded.
- On Gemini's free tier, Google may use that data to improve its products.
- On a Gemini account with billing turned on, it does not.
- A camera roll with children or personal documents should use billing, or an OpenAI key.

About half a US dollar per thousand photos is the right planning number for paid Gemini. Check the provider's current price. The free tier is enough for a 200-photo trial if you accept the free-tier terms.

## 4. Confirm the install

Ask Claude to sort your gallery, or point it at the sample photos:

```bash
~/.gallery-sorter/venv/bin/python scripts/gather.py \
  --folder examples/demo-roll \
  --n 80 \
  --out ~/.gallery-sorter/runs/sample
```

`gather.py` only makes small copies. It does not call the model and it does not change `examples/demo-roll`. A line like `done: 73 images` means the environment can read the photos.

The next step, `scripts/classify.py`, is the one that uses the API key. A trial of your own photos is covered in the [usage guide](usage.md).

## Update

From the skill folder:

```bash
git -C ~/.claude/skills/gallery-sorter pull
```

Your key and your previous runs stay in `~/.gallery-sorter/`. Pulling the skill does not touch them.

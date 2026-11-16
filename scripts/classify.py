"""Step 2: what is in each photo, what is a duplicate, what is blurry, and which trip it belongs to.

- Content: a vision model (Gemini, or OpenAI when there is no Gemini key) sees the small copies (384px)
  in batches of 10 and returns a category and a short English tag.
- Duplicates: a local visual signature (dHash) plus a capture time within 10 minutes. The sharpest photo in each group is kept.
- Blurry shots: a local sharpness score, and only when the model agrees.
- Trips: from the GPS stored in the photo. "Home" is the area with the most photos; consecutive days away from it are a trip.

Model results are cached, so a second run does not pay again.

  python scripts/classify.py --run ~/.gallery-sorter/runs/run1
"""
import argparse
import base64
import json
import math
import time
from collections import Counter
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from common import MONTHS, provider

CATS = {
    "trip": "a trip or vacation: travel scenery, a landmark, a hotel, an airport, a street in another city",
    "family": "family, children, babies, moments at home",
    "friends": "friends, events, weddings, birthdays, parties",
    "food": "food, restaurants, cafes, drinks",
    "pets": "a dog, cat, or other pet",
    "nature": "scenery and nature close to home: a sunset, the sea, a park, the sky",
    "work": "work: an office, a talk, a slide, a team, a whiteboard, a computer screen",
    "receipt": "a receipt, invoice, payment confirmation, order, or boarding pass",
    "docs": "a photo of a paper document, certificate, contract, note, or notice board",
    "saved": "a screenshot saved to come back to: a recipe, tip, post, article, idea, or product",
    "screens": "any other screenshot: a chat, settings, a map, an app screen",
    "memes": "a meme, a joke, or a funny picture from the internet",
    "shopping": "a product in a store, shopping, comparing prices",
    "other": "none of the above",
}
PROMPT = f"""You sort a person's phone camera roll. For EACH image (numbered in order), return:
- "cat": exactly one key from this list:
{json.dumps(CATS, ensure_ascii=False, indent=1)}
- "tag": 2-4 English words naming what is in the image, specific (e.g. "beach at sunset", "grocery receipt", "cake recipe").
- "blurry": true only if the image is clearly out of focus or motion-blurred.
- "accidental": true if it is an accidental shot (pocket, floor, black frame, finger).
- "sensitive": true if it shows private data (ID card, bank details, phone numbers in a private chat, passwords, nudity).
Return ONLY a JSON array with one object per image, in the same order, each with keys n,cat,tag,blurry,accidental,sensitive."""


class Fatal(Exception):
    """An error that should not be retried (bad key, out of credit)."""


def fatal_reason(msg):
    m = msg.lower()
    if "api key" in m or "api_key_invalid" in m or "permission_denied" in m or "incorrect api key" in m or " 401" in m:
        return "The API key is not valid. Create a new key and save it again."
    if "credits are depleted" in m or "insufficient_quota" in m or "billing" in m or " 402" in m:
        return "The model provider account is out of credit. Add credit (or switch keys) and run again: everything already classified is saved."
    return None


def ask_gemini(key, model, idxs, run):
    from google import genai
    from google.genai import types
    cl = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=120000))
    parts = []
    for k, i in enumerate(idxs, 1):
        parts.append(types.Part.from_text(text=f"Image {k}:"))
        parts.append(types.Part.from_bytes(data=(run / "cls" / f"{i:05d}.jpg").read_bytes(), mime_type="image/jpeg"))
    parts.append(types.Part.from_text(text=PROMPT))
    r = cl.models.generate_content(model=model, contents=parts, config=types.GenerateContentConfig(
        response_mime_type="application/json", temperature=0.2))
    return json.loads(r.text)


def ask_openai(key, model, idxs, run):
    content = []
    for k, i in enumerate(idxs, 1):
        b64 = base64.b64encode((run / "cls" / f"{i:05d}.jpg").read_bytes()).decode()
        content += [{"type": "input_text", "text": f"Image {k}:"},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}", "detail": "low"}]
    content.append({"type": "input_text", "text": PROMPT + '\nWrap the array as {"items": [...]}.'})
    body = {"model": model, "input": [{"role": "user", "content": content}],
            "text": {"format": {"type": "json_object"}}, "reasoning": {"effort": "low"}}
    req = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code} {e.read().decode()[:300]}")
    text = "".join(c.get("text", "") for o in out.get("output", []) if o.get("type") == "message"
                   for c in o.get("content", []) if c.get("type") == "output_text")
    j = json.loads(text)
    return j.get("items", j) if isinstance(j, dict) else j


def classify_batch(prov, model, run, idxs):
    name, key = prov
    for attempt in range(5):
        try:
            arr = (ask_gemini if name == "gemini" else ask_openai)(key, model, idxs, run)
            if len(arr) == len(idxs):
                return {i: a for i, a in zip(idxs, arr)}
            got = {idxs[a["n"] - 1]: a for a in arr if isinstance(a.get("n"), int) and 1 <= a["n"] <= len(idxs)}
            if got:
                return got
        except Exception as e:
            why = fatal_reason(str(e))
            if why:
                raise Fatal(why)
            print("retry", attempt, str(e)[:160], flush=True)
            time.sleep(5 * (attempt + 1))  # rate limit (especially on the free tier): wait and try again
    return {}


def dhash(path, size=8):
    a = np.asarray(Image.open(path).convert("L").resize((size + 1, size), Image.LANCZOS), dtype=np.int16)
    return int("".join("1" if b else "0" for b in (a[:, 1:] > a[:, :-1]).flatten()), 2)


def sharpness(path):
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    lap = a[1:-1, 1:-1] * -4 + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
    return float(lap.var())


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--model", help="default: gemini-3-flash-preview, or gpt-5.4-mini when the key is for OpenAI")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    run = Path(args.run).expanduser()
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))

    # 1. Classify content
    cache_f = run / "gemini.json"
    cache = {int(k): v for k, v in json.loads(cache_f.read_text()).items()} if cache_f.exists() else {}
    cache = {k: v for k, v in cache.items() if v.get("tag")}
    prov = provider()
    model = args.model or ("gemini-3-flash-preview" if prov[0] == "gemini" else "gpt-5.4-mini")
    print(f"model: {prov[0]} / {model}", flush=True)
    for size in (10, 4, 1):  # anything missed in a large batch is tried again in smaller batches
        todo = [m["i"] for m in meta if m["i"] not in cache]
        if not todo:
            break
        batches = [todo[k:k + size] for k in range(0, len(todo), size)]
        print(f"classify: {len(todo)} images, batch {size}", flush=True)
        done = 0
        try:
            with ThreadPoolExecutor(args.workers) as ex:
                for res in ex.map(lambda b: classify_batch(prov, model, run, b), batches):
                    cache.update(res); done += 1
                    if done % 10 == 0:
                        print(f"  {min(done * size, len(todo))}/{len(todo)}", flush=True)
                        cache_f.write_text(json.dumps(cache, ensure_ascii=False))
        except Fatal as e:
            cache_f.write_text(json.dumps(cache, ensure_ascii=False))
            raise SystemExit(f"Stopped: {e} (classified {len(cache)} of {len(meta)} so far)")
        cache_f.write_text(json.dumps(cache, ensure_ascii=False))

    # 2. Sharpness, signatures, and a first assignment
    for m in meta:
        p = run / "cls" / f"{m['i']:05d}.jpg"
        g = cache.get(m["i"], {})
        m["sharp"] = sharpness(p)
        m["dh"] = dhash(p)
        m["cat"] = g.get("cat") if g.get("cat") in CATS else "other"
        m["tag"] = g.get("tag", "")
        m["sensitive"] = bool(g.get("sensitive"))
        m["blurry"] = bool(g.get("blurry")) and m["sharp"] < 120
        m["accidental"] = bool(g.get("accidental"))
        m["ts"] = datetime.fromisoformat(m["date"]).timestamp()

    # 3. Duplicates: only neighbors in time are compared (fast even at 10,000 photos). The sharpest in each group is kept
    by_time = sorted(meta, key=lambda m: m["ts"])
    keep_of = {}
    for k, a in enumerate(by_time):
        for b in by_time[k + 1:]:
            if b["ts"] - a["ts"] > 600:
                break
            lim = 1 if (a["screenshot"] or b["screenshot"]) else 4  # screenshots of the same app look alike even when they differ
            if bin(a["dh"] ^ b["dh"]).count("1") <= lim:
                ra, rb = keep_of.get(a["i"], a["i"]), keep_of.get(b["i"], b["i"])
                if ra == rb:
                    continue
                best = max((ra, rb), key=lambda i: meta[i]["sharp"])
                worse = rb if best == ra else ra
                for x, r in list(keep_of.items()):
                    if r == worse:
                        keep_of[x] = best
                keep_of[worse] = best
    for m in meta:
        m["dup_of"] = keep_of.get(m["i"])

    # 4. Trips from GPS: home = the cell (about 50 km) with the most photos
    geo = [m for m in meta if m.get("lat") is not None]
    trip_of = {}
    if len(geo) >= 10:
        cells = Counter((round(m["lat"] * 2) / 2, round(m["lon"] * 2) / 2) for m in geo)
        home = cells.most_common(1)[0][0]
        away = sorted([m for m in geo if km((m["lat"], m["lon"]), home) > 80], key=lambda m: m["ts"])
        groups, cur = [], []
        for m in away:  # a gap of more than three days starts a new trip
            if cur and m["ts"] - cur[-1]["ts"] > 3 * 86400:
                groups.append(cur); cur = []
            cur.append(m)
        if cur:
            groups.append(cur)
        names = Counter()
        for g in groups:
            if len(g) < 8:
                for m in g:
                    trip_of[m["i"]] = "*"
                continue
            d = datetime.fromtimestamp(g[len(g) // 2]["ts"])
            name = f"{MONTHS[d.month - 1]} {d.year}"
            names[name] += 1
            if names[name] > 1:
                name += f" ({names[name]})"
            for m in g:
                trip_of[m["i"]] = name
        print("home cell:", home, "| trips:", sorted(set(trip_of.values())))
    for m in meta:
        m["trip"] = trip_of.get(m["i"]) or ("*" if m["cat"] == "trip" else None)

    # 5. Final assignment
    for m in meta:
        if m["dup_of"] is not None:
            m["album"] = "dupes"
        elif m["blurry"] or m["accidental"]:
            m["album"] = "blurry"
        elif m["trip"]:
            m["album"] = "trip" if m["trip"] == "*" else "trip:" + m["trip"]
        else:
            m["album"] = "receipt" if m["cat"] == "docs" else m["cat"]
        m.pop("dh", None)
    (run / "sorted.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    c = Counter(m["album"] for m in meta)
    for k, v in c.most_common():
        print(f"{v:6d}  {k}")
    freed = sum(m.get("bytes") or 0 for m in meta if m["album"] in ("dupes", "blurry"))
    print(f"review before delete: {c['dupes'] + c['blurry']} images, {freed / 1e6:.0f}MB")


if __name__ == "__main__":
    main()

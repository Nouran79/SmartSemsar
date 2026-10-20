# Smart Semsar - furnish the whole apartment with your own furniture (several photos)
# VS Code / Windows version of SmartSemsar_multi_photo_edit.ipynb (Colab).
#
# Before you run:
#   1. VS Code with the Python and Jupyter extensions, Python 3.11, Git for Windows.
#   2. Once, in the VS Code terminal:
#        pip install shapely trimesh scipy mapbox_earcut pandas pydantic pillow requests gradio gradio_client python-dotenv
#   3. A file called .env next to this file with your keys:
#        HF_TOKEN=...
#        GEMINI_API_KEY=...
#        GROQ_API_KEY=...
#        SMARTSEMSAR_KEY=...      (the same password the diffusion server uses)
#        GITHUB_TOKEN=...         (only if the repository is private)
#   4. Start the diffusion server on Kaggle and put its address in COLAB_URL below.
#
# Run it: "Run All Cells" (the # %% lines are cells, like a notebook), or
#         python SmartSemsar_multi_photo_vscode.py
# Then open http://127.0.0.1:7860 (it opens by itself).


# %% 1. Settings
import os
import sys
from pathlib import Path

SHARE = False          # True = Gradio also gives a public https://....gradio.live link
PORT = int(os.environ.get("SMARTSEMSAR_FURNISH_PORT", "7861"))   # the Streamlit app opens this port
# --from-app: started by the "فرش ومعاينة" button (frontend/views/chat_view.py):
# skip the slow model check in cell 4 and do not open a browser tab of its own
FROM_APP = "--from-app" in sys.argv

# this file sits in the project folder, so the project's own code is used (nothing is cloned)
try:
    HERE = Path(__file__).resolve().parent
except NameError:      # running cell by cell in the interactive window
    HERE = globals().get("HERE") or Path.cwd()
REPO_DIR = HERE
ENV_FILE = HERE / ".env"
print("code folder:", REPO_DIR, "| .env found:", ENV_FILE.exists())


# %% 2. The keys
from dotenv import load_dotenv

load_dotenv(ENV_FILE)          # the keys from .env go into os.environ (they are never printed)


def secret(name):
    return os.environ.get(name, "")


os.chdir(REPO_DIR)
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))
COLAB_URL = secret("SMARTSEMSAR_COLAB_URL").strip()   # the diffusion server, from .env (empty = TRELLIS.2)


# %% 3. Keys
KEYS = {"HF_TOKEN": ["HF_TOKEN", "HF_TOKEN_3", "HF_TOKEN_2"],
        "GEMINI_API_KEY": ["GEMINI_API_KEY", "AGENT_API_KEY_2"],
        "GROQ_API_KEY": ["GROQ_API_KEY", "GROQ_API_KEY_2"],
        "SMARTSEMSAR_COLAB_KEY": ["SMARTSEMSAR_COLAB_KEY", "SMARTSEMSAR_KEY"]}
found = {env: next((n for n in names if secret(n)), None) for env, names in KEYS.items()}
os.environ.update({env: "".join(secret(n).split()) for env, n in found.items() if n})
if COLAB_URL:
    os.environ["SMARTSEMSAR_COLAB_URL"] = COLAB_URL
print({env: ("set from " + n) if n else "NOT SET" for env, n in found.items()})


# %% 4. Which Gemini and Groq models work right now
# Which Gemini and Groq models answer right now? Each is really called (text, and a photo for vision);
# the first one that works is the one the app uses. Only model names and OK / the error are printed.
import requests
from backend.services import vision_service as vs
from backend.services.llm_furnisher import LLMClient

PHOTO = REPO_DIR / "OIP.jpg"            # a small furniture photo that ships with the repo
ASK = 'Look at the photo and answer only JSON: {"kind": "<what furniture it is>"}'
GEMINI_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-lite-latest", "gemini-2.5-flash-lite"]
GROQ_TEXT_MODELS = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "llama-3.1-8b-instant"]
SKIP = ("whisper", "tts", "guard", "compound", "playai", "orpheus", "allam")


def short(e):
    return f"{type(e).__name__}: {str(e)[:110]}"


def works_text(name, url, model, key):
    try:
        LLMClient(name, url, model, key, timeout=40).chat_json(
            [{"role": "user", "content": 'Answer only this JSON: {"ok": true}'}])
        return "OK"
    except Exception as e:
        return short(e)


def first_working(models, test):
    results = {m: test(m) for m in models}
    for m, r in results.items():
        print(f"   {m:45s} {r}")
    return next((m for m, r in results.items() if r == "OK"), None)


gem_key, groq_key = os.environ.get("GEMINI_API_KEY"), os.environ.get("GROQ_API_KEY")
if FROM_APP:           # opened from the app: start fast, the services fall back to their default models
    gem_key = groq_key = None
    print("Started from the app: model check skipped")
chosen = {}

if gem_key:
    print("Gemini, photo reading:")
    def gem_photo(m):
        try:
            vs._ask_gemini(ASK, PHOTO, gem_key, m, vs.DEFAULT_URL, 40)
            return "OK"
        except Exception as e:
            return short(e)
    chosen["Gemini photo"] = first_working(GEMINI_MODELS, gem_photo)
    print("Gemini, arranging furniture (text):")
    chosen["Gemini text"] = first_working(GEMINI_MODELS, lambda m: works_text(
        "gemini", "https://generativelanguage.googleapis.com/v1beta/openai", m, gem_key))
    # the app reads one Gemini model name for both jobs: prefer one that does both
    both = chosen["Gemini photo"] if chosen["Gemini photo"] and chosen["Gemini photo"] == chosen["Gemini text"] else \
        (chosen["Gemini photo"] or chosen["Gemini text"])
    if both:
        os.environ["SMARTSEMSAR_GEMINI_MODEL"] = both
elif not FROM_APP:
    print("GEMINI_API_KEY not set")

if groq_key:
    try:
        ids = sorted(m["id"] for m in requests.get("https://api.groq.com/openai/v1/models", timeout=20,
                                                   headers={"Authorization": f"Bearer {groq_key}"}).json()["data"])
    except Exception as e:
        ids = []
        print("Could not list Groq models:", short(e))
    print("Groq models available:", ", ".join(ids))
    # vision: likely names first, then every other chat model, until one reads the photo
    likely = [i for i in ids if any(w in i.lower() for w in ("llama-4", "vision", "-vl", "scout", "maverick", "qwen"))]
    rest = [i for i in ids if i not in likely and not any(w in i.lower() for w in SKIP)]
    print("Groq, photo reading:")
    def groq_photo(m):
        try:
            vs._ask_groq(ASK, PHOTO, groq_key, m, 40)
            return "OK"
        except Exception as e:
            return short(e)
    chosen["Groq photo"] = None
    for m in likely + rest:
        r = groq_photo(m)
        print(f"   {m:45s} {r}")
        if r == "OK":
            chosen["Groq photo"] = m
            os.environ["SMARTSEMSAR_GROQ_VISION_MODEL"] = m
            break
    print("Groq, arranging furniture (text):")
    text_models = [m for m in GROQ_TEXT_MODELS if m in ids] + [m for m in ids if m not in GROQ_TEXT_MODELS and not any(w in m.lower() for w in SKIP)]
    chosen["Groq text"] = first_working(text_models[:4], lambda m: works_text(
        "groq", "https://api.groq.com/openai/v1", m, groq_key))
    if chosen["Groq text"]:
        os.environ["SMARTSEMSAR_GROQ_MODEL"] = chosen["Groq text"]
elif not FROM_APP:
    print("GROQ_API_KEY not set")

print("\n=== used by the app ===")
for job, m in chosen.items():
    print(f"{job:14s} {m or 'NONE WORKS'}")


# %% 5. Is the diffusion server there?
from backend.services import colab_service
if COLAB_URL:
    try:
        print("server:", colab_service.health())
    except Exception as e:
        print("Server not reachable, so photos will go to TRELLIS.2.", e)
        os.environ.pop("SMARTSEMSAR_COLAB_URL", None)
else:
    print("No COLAB_URL: photos go to TRELLIS.2 (needs HF_TOKEN; daily quota).")


# %% 6. Many photos -> many pieces -> the furnished apartment
# Many photos -> each becomes a 3D piece -> the whole apartment furnished with them.
# After that the apartment can be changed without starting over: add or swap photos (only the new
# ones go to the 3D server), keep the last layout, move / turn / remove / add single items.
# Uses the project's own code (furniture-merge branch); nothing in the repository is changed.
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from backend.config import setting
from backend.schema.design import DesignPreferences
from backend.schema.plan import load_plan
from backend.schema.staging import load_catalog, save_staging
from backend.services import colab_service, trellis_service, vision_service
from backend.services.custom_furniture import FRONT_TURN_DEG, add_furniture_model
from backend.services.furniture_placer import stage_plan
from backend.services.llm_furnisher import furnish as llm_furnish
from backend.services.staging_validator import validate_staging
from backend.services.walkthrough import build_walkthrough
from inference import OUT_DIR, ROOT, load_listings, place_unplaced

GENERATORS = {"colab": colab_service, "trellis": trellis_service}
RAW_DIR = OUT_DIR / "_raw_models"      # one raw 3D model per photo, reused when only the table changes


def default_generator():
    return "colab" if setting("SMARTSEMSAR_COLAB_URL") else "trellis"


MAIN_PIECE_PROMPT = """This photo shows more than one piece of furniture (for example a bed with nightstands).
Find the MAIN piece: the biggest one, the subject of the photo. Answer with ONE JSON object, nothing else:
{{"kind": one of {kinds}, "width_m": its real width in meters,
  "left": .., "top": .., "right": .., "bottom": ..}}
left/top/right/bottom: the edges of the main piece only, in percent (0-100) of the image width and height."""


def main_piece(path, kinds):
    """Several pieces in one photo -> {"kind", "width_m", "box"} of the main one, or None."""
    prompt = MAIN_PIECE_PROMPT.format(kinds=json.dumps(kinds))
    gemini, groq = setting(vision_service.KEY_ENV), setting(vision_service.GROQ_KEY_ENV)
    asks = [lambda m=m: vision_service._ask_gemini(prompt, Path(path), gemini, m, vision_service.DEFAULT_URL, 60)
            for m in dict.fromkeys([setting(vision_service.MODEL_ENV, vision_service.DEFAULT_MODEL),
                                    vision_service.BACKUP_MODEL]) if gemini]
    if groq:
        asks.append(lambda: vision_service._ask_groq(prompt, Path(path), groq, setting(
            vision_service.GROQ_MODEL_ENV, vision_service.GROQ_DEFAULT_MODEL), 60))
    for ask in asks:
        try:
            data = ask()
            break
        except vision_service.VisionError:
            continue
    else:
        return None
    kind = "_".join(str(data.get("kind") or "").strip().lower().split())
    if kind not in kinds:
        return None
    try:
        width = float(data.get("width_m"))
        width = width if vision_service.WIDTH_RANGE_M[0] <= width <= vision_service.WIDTH_RANGE_M[1] else None
    except (TypeError, ValueError):
        width = None
    try:
        box = [float(data[k]) / 100 for k in ("left", "top", "right", "bottom")]
    except (KeyError, TypeError, ValueError):
        box = None
    return {"kind": kind, "width_m": width, "box": box}


def read_photo(path, catalog=None):
    """What the vision model sees in one photo -> {"kind", "width_m", "note"} (kind "" if unknown).
    A photo with several pieces is placed as its main piece; the photo is used as it is (never cut),
    so the 3D model keeps every detail the customer sees in it."""
    if not vision_service.is_configured():
        return {"kind": "", "width_m": None, "note": "no vision key: fill in 'what is it' yourself"}
    try:
        seen = vision_service.analyze_photo(path, catalog)
    except vision_service.VisionError as e:
        return {"kind": "", "width_m": None, "note": f"could not read it ({str(e)[:70]}): fill it in yourself"}
    note = seen.name or seen.scene
    if not seen.kind and seen.scene in ("several_items", "room"):
        main = main_piece(path, sorted({i.kind for i in (catalog or load_catalog()).items if i.kind}))
        if main:
            return {"kind": main["kind"], "width_m": main["width_m"] or seen.width_m,
                    "note": f"{note} - placed as {main['kind']}, photo used as it is"}
    if not seen.usable:
        note += f" - {seen.reason}"
    return {"kind": seen.kind or "", "width_m": seen.width_m, "note": note}


def raw_model(photo, generator, say=print):
    """Photo -> raw GLB. Made once per photo and generator; a second run with the same photo reuses it."""
    digest = hashlib.sha1(Path(photo).read_bytes()).hexdigest()[:12]
    raw = RAW_DIR / f"{generator}_{digest}.glb"
    if raw.exists():
        say("     3D model reused (same photo as before)")
        return raw
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    # a coloured piece takes about 3 minutes on a T4; wait up to 10 instead of the client's default 5
    options = {"timeout": 600} if generator == "colab" else {}
    GENERATORS[generator].generate_model(photo, raw, **options)
    say(f"     3D model made in {time.time() - t0:.0f} s")
    return raw


def assign_slots(pieces, catalog, say=print):
    """Each piece takes one stock catalog item of its kind: the first sofa photo takes the first sofa
    model, a second sofa photo the next one. A kind with no free model left is skipped.
    'what is it' may also be a catalog id (e.g. sofa_2_seat) to pick the model yourself."""
    kinds = {i.kind for i in catalog.items}
    used, out = set(), []
    for n, p in enumerate(pieces, 1):
        want = "_".join((p.get("kind") or "").strip().lower().replace("-", " ").split())   # "Console table" -> console_table
        if not want:
            say(f"  {n}. {p['label']}: skipped (say what it is)")
            continue
        if want not in kinds and want not in {i.id for i in catalog.items}:
            say(f"  {n}. {p['label']}: skipped ('{want}' is not one of {sorted(kinds)})")
            continue
        free = [i for i in catalog.items if (i.kind == want or i.id == want) and i.id not in used]
        if not free:
            say(f"  {n}. {p['label']}: skipped (all {want} models are already taken by other photos)")
            continue
        used.add(free[0].id)
        out.append({**p, "slot": free[0].id})
    return out


def open_listing(property_id):
    """-> (listing row, plan path, plan, output folder) of one apartment."""
    rows = load_listings()
    listing = rows[rows["property_id"] == property_id].iloc[0].to_dict()
    plan_path = ROOT / listing["plan_path"]
    return listing, plan_path, load_plan(plan_path), OUT_DIR / property_id / "multi"


def fit_pieces(pieces, generator, out_dir, say=print):
    """Every piece's raw model fitted and put in the catalog in place of its stock item.
    -> (catalog, the user's catalog items)"""
    catalog, mine_items = load_catalog(), []
    for p in pieces:
        yaw = (p.get("turn", 0) + FRONT_TURN_DEG.get(generator, 0.0)) % 360
        try:
            catalog, item = add_furniture_model(p["raw"], p["slot"], out_dir / "custom", catalog,
                                                width_m=p.get("width_m"), yaw_deg=yaw,
                                                name=f"Your {p['slot'].replace('_', ' ')}")
        except (KeyError, ValueError) as e:
            say(f"  {p['label']}: not used ({e})")
            continue
        mine_items.append(item)
        p["fitted"] = item.mesh            # the piece as it stands in the apartment (front = +z)
        say(f"  {p['label']} -> {item.id}: {item.width_m} x {item.depth_m} x {item.height_m} m")
    return catalog, mine_items


def reuse_layout(plan, old, catalog, prefs, say=print):
    """The last layout with today's catalog: every item stays where it was (with its piece's new size),
    'leave out' kinds are taken away and must-haves that are not there yet (a new photo) are fitted in."""
    known = {i.id: i for i in catalog.items}
    items = [it.model_copy(update={"width_m": c.width_m, "depth_m": c.depth_m, "height_m": c.height_m})
             for it in old.items for c in [known.get(it.catalog_id)] if c is not None and not c.is_a(prefs.exclude)]
    if len(items) < len(old.items):
        say(f"Took out {len(old.items) - len(items)} item(s) you asked to leave out")
    have = [known[i.catalog_id] for i in items]
    missing = [n for n in prefs.must_have if not any(c.is_a([n]) for c in have)]
    staging = old.model_copy(update={"items": items, "unplaced": missing})
    if missing:
        staging, placed = place_unplaced(plan, staging, catalog)
        say(f"Added to the layout: {', '.join(placed) or 'nothing'}")
    return staging


def finish(plan, plan_path, listing, staging, catalog, out_dir, say=print, save_rejected=True):
    """Validate, save and build the walkthrough. -> walkthrough path, or None if the validator rejects it."""
    result = validate_staging(plan, staging, catalog)
    say("Check: " + ("APPROVED" if result["approved"] else "REJECTED"))
    for check in result["checks"]:
        if not check["passed"]:
            say(f"  FAIL {check['name']}: {check['message']} {check['actual']}")
    if result["approved"] or save_rejected:
        save_staging(staging, out_dir / "staging.json")
    if not result["approved"]:
        return None
    (out_dir / "catalog.json").write_text(catalog.model_dump_json(indent=1), encoding="utf-8")
    started = time.time()
    html = build_walkthrough(plan_path, out_dir / "walkthrough.html", glb_path=out_dir / "architecture.glb",
                             listing=listing, staging=staging, catalog=catalog)
    say(f"Walkthrough built: {html.stat().st_size / 1e6:.1f} MB in {time.time() - started:.0f} s")
    return html


def place_pieces(property_id, pieces, generator, prefs=None, planner="rules", say=print, keep=None):
    """pieces: [{label, slot, raw, width_m, turn}] -> (walkthrough path or None, staging, catalog).
    prefs: the wishes from the form (density, must have, leave out, dining seats, style);
    planner: "rules" = the project's rules, "llm" = Gemini (Groq if busy) arranges, rules as fallback;
    keep: the last staging of this apartment: kept as it is where the changed pieces still fit."""
    prefs = prefs or DesignPreferences()
    listing, plan_path, plan, out_dir = open_listing(property_id)
    say(f"Plan: {listing['title'].strip()} ({plan.total_area_sqm:.0f} m2, {len(plan.rooms())} rooms)")

    catalog, mine_items = fit_pieces(pieces, generator, out_dir, say)
    mine = [i.id for i in mine_items]

    both = sorted(set(prefs.must_have) & set(prefs.exclude))
    if both:      # ticked as "must have" and "leave out": must have wins
        say(f"{both} was both 'must have' and 'leave out': kept it as must have")
    # your pieces always appear, and "leave out" never removes them
    prefs = prefs.model_copy(update={
        "must_have": prefs.must_have + [m for m in mine if m not in prefs.must_have],
        "exclude": [n for n in prefs.exclude if n not in both and not any(i.is_a([n]) for i in mine_items)]})
    say(f"Wishes: {prefs.model_dump(exclude_defaults=True) or 'none (defaults)'}")
    unknown = prefs.unknown_names(catalog.vocabulary())
    if unknown:
        say(f"  not catalog names, will be reported as unplaced: {unknown}")

    staging = None
    if keep is not None and keep.plan_id == plan.plan_id:
        staging = reuse_layout(plan, keep, catalog, prefs, say)
        if validate_staging(plan, staging, catalog)["approved"]:
            say("Kept the last layout (only the changed pieces were updated)")
        else:
            say("The changed pieces do not fit the last layout: arranging the apartment again")
            staging = None
    if staging is None:
        if planner == "llm":
            staging, report = llm_furnish(plan, prefs, catalog)
            say(f"Arranged by {report.planner}" + (f" ({report.rounds} round(s))" if report.rounds else ""))
            for w in report.warnings:
                say(f"  {w}")
            if report.summary:
                say(f"  model says: {report.summary}")
        else:
            staging = stage_plan(plan, catalog, preferences=prefs)
        if staging.unplaced:
            staging, rescued = place_unplaced(plan, staging, catalog)
            if rescued:
                say(f"Placed with extra rules: {rescued}")
    room_type = {r.id: r.type for r in plan.rooms()}
    say(f"Placed {len(staging.items)} items, {sum(i.catalog_id in mine for i in staging.items)} of them yours:")
    for rtype in sorted({room_type[i.room_id] for i in staging.items}):
        counts = Counter(i.catalog_id for i in staging.items if room_type[i.room_id] == rtype)
        say(f"  {rtype:8s} " + ", ".join((f"{n} x " if n > 1 else "") + (f"YOUR {k}" if k in mine else k)
                                          for k, n in sorted(counts.items())))
    if staging.unplaced:
        say(f"Did not fit: {staging.unplaced}")
    return finish(plan, plan_path, listing, staging, catalog, out_dir, say), staging, catalog


# ---------- small changes to a furnished apartment (no 3D server, no new layout) ----------
def edit_layout(property_id, staging, catalog, change, say=print):
    """One change to the furnished apartment, kept only if the validator still approves it.
    change(plan, staging, catalog) -> new staging (None = nothing to do). -> (walkthrough or None, staging)"""
    listing, plan_path, plan, out_dir = open_listing(property_id)
    if staging is None or catalog is None or staging.plan_id != plan.plan_id:
        say("Furnish this apartment first.")
        return None, staging
    new = change(plan, staging, catalog)
    if new is None:
        return None, staging
    html = finish(plan, plan_path, listing, new, catalog, out_dir, say, save_rejected=False)
    if html is None:
        say("Not changed: the apartment stays as it was.")
        return None, staging
    return html, new


def move_item(item_id, dx=0.0, dy=0.0, turn=0):
    """Move an item (meters on the plan: x right, y up) and/or turn it (degrees, counter-clockwise)."""
    def change(plan, staging, catalog):
        items = [i.model_copy(update={"x": round(i.x + dx, 3), "y": round(i.y + dy, 3),
                                      "rotation_deg": (i.rotation_deg + turn) % 360}) if i.id == item_id else i
                 for i in staging.items]
        return staging.model_copy(update={"items": items})
    return change


def remove_item(item_id):
    def change(plan, staging, catalog):
        return staging.model_copy(update={"items": [i for i in staging.items if i.id != item_id]})
    return change


def add_item(name, say=print):
    """Put one more catalog item (a kind or an id) where the rules find room for it."""
    def change(plan, staging, catalog):
        new, placed = place_unplaced(plan, staging.model_copy(update={"unplaced": [name]}), catalog)
        if not placed:
            say(f"No room found for {name}.")
            return None
        say(f"Added {name}.")
        return new.model_copy(update={"unplaced": staging.unplaced})
    return change


# %% 7. The app (stop it with Ctrl+C, or Interrupt in the interactive window)
# The app: add photos -> check the table -> furnish; then change it without starting over
import json
import math

import gradio as gr
import pandas as pd

from backend.schema.staging import Catalog, load_staging
from backend.services.llm_furnisher import detect_llm

OUT_DIR.mkdir(exist_ok=True)
gr.set_static_paths(paths=[OUT_DIR])          # lets the page load the walkthrough it builds
PHOTO_DIR = OUT_DIR / "_photos"               # every added photo is kept here, so a page reload keeps it
SESSION = OUT_DIR / "_session.json"           # the pieces table, brought back when the page is reloaded

LISTINGS = load_listings()
LISTING_CHOICES = [(f"{r.property_id} · {str(r.title).strip()[:55]} · {r.pf_area_sqm:.0f} m² · {r.pf_bedrooms} bed",
                    r.property_id) for r in LISTINGS.itertuples()]
KINDS = sorted({i.kind for i in load_catalog().items})
COLUMNS = ["photo", "what is it", "width (m)", "turn", "note"]
DEFAULT_TURN = 180     # every piece starts turned 180 degrees; change it per piece below
GENERATOR_CHOICES = [("Diffusion server (Hunyuan3D on Kaggle/Colab, coloured)", "colab"),
                     ("TRELLIS.2 on Hugging Face (daily quota)", "trellis")]
AUTO = "Auto"
PLANNERS = [("Rules", "rules"), ("AI designs it (Gemini, Groq if Gemini is busy)", "llm")]
PLANNER_MODEL = detect_llm()
EMPTY_VIEW = "<div style='padding:40px;text-align:center;color:#888'>The furnished apartment appears here.</div>"
STEP_M = 0.25          # one press of an arrow moves the item this far


def _path(f):
    return f if isinstance(f, str) else getattr(f, "name", None) or f["path"]


def _number(value, default=None):
    try:
        value = float(value)
        return default if math.isnan(value) else value
    except (TypeError, ValueError):
        return default


def _table(table):
    return table if isinstance(table, pd.DataFrame) else pd.DataFrame(table, columns=COLUMNS)


def _names(paths):
    return [Path(p).name for p in paths or []]


def _pick(paths, value=None):
    names = _names(paths)
    return gr.update(choices=names, value=value if value in names else (names[0] if names else None))


def _frame(html):
    src = f"/gradio_api/file={Path(html).resolve().as_posix()}?t={int(time.time())}"
    return (f'<iframe src="{src}" title="3D walkthrough" allow="fullscreen" allowfullscreen '
            f'style="width:100%;height:680px;border:0;border-radius:8px"></iframe>')


def _keep_photo(src, taken):
    """Copy an uploaded photo next to the others (its own folder, named by its content).
    -> its new path, or None if that photo is already in the list."""
    data = Path(src).read_bytes()
    digest = hashlib.sha1(data).hexdigest()[:12]
    if any(Path(p).parent.name == digest for p in taken):
        return None
    name, names, n = Path(src).name, set(_names(taken)), 2
    while name in names:                      # two different photos called the same
        name = f"{Path(src).stem} ({n}){Path(src).suffix}"
        n += 1
    dst = PHOTO_DIR / digest / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return str(dst)


def _save_session(paths, table, property_id, made=None):
    old = json.loads(SESSION.read_text(encoding="utf-8")) if SESSION.exists() else {}
    rows = json.loads(_table(table).to_json(orient="split"))["data"] if paths else []
    SESSION.write_text(json.dumps({"paths": list(paths or []), "rows": rows, "property": property_id,
                                   "made": old.get("made", []) if made is None else made,
                                   "visit": old.get("visit"), "since": old.get("since")}), encoding="utf-8")


def _read(path, catalog):
    seen = read_photo(path, catalog)
    return [Path(path).name, seen["kind"], seen["width_m"], DEFAULT_TURN, seen["note"]]


def item_choices(property_id, staging, catalog, value=None):
    """The items standing in the apartment, as (room · name · id, id), for the item editor."""
    if staging is None or catalog is None:
        return gr.update(choices=[], value=None)
    rooms = {r.id: r.type for r in open_listing(property_id)[2].rooms()}
    names = {i.id: i.name for i in catalog.items}
    choices = sorted((f"{rooms.get(i.room_id, i.room_id)} · {names.get(i.catalog_id, i.catalog_id)} · {i.id}", i.id)
                     for i in staging.items)
    return gr.update(choices=choices, value=value if value in {v for _, v in choices} else None)


# ---------- the pieces list: add, remove, replace (the 3D models already made are kept) ----------
def add_photos(files, paths, table, property_id):
    """Adds the uploaded photos to the list; the pieces already there stay as they are."""
    paths, table = list(paths or []), _table(table) if paths else pd.DataFrame(columns=COLUMNS)
    if not files:
        return table, "Choose one or more photos first (one piece per photo).", paths, _pick(paths), None
    catalog, rows, new, same = load_catalog(), [], [], 0
    for f in files:
        kept = _keep_photo(_path(f), paths + new)
        if kept is None:
            same += 1
            continue
        rows.append(_read(kept, catalog))
        new.append(kept)
    if rows:
        added = pd.DataFrame(rows, columns=COLUMNS)
        table = added if table.empty else pd.concat([table, added], ignore_index=True)
    paths += new
    msg = f"Added {len(new)} photo(s); {len(paths)} in the list now."
    if same:
        msg += f" {same} were already in the list."
    msg += f"\nCheck 'what is it' (one of: {', '.join(KINDS)}) and the width, then Furnish."
    missing = sum(not str(r or "").strip() for r in table["what is it"])
    if missing:
        msg += f"\n{missing} photo(s) still need 'what is it'."
    _save_session(paths, table, property_id)
    return table, msg, paths, _pick(paths, Path(new[-1]).name if new else None), None


def remove_piece(label, paths, table, property_id):
    """Takes a photo out of the list. After Furnish its place goes back to the catalog piece."""
    paths, table = list(paths or []), _table(table)
    if label not in _names(paths):
        return table, "Pick the piece to take out first.", paths, _pick(paths)
    i = _names(paths).index(label)
    paths.pop(i)
    table = table.drop(index=table.index[i]).reset_index(drop=True)
    _save_session(paths, table, property_id)
    return (table, f"Took out {label}. Press Furnish: the catalog piece comes back in its place "
                   f"(to have nothing there, remove the item below).", paths, _pick(paths))


def replace_piece(label, file, paths, table, property_id):
    """Puts a new photo in place of one in the list (same row: its kind and width are read again)."""
    paths, table = list(paths or []), _table(table)
    if label not in _names(paths) or not file:
        return table, "Pick the piece and choose its new photo first.", paths, _pick(paths, label), None
    i = _names(paths).index(label)
    kept = _keep_photo(_path(file), paths[:i] + paths[i + 1:] + [paths[i]])
    if kept is None:
        return table, "That photo is already in the list.", paths, _pick(paths, label), None
    paths[i] = kept
    table = table.copy()
    table.iloc[i] = _read(kept, load_catalog())
    _save_session(paths, table, property_id)
    return (table, f"{label} replaced by {Path(kept).name}. Check its row, then Furnish "
                   f"(only this photo goes to the 3D server).", paths, _pick(paths, Path(kept).name), None)


def reread_piece(label, paths, table, property_id):
    """Asks the vision model about that photo again (its row is filled in again)."""
    paths, table = list(paths or []), _table(table).copy()
    if label not in _names(paths):
        return table, "Pick the piece first.", paths, _pick(paths)
    i = _names(paths).index(label)
    table.iloc[i] = _read(paths[i], load_catalog())
    _save_session(paths, table, property_id)
    return table, f"Read {label} again: {table.iloc[i]['what is it'] or 'still unknown'}.", paths, _pick(paths, label)


def start_over():
    SESSION.unlink(missing_ok=True)
    return (pd.DataFrame(columns=COLUMNS), "Cleared. Add your photos.", [], _pick([]), [], None, None,
            EMPTY_VIEW, None, gr.update(choices=[], value=None))


# ---------- furnish ----------
def furnish(paths, table, property_id, density, must_have, exclude, dining_seats, style_brief, planner, generator,
            keep_layout, last_staging):
    """Streams (report, view, download, pieces, piece choices, staging, catalog, item choices) while it works."""
    lines = []
    say = lines.append
    keep = gr.update()

    def out(view=keep, download=keep, pieces=keep, staging=keep, catalog=keep, items=keep):
        return "\n".join(lines), view, download, pieces, keep, staging, catalog, items

    if not paths:
        say("Add photos first.")
        yield out()
        return
    table = _table(table)
    pieces = []
    for path, (_, row) in zip(paths, table.iterrows()):
        turn = int(_number(row["turn"], DEFAULT_TURN)) % 360
        pieces.append({"label": Path(path).name, "photo": path, "kind": str(row["what is it"] or "").strip(),
                       "width_m": _number(row["width (m)"]), "turn": turn if turn in (0, 90, 180, 270) else DEFAULT_TURN})
    prefs = DesignPreferences.from_loose({
        "density": density, "must_have": must_have or [], "exclude": exclude or [],
        "dining_seats": None if dining_seats == AUTO else int(dining_seats),
        "style_brief": (style_brief or "").strip() or None})
    say(f"{len(pieces)} photo(s), 3D with {generator}, arranged by {planner}"
        + (", keeping the last layout where it still fits" if keep_layout and last_staging else ""))
    pieces = assign_slots(pieces, load_catalog(), say)
    if not pieces:
        say("Nothing to place.")
        yield out()
        return
    ready = []
    for n, p in enumerate(pieces, 1):
        say(f"{n}/{len(pieces)} {p['label']} ({p['slot']}): making the 3D model...")
        yield out()
        try:
            p["raw"] = raw_model(p["photo"], generator, say)
            ready.append(p)
        except Exception as e:          # server down, quota used up, bad photo ...
            say(f"     failed: {type(e).__name__}: {str(e)[:160]}")
        yield out()
    if not ready:
        say("No 3D model could be made.")
        yield out()
        return
    say("Placing everything in the apartment...")
    yield out()
    try:
        html, staging, catalog = place_pieces(property_id, ready, generator, prefs, planner, say,
                                              keep=last_staging if keep_layout else None)
    except Exception as e:
        say(f"error: {type(e).__name__}: {e}")
        yield out()
        return
    made = [{"label": p["label"], "slot": p["slot"], "turn": p["turn"], "fitted": p["fitted"]}
            for p in ready if p.get("fitted")]
    _save_session(paths, table, property_id, made)
    if html is None:
        say("\nThe last walkthrough (if any) stays on screen.")
        yield out(pieces=made)
        return
    say("\nNow you can change it without starting over: add or replace photos and Furnish again "
        "(only new photos go to the 3D server), or move / turn / remove / add single items below the view.")
    yield out(_frame(html), str(html), made, staging, catalog, item_choices(property_id, staging, catalog))


# ---------- single items in the furnished apartment ----------
def change_item(change_for):
    """An editor button: change_for(item_id, say) -> change, applied with edit_layout."""
    def run(property_id, item_id, staging, catalog):
        lines = []
        if not item_id and change_for is not None:
            return "Pick an item first.", gr.update(), gr.update(), staging, gr.update()
        html, staging = edit_layout(property_id, staging, catalog, change_for(item_id, lines.append), lines.append)
        if html is None:
            return "\n".join(lines), gr.update(), gr.update(), staging, gr.update()
        # the item stays picked, so an arrow can be pressed again
        return "\n".join(lines), _frame(html), str(html), staging, item_choices(property_id, staging, catalog, item_id)
    return run


def add_catalog_item(property_id, name, staging, catalog):
    if not name:
        return "Pick what to add first.", gr.update(), gr.update(), staging, gr.update()
    return change_item(lambda _, say: add_item(name, say))(property_id, name, staging, catalog)


# ---------- the piece viewer ----------
def show_piece(label, made, table, paths):
    """The chosen piece: its turn from the table, and its 3D model once Furnish has made it
    (as it stands in the apartment: the side facing you at the start is its front)."""
    table = _table(table)
    row = next((i for i, p in enumerate(paths or []) if Path(p).name == label), None)
    turn = int(_number(table.iloc[row]["turn"], DEFAULT_TURN)) if row is not None and row < len(table) else DEFAULT_TURN
    turn = str(turn if turn in (0, 90, 180, 270) else DEFAULT_TURN)
    piece = next((p for p in made or [] if p["label"] == label), None)
    if piece is None:
        return None, turn, f"**{label}**: its 3D model appears here after Furnish." if label else ""
    return (piece["fitted"], turn,
            f"**{label}** is your `{piece['slot']}`. Drag to look around; the side facing you at the start is its front.")


def set_turn(label, turn, table, paths):
    """Write the chosen turn into the table row of that photo."""
    table = _table(table).copy()
    for i, path in enumerate(paths or []):
        if Path(path).name == label and i < len(table):
            table.iloc[i, COLUMNS.index("turn")] = int(turn)
    return table


def restore(request: gr.Request):
    """After a page reload: the pieces list and the last furnished apartment come back.
    A link from the app (?property_id=PROP_1002&visit=...) opens that apartment empty, ready for the
    customer's photos; going back to the app and returning in the same visit brings the work back."""
    asked = request.query_params.get("property_id") if request else None
    asked = asked if asked in set(LISTINGS["property_id"]) else None
    visit = request.query_params.get("visit") if request else None
    if asked:
        s = json.loads(SESSION.read_text(encoding="utf-8")) if SESSION.exists() else {}
        if not (visit and s.get("visit") == visit and s.get("property") == asked):
            SESSION.write_text(json.dumps({"paths": [], "rows": [], "property": asked, "made": [], "visit": visit,
                                           "since": time.time()}), encoding="utf-8")
            return ([], pd.DataFrame(columns=COLUMNS), asked, _pick([]), [], None, None, EMPTY_VIEW, None,
                    gr.update(choices=[], value=None),
                    "Add a photo of each piece of furniture you have, then press 2. Furnish the apartment.")
    nothing = tuple(gr.update() for _ in range(10)) + (gr.update(),)
    if not SESSION.exists():
        if asked:
            return nothing[:2] + (asked,) + nothing[3:]
        return nothing
    s = json.loads(SESSION.read_text(encoding="utf-8"))
    rows = [(p, r) for p, r in zip(s["paths"], s["rows"]) if Path(p).exists()]
    paths = [p for p, _ in rows]
    table = pd.DataFrame([r for _, r in rows], columns=COLUMNS)
    s["property"] = asked or s["property"]
    out_dir = OUT_DIR / s["property"] / "multi"
    staging = catalog = None
    if (out_dir / "staging.json").exists() and (out_dir / "catalog.json").exists():
        staging = load_staging(out_dir / "staging.json")
        catalog = Catalog.model_validate_json((out_dir / "catalog.json").read_text(encoding="utf-8"))
    html = out_dir / "walkthrough.html"
    # الشقة المفروشة بترجع بس لو اتفرشت في الزيارة دي (مش فرش قديم من قبلها)
    furnished_now = staging is not None and (out_dir / "staging.json").stat().st_mtime > s.get("since", 0)
    if not furnished_now:
        staging = catalog = None        # ولا محرر القطع ولا "Keep the last layout" يشتغلوا على الفرش القديم
    shown = furnished_now and html.exists()
    return (paths, table, s["property"], _pick(paths), s.get("made", []), staging, catalog,
            _frame(html) if shown else EMPTY_VIEW, str(html) if shown else None,
            item_choices(s["property"], staging, catalog),
            f"Brought back {len(paths)} photo(s)" + (" and the last furnished apartment." if shown else "."))


with gr.Blocks(title="Smart Semsar - furnish with your own furniture") as demo:
    gr.Markdown("# Smart Semsar — furnish the whole apartment with your own furniture\n"
                "Add a photo of each piece you have (one piece per photo), check the table, and walk through "
                "the apartment furnished with them. Pieces you have no photo of come from the catalog. "
                "Afterwards add, take out or replace pieces and move things around without starting over.")
    paths = gr.State([])
    made = gr.State([])
    staging_st = gr.State(None)      # the furnished apartment now on screen
    catalog_st = gr.State(None)      # the catalog it was made with (your pieces in it)
    with gr.Row():
        with gr.Column(scale=1, min_width=360):
            listing = gr.Dropdown(LISTING_CHOICES, value="PROP_1002", label="Apartment")
            photos = gr.File(file_count="multiple", file_types=["image"], label="Your furniture photos")
            with gr.Row():
                read_btn = gr.Button("1. Add these photos")
                clear_btn = gr.Button("Start over", variant="stop", size="sm")
            table = gr.Dataframe(headers=COLUMNS, datatype=["str", "str", "number", "number", "str"],
                                 col_count=(len(COLUMNS), "fixed"), interactive=True, wrap=True,
                                 label="Your pieces (edit 'what is it', width in meters, turn 0/90/180/270)")
            with gr.Accordion("Change a piece (take it out, give it a new photo, turn it)", open=False):
                piece = gr.Dropdown([], label="Piece", info="Filled when photos are added")
                with gr.Row():
                    remove_btn = gr.Button("Take it out", size="sm")
                    reread_btn = gr.Button("Read it again", size="sm")
                    replace_file = gr.File(file_types=["image"], label="New photo for it", height=90)
                    replace_btn = gr.Button("Replace with this photo", size="sm")
                turn = gr.Radio(["0", "90", "180", "270"], value=str(DEFAULT_TURN), label="Turn it (if it faces sideways)")
                piece_note = gr.Markdown()
                piece_view = gr.Model3D(label="Your piece (drag to rotate)", height=300,
                                        clear_color=(0.15, 0.15, 0.15, 1.0))
            density = gr.Radio(["minimal", "normal", "full"], value="normal", label="How much furniture")
            must_have = gr.CheckboxGroup(KINDS, label="Must have")
            exclude = gr.CheckboxGroup(KINDS, label="Leave out")
            dining_seats = gr.Radio([AUTO, "4", "6"], value=AUTO, label="Dining seats")
            style_brief = gr.Textbox(label="Style description (used by the Gemini planner)",
                                     placeholder="e.g. calm modern, light wood, grey fabric, a reading corner")
            planner = gr.Radio(PLANNERS, value="rules", label="Who arranges the furniture")
            generator = gr.Radio(GENERATOR_CHOICES, value=default_generator(), label="Photo to 3D with")
            keep_box = gr.Checkbox(True, label="Keep the last layout (only update what changed)",
                                      info="Off = arrange the whole apartment again")
            go = gr.Button("2. Furnish the apartment", variant="primary")
        with gr.Column(scale=3):
            view = gr.HTML(EMPTY_VIEW)
            with gr.Group():
                gr.Markdown("**Edit the furnished apartment** (each change is checked; one that breaks the rules is not kept)")
                with gr.Row():
                    item = gr.Dropdown([], label="Item in the apartment", scale=3)
                    turn_btn = gr.Button("⟲ Turn 90°", size="sm", scale=1)
                    delete_btn = gr.Button("Remove from the apartment", variant="stop", size="sm", scale=1)
                with gr.Row():
                    left_btn = gr.Button("← left", size="sm")
                    up_btn = gr.Button("↑ up", size="sm")
                    down_btn = gr.Button("↓ down", size="sm")
                    right_btn = gr.Button("→ right", size="sm")
                gr.Markdown(f"<small>Arrows move it {STEP_M} m as on the floor plan (up = the plan's top).</small>")
                with gr.Row():
                    add_kind = gr.Dropdown(KINDS, label="Add a catalog piece", scale=3)
                    add_btn = gr.Button("Add it", size="sm", scale=1)
            report = gr.Textbox(label="What happened", lines=14, max_lines=30)
            download = gr.File(label="Walkthrough page (opens offline in any browser)")
    gr.Markdown(f"Keys found: GEMINI_API_KEY {'yes' if setting('GEMINI_API_KEY') else 'no'} · "
                f"GROQ_API_KEY {'yes' if setting('GROQ_API_KEY') else 'no'} · "
                f"planner model: {PLANNER_MODEL.name if PLANNER_MODEL else 'none (rules only)'}")

    read_btn.click(add_photos, [photos, paths, table, listing], [table, report, paths, piece, photos])
    clear_btn.click(start_over, None, [table, report, paths, piece, made, staging_st, catalog_st, view, download, item])
    remove_btn.click(remove_piece, [piece, paths, table, listing], [table, report, paths, piece])
    reread_btn.click(reread_piece, [piece, paths, table, listing], [table, report, paths, piece])
    replace_btn.click(replace_piece, [piece, replace_file, paths, table, listing],
                      [table, report, paths, piece, replace_file])
    go.click(furnish, [paths, table, listing, density, must_have, exclude, dining_seats, style_brief, planner,
                       generator, keep_box, staging_st],
             [report, view, download, made, piece, staging_st, catalog_st, item])
    piece.change(show_piece, [piece, made, table, paths], [piece_view, turn, piece_note])
    turn.input(set_turn, [piece, turn, table, paths], [table])
    edit_outputs = [report, view, download, staging_st, item]
    for btn, change_for in ((left_btn, lambda i, say: move_item(i, dx=-STEP_M)),
                            (right_btn, lambda i, say: move_item(i, dx=STEP_M)),
                            (up_btn, lambda i, say: move_item(i, dy=STEP_M)),
                            (down_btn, lambda i, say: move_item(i, dy=-STEP_M)),
                            (turn_btn, lambda i, say: move_item(i, turn=90)),
                            (delete_btn, lambda i, say: remove_item(i))):
        btn.click(change_item(change_for), [listing, item, staging_st, catalog_st], edit_outputs)
    add_btn.click(add_catalog_item, [listing, add_kind, staging_st, catalog_st], edit_outputs)
    demo.load(restore, None, [paths, table, listing, piece, made, staging_st, catalog_st, view, download, item, report])

demo.queue().launch(share=SHARE, inbrowser=not FROM_APP, server_port=PORT, height=1400)

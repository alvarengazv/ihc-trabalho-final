import hashlib
import json
import random
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("configs") / "v1.json"
CALIBRATION = ("C1", "C2")


def calibration_only(task):
    if task not in CALIBRATION:
        raise ValueError("Pilot runs accept only calibration tasks C1 and C2.")


def sample(profile, seed, disabled=(), reference_zoom=None):
    source = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    params = {**source["defaults"], **source["profiles"][profile]}
    # Independent parameter streams keep k identical between paired P/C seeds.
    for name in ("k", "z", "s"):
        rng = random.Random(f"{seed}/{name}")
        if name == "k" and params[name]:
            params[name] = rng.choice(params[name])
        if name == "z":
            params[name] = rng.uniform(*params[name])
        if name == "s" and params[name] == "mista":
            params[name] = "linear" if rng.randrange(11) < 9 else "salteada"
    if reference_zoom is not None:
        if profile != "R" or not 1 <= reference_zoom <= 7:
            raise ValueError("Reference zoom must be between 1 and 7 on R.")
        params["z"] = reference_zoom
    unknown = set(disabled) - set(source["defaults"]["mechanisms"])
    if unknown:
        raise ValueError(f"Unknown mechanisms: {unknown}")
    params["mechanisms"] = [m for m in params["mechanisms"] if m not in disabled]
    params.update(profile=profile, version=source["version"], seed=seed)
    return params


def digest(data):
    encoded = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


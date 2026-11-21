"""Recompute a run from its event log, independent of the original policy."""
import argparse
import json
from pathlib import Path

from . import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path, nargs="+")
    for path in parser.parse_args().logs:
        with path.open(encoding="utf-8-sig") as stream:
            log = json.load(stream)
        result = evaluate(log)
        print(json.dumps({"file": path.name, **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

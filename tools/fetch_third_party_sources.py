"""Fetch the exact release sources; verify the recorded SHA-256 before keeping them."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    records = json.loads((ROOT / "licenses/sources.json").read_text())
    for record in records:
        path = args.destination / record["file"]
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]:
            print(f"Verified: {path.name}")
            continue
        temporary = path.with_suffix(path.suffix + ".part")
        request = urllib.request.Request(record["url"], headers={"User-Agent": "ContourNote-source-fetch"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != record["sha256"]:
                raise RuntimeError(f"Source checksum mismatch: {path.name}")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Downloaded and verified: {path.name}")


if __name__ == "__main__":
    main()

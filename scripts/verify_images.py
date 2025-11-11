import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Verify generated image assets by checking MIME types and decodeability.")
    parser.add_argument("roots", nargs="+", help="Directories containing images to verify")
    parser.add_argument("--min-bytes", type=int, default=4096, help="Minimum allowed file size")
    parser.add_argument("--decode", action="store_true", help="Attempt to decode each image with sips")
    parser.add_argument("--sample", type=int, default=0, help="Report detailed probes for the first N files that pass")
    return parser.parse_args()


def mime_type(path: Path) -> str:
    result = subprocess.run(
        ["file", "-b", "--mime-type", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.decode().strip()


def decode_with_sips(path: Path) -> None:
    if shutil.which("sips") is None:
        raise RuntimeError("sips binary not available")
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "probe.png"
        subprocess.run(
            ["sips", "-s", "format", "png", str(path), "--out", str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )


def check_path(path: Path, min_bytes: int, decode: bool):
    errors = []
    meta = {"size": None, "mime": None}
    if not path.exists():
        errors.append("missing")
        return errors, meta
    size = path.stat().st_size
    meta["size"] = size
    if size < min_bytes:
        errors.append(f"too-small({size})")
    try:
        mime = mime_type(path)
        meta["mime"] = mime
    except subprocess.CalledProcessError as exc:
        errors.append(f"mime-error({exc})")
        mime = None
    if mime:
        if not mime.startswith("image/"):
            errors.append(f"mime={mime}")
    if decode:
        try:
            decode_with_sips(path)
        except Exception as exc:
            errors.append(f"decode-error({exc})")
    return errors, meta


def main():
    args = parse_args()
    failures = []
    samples = []
    for root in args.roots:
        for file_path in Path(root).rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"}:
                issues, meta = check_path(file_path, args.min_bytes, args.decode)
                if issues:
                    failures.append((file_path, issues))
                elif len(samples) < args.sample:
                    samples.append((file_path, meta))

    if failures:
        print("[WARN] Verification failures detected:")
        for idx, (path, issues) in enumerate(failures, start=1):
            joined = ", ".join(issues)
            print(f"  {idx:03d}: {path} -> {joined}")
        sys.exit(1)

    print("[OK] All files passed verification.")
    if samples:
        print("[INFO] Sample probes:")
        for path, meta in samples:
            size = meta.get("size")
            mime = meta.get("mime")
            size_text = f"{size} bytes" if size is not None else "unknown size"
            print(f"  - {path}: {size_text}, mime={mime}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(2)


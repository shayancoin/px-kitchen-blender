import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PNG_ROOT_DEFAULT = ROOT / "web_kitchen_bundles_png"
WEBP_ROOT_DEFAULT = ROOT / "web_kitchen_bundles"
JPEG_ROOT_DEFAULT = ROOT / "web_kitchen_bundles_jpeg"
PNG_MANIFEST = "web_kitchen_manifest.json"


def require_binary(binary: str) -> None:
    if shutil.which(binary) is None:
        raise RuntimeError(f"Required binary '{binary}' not found in PATH")


def parse_args():
    parser = argparse.ArgumentParser(description="Transcode PNG renders to WebP and JPEG outputs.")
    parser.add_argument("--png-root", default=str(PNG_ROOT_DEFAULT), help="Directory containing PNG renders and manifest")
    parser.add_argument("--webp-root", default=str(WEBP_ROOT_DEFAULT), help="Destination root for WebP outputs")
    parser.add_argument("--jpeg-root", default=str(JPEG_ROOT_DEFAULT), help="Destination root for JPEG outputs")
    parser.add_argument("--webp-quality", type=int, default=90, help="Quality for cwebp (0-100)")
    parser.add_argument("--jpeg-quality", type=int, default=2, help="ffmpeg -q:v quality value (lower is better)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip conversion if destination already exists")
    return parser.parse_args()


def run_cmd(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def convert_png(png_path: Path, webp_path: Path, jpeg_path: Path, args) -> None:
    webp_path.parent.mkdir(parents=True, exist_ok=True)
    jpeg_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.skip_existing or not webp_path.exists():
        run_cmd(
            [
                "cwebp",
                "-q",
                str(args.webp_quality),
                "-m",
                "6",
                "-mt",
                "-metadata",
                "none",
                str(png_path),
                "-o",
                str(webp_path),
            ]
        )

    if not args.skip_existing or not jpeg_path.exists():
        run_cmd(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(png_path),
                "-vf",
                "format=yuv420p",
                "-q:v",
                str(args.jpeg_quality),
                "-pix_fmt",
                "yuvj420p",
                str(jpeg_path),
            ]
        )


def rewrite_manifest(manifest: dict, target_root: Path, extension: str) -> dict:
    updated = json.loads(json.dumps(manifest))
    updated["format"] = extension.upper()
    for bundle in updated.get("bundles", []):
        for file_entry in bundle.get("files", []):
            rel_path = Path(file_entry["rel"])
            file_entry["rel"] = rel_path.with_suffix(f".{extension.lower()}").as_posix()
    manifest_path = target_root / PNG_MANIFEST
    target_root.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(updated, fh, indent=2)
    return updated


def main():
    args = parse_args()

    require_binary("cwebp")
    require_binary("ffmpeg")

    png_root = Path(args.png_root).resolve()
    webp_root = Path(args.webp_root).resolve()
    jpeg_root = Path(args.jpeg_root).resolve()

    manifest_path = png_root / PNG_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(f"PNG manifest not found at {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    png_files = sorted(png_root.rglob("*.png"))
    if not png_files:
        raise RuntimeError(f"No PNG files found under {png_root}")

    for png_file in png_files:
        rel = png_file.relative_to(png_root)
        webp_path = webp_root / rel.with_suffix(".webp")
        jpeg_path = jpeg_root / rel.with_suffix(".jpg")
        convert_png(png_file, webp_path, jpeg_path, args)

    rewrite_manifest(manifest, webp_root, "webp")
    rewrite_manifest(manifest, jpeg_root, "jpg")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)


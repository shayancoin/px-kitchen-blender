import subprocess
from pathlib import Path

SRC_ROOT = Path('web_kitchen_bundles')
DST_ROOT = Path('web_kitchen_bundles_jpeg')

for webp_path in SRC_ROOT.rglob('*.webp'):
    rel = webp_path.relative_to(SRC_ROOT)
    dst_path = DST_ROOT / rel.with_suffix('.jpg')
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(webp_path),
        '-qscale:v', '2',
        '-frames:v', '1',
        str(dst_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

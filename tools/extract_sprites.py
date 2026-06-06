"""Extract Clawdmeter sprites from the firmware C header into PNG frames.

Reads firmware/src/splash_animations.h (cached at assets/_splash_animations.h),
decodes the RGB565 palette + 20x20 frame indices, writes one PNG per frame at
assets/sprites/<slug>/<NN>.png plus a manifest.json describing the firmware's
rate-group mapping.

The PNGs stay 20x20 — runtime scales them with nearest-neighbor so they keep
the pixel-art look at any window size.

Requires Pillow (build-time only; not bundled into the .exe).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "assets" / "_splash_animations.h"
OUT_DIR = ROOT / "assets" / "sprites"

# Firmware (splash.cpp): rate-group → animations played in that group.
FIRMWARE_GROUPS = {
    0: ("idle", ["expression sleep", "idle breathe", "idle blink", "expression wink"]),
    1: ("normal", ["idle look around", "work think", "work coding"]),
    2: ("active", ["dance sway", "expression surprise", "dance bounce"]),
    3: ("heavy", ["dance bounce dj", "dance sway dj", "dance djmix"]),
}


def rgb565_to_rgb888(c: int) -> tuple[int, int, int]:
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return (
        (r << 3) | (r >> 2),
        (g << 2) | (g >> 4),
        (b << 3) | (b >> 2),
    )


_INT = re.compile(r"0[xX][0-9A-Fa-f]+|\d+")


def parse_int_list(text: str) -> list[int]:
    return [int(m.group(0), 0) for m in _INT.finditer(text)]


def slug(name: str) -> str:
    return name.replace(" ", "_")


def parse_anims_table(src: str) -> list[dict]:
    """Return rows from splash_anims[] as dicts."""
    block = re.search(r"splash_anims\[SPLASH_ANIM_COUNT\]\s*=\s*\{(.*?)\};", src, re.S)
    if not block:
        raise SystemExit("Could not find splash_anims[] table")
    rows = re.findall(
        r'\{\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*\}',
        block.group(1),
    )
    out = []
    for name, category, fc, pal, frm, hld in rows:
        prefix = pal[: -len("_palette")]
        out.append({
            "name": name,
            "category": category,
            "frame_count": int(fc),
            "prefix": prefix,
        })
    return out


def parse_palette(src: str, prefix: str) -> list[int]:
    m = re.search(rf"{re.escape(prefix)}_palette\[10\]\s*=\s*\{{([^}}]+)\}}", src)
    if not m:
        raise SystemExit(f"palette not found for {prefix}")
    vals = parse_int_list(m.group(1))
    if len(vals) != 10:
        raise SystemExit(f"palette for {prefix} has {len(vals)} entries, expected 10")
    return vals


def parse_holds(src: str, prefix: str, expected: int) -> list[int]:
    m = re.search(rf"{re.escape(prefix)}_holds\[\d+\]\s*=\s*\{{([^}}]+)\}}", src)
    if not m:
        raise SystemExit(f"holds not found for {prefix}")
    vals = parse_int_list(m.group(1))
    if len(vals) != expected:
        raise SystemExit(f"holds for {prefix}: {len(vals)} vs frame_count {expected}")
    return vals


def parse_frames(src: str, prefix: str, expected: int) -> list[list[int]]:
    """Find the {prefix}_frames[N][400] block and split into N inner cell lists."""
    head = re.search(rf"{re.escape(prefix)}_frames\[\d+\]\[400\]\s*=\s*\{{", src)
    if not head:
        raise SystemExit(f"frames not found for {prefix}")
    start = head.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    body = src[start:i - 1]
    inner = re.findall(r"\{([^{}]+)\}", body)
    if len(inner) != expected:
        raise SystemExit(f"frames for {prefix}: parsed {len(inner)}, expected {expected}")
    frames = []
    for chunk in inner:
        vals = parse_int_list(chunk)
        if len(vals) != 400:
            raise SystemExit(f"frame for {prefix} has {len(vals)} cells, expected 400")
        frames.append(vals)
    return frames


def render_frame(cells: list[int], palette_rgb565: list[int]) -> Image.Image:
    rgb = [rgb565_to_rgb888(c) for c in palette_rgb565]
    img = Image.new("RGBA", (20, 20))
    px = img.load()
    for i, code in enumerate(cells):
        gx, gy = i % 20, i // 20
        if code == 0:
            px[gx, gy] = (0, 0, 0, 0)
        else:
            r, g, b = rgb[code]
            px[gx, gy] = (r, g, b, 255)
    return img


def main() -> None:
    if not HEADER.exists():
        raise SystemExit(f"Missing header: {HEADER}\nRun the downloader first.")
    src = HEADER.read_text(encoding="utf-8")

    rows = parse_anims_table(src)
    print(f"Found {len(rows)} animations")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_entries: dict[str, dict] = {}
    for r in rows:
        palette = parse_palette(src, r["prefix"])
        holds = parse_holds(src, r["prefix"], r["frame_count"])
        frames = parse_frames(src, r["prefix"], r["frame_count"])

        anim_slug = slug(r["name"])
        anim_dir = OUT_DIR / anim_slug
        anim_dir.mkdir(parents=True, exist_ok=True)

        frame_files = []
        for idx, cells in enumerate(frames):
            img = render_frame(cells, palette)
            fp = anim_dir / f"{idx:02d}.png"
            img.save(fp, "PNG")
            frame_files.append({"file": f"{anim_slug}/{fp.name}", "hold_ms": holds[idx]})

        manifest_entries[r["name"]] = {
            "slug": anim_slug,
            "category": r["category"],
            "frames": frame_files,
        }
        print(f"  {r['name']:<24} {r['frame_count']:>3} frames  -> {anim_dir.name}/")

    name_to_group: dict[str, int] = {}
    groups = []
    for gid, (gname, names) in FIRMWARE_GROUPS.items():
        members = [n for n in names if n in manifest_entries]
        for n in members:
            name_to_group[n] = gid
        groups.append({"id": gid, "name": gname, "animations": members})

    manifest = {
        "source": "https://github.com/HermannBjorgvin/Clawdmeter (firmware/src/splash_animations.h)",
        "art_credit": "https://claudepix.vercel.app",
        "tile": 20,
        "animations": manifest_entries,
        "groups": groups,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()

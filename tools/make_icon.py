"""Build assets/icon.ico (multi-size) and assets/icon.png from the idle-breathe
sprite. The icon is what Windows Explorer/taskbar/title-bar show.

Frame 00 of idle_breathe is the "neutral standing" pose — a good app face.
We upscale 20x20 with nearest-neighbor and pad transparently so the sprite
sits centered with breathing room (otherwise it touches the icon edges).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "sprites" / "idle_breathe" / "00.png"
OUT_PNG = ROOT / "assets" / "icon.png"
OUT_ICO = ROOT / "assets" / "icon.ico"

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PAD_PX = 1  # 1px transparent margin after cropping to non-transparent bbox


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing source frame: {SRC}\nRun tools/extract_sprites.py first.")
    base = Image.open(SRC).convert("RGBA")

    # Crop to the actual sprite bounding box so the creature fills the icon,
    # then put it back on a square canvas (sides = max dim + margin).
    bbox = base.getbbox()
    if not bbox:
        raise SystemExit("Source frame is fully transparent")
    cropped = base.crop(bbox)
    side = max(cropped.size) + 2 * PAD_PX
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    cx = (side - cropped.width) // 2
    cy = (side - cropped.height) // 2
    canvas.paste(cropped, (cx, cy), cropped)

    images = []
    for size in ICO_SIZES:
        scaled = canvas.resize((size, size), Image.NEAREST)
        images.append(scaled)

    largest = canvas.resize((512, 512), Image.NEAREST)
    largest.save(OUT_PNG, "PNG")

    images[0].save(OUT_ICO, format="ICO", sizes=[(im.width, im.height) for im in images])

    print(f"Wrote {OUT_PNG} ({largest.size})")
    print(f"Wrote {OUT_ICO} sizes={ICO_SIZES}")


if __name__ == "__main__":
    main()

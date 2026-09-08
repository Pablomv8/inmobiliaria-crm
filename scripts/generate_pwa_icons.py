from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "static" / "pwa"
BRAND_MARK = ROOT / "static" / "branding" / "sigo-mark.png"


def build_icon(size, filename, *, maskable=False):
    mark = Image.open(BRAND_MARK).convert("RGBA")
    image = Image.new("RGBA", (size, size), "white")
    safe_ratio = 0.62 if maskable else 0.78
    max_side = round(size * safe_ratio)
    mark.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    position = ((size - mark.width) // 2, (size - mark.height) // 2)
    image.alpha_composite(mark, position)
    image.convert("RGB").save(OUTPUT_DIR / filename, format="PNG", optimize=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_icon(180, "apple-touch-icon.png")
    build_icon(192, "icon-192.png")
    build_icon(512, "icon-512.png")
    build_icon(512, "icon-maskable-512.png", maskable=True)
    build_icon(32, "favicon-32.png")


if __name__ == "__main__":
    main()

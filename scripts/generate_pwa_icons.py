from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "static" / "pwa"


def rounded_rectangle(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def build_icon(size, filename, *, maskable=False):
    scale = size / 512
    image = Image.new("RGB", (size, size), "#111827")
    draw = ImageDraw.Draw(image)

    margin = int((82 if maskable else 42) * scale)
    radius = int(88 * scale)
    rounded_rectangle(
        draw,
        (margin, margin, size - margin, size - margin),
        radius,
        "#4f46e5",
    )

    left = int(142 * scale)
    right = int(370 * scale)
    roof_y = int(174 * scale)
    base_y = int(366 * scale)
    draw.polygon(
        [
            (int(119 * scale), int(222 * scale)),
            (int(256 * scale), roof_y),
            (int(393 * scale), int(222 * scale)),
            (right, int(242 * scale)),
            (int(256 * scale), int(202 * scale)),
            (left, int(242 * scale)),
        ],
        fill="#ffffff",
    )
    rounded_rectangle(
        draw,
        (left, int(232 * scale), right, base_y),
        int(15 * scale),
        "#ffffff",
    )

    window_color = "#4f46e5"
    for x in (180, 244, 308):
        rounded_rectangle(
            draw,
            (
                int(x * scale),
                int(262 * scale),
                int((x + 34) * scale),
                int(307 * scale),
            ),
            int(6 * scale),
            window_color,
        )
    rounded_rectangle(
        draw,
        (
            int(237 * scale),
            int(322 * scale),
            int(275 * scale),
            base_y,
        ),
        int(6 * scale),
        window_color,
    )

    image.save(OUTPUT_DIR / filename, format="PNG", optimize=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_icon(180, "apple-touch-icon.png")
    build_icon(192, "icon-192.png")
    build_icon(512, "icon-512.png")
    build_icon(512, "icon-maskable-512.png", maskable=True)


if __name__ == "__main__":
    main()

"""Draw the app icon (assets/icon.png, .ico and .icns). Dev-time only; needs Pillow."""
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
S = 1024  # drawn large, scaled down for each icon size

# Floor colours from the hot bottom to the cool top.
FLOORS = ["#e8452c", "#f07a2a", "#f2b233", "#5bb6d9", "#3a7bd5"]


def draw():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 40, S - 40, S - 40), radius=200, fill="#1e2330")
    n = len(FLOORS)
    left, right, bottom, top = 230, 794, 860, 170
    fh = (bottom - top) / n
    d.rectangle((150, bottom, 874, bottom + 40), fill="#9aa3b5")  # base plate
    for k, colour in enumerate(FLOORS):
        z1 = bottom - k * fh
        z0 = z1 - fh + 14
        d.rectangle((left + 70, z0, left + 230, z1), fill=colour)                 # label block
        d.polygon([(left + 70, z1), (left + 70, z0), (left - 40, z0)], fill=colour)  # 45° overhang
        d.rectangle((right - 150, z0, right - 70, z1), fill=colour)               # pillar
        d.polygon([(right - 70, z1), (right - 70, z0), (right + 60, z0)], fill=colour)  # 35° overhang
        d.rectangle((left + 230, z0, right - 150, z0 + 26), fill=colour)          # bridge
        cx = (left + 230 + right - 150) / 2
        d.polygon([(cx - 34, z1), (cx + 34, z1), (cx, z1 - fh * 0.55)], fill=colour)  # cone
    return img


def main():
    img = draw()
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(ASSETS, "icon.png"))
    img.save(os.path.join(ASSETS, "icon.ico"), sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    img.resize((512, 512), Image.LANCZOS).save(os.path.join(ASSETS, "icon.icns"))
    print("wrote icon.png, icon.ico, icon.icns to", ASSETS)


if __name__ == "__main__":
    main()

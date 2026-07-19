"""Generates 8x8 pixel-art icons for the data.gov.sg 2-hour forecast conditions.

Unlike convert_tiles.py (which converts real airline logo images), there's no
source artwork for weather conditions, so these are hand-plotted pixel grids
drawn directly at 8x8 and saved in the same format AWTRIX expects: black
background, indexed GIF, no transparency.

Output: icons/wx_<key>.gif, e.g. icons/wx_fair_day.gif
"""

import os
from PIL import Image

OUTPUT_FOLDER = "./icons"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

BLACK = "."
COLORS = {
    "S": (255, 200, 0),     # sun
    "M": (190, 200, 255),   # moon
    "C": (200, 200, 200),   # light cloud
    "D": (120, 120, 135),   # dark/rain cloud
    "R": (60, 130, 255),    # rain drop
    "T": (255, 230, 60),    # thunder bolt
    "F": (150, 150, 150),   # fog/mist/haze
    "W": (100, 210, 220),   # wind
}

# Each icon is 8 rows of 8 characters. '.' is background, everything else
# is looked up in COLORS above.
ICONS = {
    "fair_day": [
        "..S..S..",
        ".S....S.",
        "..SSSS..",
        ".SSSSSS.",
        ".SSSSSS.",
        "..SSSS..",
        ".S....S.",
        "..S..S..",
    ],
    "fair_night": [
        "...MM...",
        "..MMM...",
        ".MMM....",
        "MMM.....",
        "MMM.....",
        ".MMM....",
        "..MMM...",
        "...MM...",
    ],
    "partly_cloudy_day": [
        "..S.....",
        ".S.S....",
        "..S.CCC.",
        ".CCCCCCC",
        "CCCCCCCC",
        "CCCCCCCC",
        "........",
        "........",
    ],
    "partly_cloudy_night": [
        "..M.....",
        ".MM.....",
        "MM..CCC.",
        ".CCCCCCC",
        "CCCCCCCC",
        "CCCCCCCC",
        "........",
        "........",
    ],
    "cloudy": [
        "........",
        "..DDDD..",
        ".DDDDDD.",
        "DDDDDDDD",
        "DDDDDDDD",
        "........",
        "........",
        "........",
    ],
    "hazy": [
        "........",
        ".FFFFFF.",
        "........",
        "FFFFFFFF",
        "........",
        ".FFFFFF.",
        "........",
        "........",
    ],
    "windy": [
        "........",
        ".WWW....",
        "....WWW.",
        "WWW.....",
        "....WWW.",
        ".WWW....",
        "....WWW.",
        "........",
    ],
    "mist": [
        "........",
        "FFFFFFFF",
        "........",
        "FFFFFFFF",
        "........",
        "FFFFFFFF",
        "........",
        "FFFFFFFF",
    ],
    "fog": [
        "FFFFFFFF",
        "FFFFFFFF",
        "........",
        "FFFFFFFF",
        "FFFFFFFF",
        "........",
        "FFFFFFFF",
        "FFFFFFFF",
    ],
    "light_rain": [
        "..DDDD..",
        ".DDDDDD.",
        "DDDDDDDD",
        "........",
        ".R.R.R..",
        "........",
        ".R.R.R..",
        "........",
    ],
    "moderate_rain": [
        "..DDDD..",
        ".DDDDDD.",
        "DDDDDDDD",
        "........",
        "R.R.R.R.",
        ".R.R.R.R",
        "R.R.R.R.",
        ".R.R.R.R",
    ],
    "heavy_rain": [
        "DDDDDDDD",
        "DDDDDDDD",
        "DDDDDDDD",
        "RRRRRRRR",
        ".R.R.R.R",
        "RRRRRRRR",
        ".R.R.R.R",
        "RRRRRRRR",
    ],
    "thunder": [
        "..DDDD..",
        ".DDDDDD.",
        "DDDDDDDD",
        "...TT...",
        "..TT....",
        ".TTTT...",
        "..TT....",
        ".TT.....",
    ],
    "thunder_heavy": [
        "DDDDDDDD",
        "DDDDDDDD",
        "DDDDDDDD",
        "..TT.R..",
        ".TT..R..",
        "TTTT.R..",
        "..TT..R.",
        ".TT...R.",
    ],
    "thunder_wind": [
        "DDDDDDDD",
        "DDDDDDDD",
        "WW.TT.WW",
        "..TT....",
        ".TTTT...",
        "WW.TT.WW",
        "..TT....",
        "WW....WW",
    ],
}


def build(grid):
    img = Image.new("RGB", (8, 8), (0, 0, 0))
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != BLACK:
                img.putpixel((x, y), COLORS[ch])
    return img


def main():
    for key, grid in ICONS.items():
        img = build(grid).convert("P", palette=Image.ADAPTIVE, colors=16)
        out_path = os.path.join(OUTPUT_FOLDER, f"wx_{key}.gif")
        img.save(out_path, transparency=None)
        print(f"{key} -> {out_path}")


if __name__ == "__main__":
    main()
